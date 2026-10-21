"""Pruebas de recuperación sobre SQLite real y de transiciones tardías.

No requiere Agentes, Data/IA, OCI ni credenciales. Conserva el original.
"""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.application.stale_revision_recovery_service import StaleRevisionRecoveryService
from app.domain.document import Document
from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.generated_content import TLDRContent
from app.domain.generated_format import ChunkEvidence, GeneratedFormat, GenerationContext
from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_stale_revision_recovery_adapter import (
    SQLiteStaleRevisionRecoveryAdapter,
)
from app.operations.recover_stale_revisions import main
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryError

NOW = datetime(2026, 10, 15, 15, 0, tzinfo=UTC)
CONTEXT = GenerationContext(profile="profesional", niche="tecnología", detail_level="avanzado")


def make_content(title: str) -> TLDRContent:
    """Contenido canónico usado para probar cambios de estado terminal."""
    return TLDRContent(
        title=title,
        summary="Resumen de prueba",
        key_points=("Trazabilidad",),
        conclusion="Conclusión de prueba",
    )


def make_evidence(document_id: str) -> tuple[ChunkEvidence, ...]:
    """Evidencia RAG canónica perteneciente al documento."""
    return (ChunkEvidence(
        chunk_id=f"chunk_{document_id}",
        document_id=document_id,
        rank=1,
        score=0.91,
        text="La arquitectura mantiene la trazabilidad del contenido.",
    ),)


def make_format(
    identifier: str,
    *,
    document_id: str = "doc_recovery",
    parent_id: str | None = None,
    status: GeneratedFormatStatus = GeneratedFormatStatus.PROCESSING,
    age_minutes: int = 120,
) -> GeneratedFormat:
    """Crea raíz o revisión con un estado y tiempo conocido."""
    stamp = NOW - timedelta(minutes=age_minutes)
    return GeneratedFormat(
        format_id=identifier,
        document_id=document_id,
        revision_of_format_id=parent_id,
        format_type=GeneratedFormatType.TLDR,
        status=status,
        generation_context=CONTEXT,
        content=make_content(identifier) if status == GeneratedFormatStatus.SUCCESS else None,
        chunks_used=(
            make_evidence(document_id) if status == GeneratedFormatStatus.SUCCESS else ()
        ),
        error_message=("Error anterior" if status == GeneratedFormatStatus.FAILED else None),
        created_at=stamp,
        updated_at=stamp,
    )


def setup_database(tmp_path: Path):
    """Prepara bases y repositorios SQLite reales y aislados por prueba."""
    path = tmp_path / "recovery.db"
    db = SQLiteDatabase(f"sqlite:///{path.as_posix()}")
    db.initialize()
    documents = SQLiteDocumentRepositoryAdapter(db)
    documents.create(Document(
        document_id="doc_recovery",
        original_filename="manual.txt",
        sha256=hashlib.sha256(b"manual recovery").hexdigest(),
        content_type="text/plain",
        size_bytes=len(b"manual recovery"),
    ))
    formats = SQLiteGeneratedFormatRepositoryAdapter(db)
    recovery = SQLiteStaleRevisionRecoveryAdapter(db)
    service = StaleRevisionRecoveryService(recovery_port=recovery)
    return path, formats, recovery, service


def seed_root_and_revision(
    formats: SQLiteGeneratedFormatRepositoryAdapter,
    *,
    root_id: str = "root",
    revision_id: str = "rev_old",
    age_minutes: int = 120,
) -> GeneratedFormat:
    """Persiste una raíz exitosa y su revisión en processing."""
    formats.create(make_format(root_id, status=GeneratedFormatStatus.SUCCESS, age_minutes=240))
    return formats.create(make_format(
        revision_id,
        parent_id=root_id,
        age_minutes=age_minutes,
    ))


def test_preview_is_read_only_and_does_not_repeat_llm(tmp_path: Path) -> None:
    """Vista previa devuelve identidades y no escribe ni produce correcciones."""
    _, formats, _, service = setup_database(tmp_path)
    seed_root_and_revision(formats)
    report = service.execute(older_than_minutes=60, now=NOW)
    assert report.applied is False
    assert report.recovered_ids == ()
    assert len(report.candidates) == 1
    assert report.candidates[0].original_format_id == "root"
    assert report.candidates[0].format_id == "rev_old"
    assert formats.find_by_id("rev_old").status == GeneratedFormatStatus.PROCESSING


def test_apply_marks_only_old_revisions_failed_and_is_idempotent(tmp_path: Path) -> None:
    """Solo falla revisiones vencidas; respeta raíces y reservas recientes."""
    _, formats, _, service = setup_database(tmp_path)
    seed_root_and_revision(formats)
    seed_root_and_revision(
        formats,
        root_id="root_new",
        revision_id="rev_recent",
        age_minutes=5,
    )
    formats.create(make_format("root_processing", age_minutes=180))
    first = service.execute(older_than_minutes=60, apply=True, now=NOW)
    assert first.recovered_ids == ("rev_old",)
    assert formats.find_by_id("rev_old").status == GeneratedFormatStatus.FAILED
    assert "Revisión interrumpida" in formats.find_by_id("rev_old").error_message
    assert formats.find_by_id("root").status == GeneratedFormatStatus.SUCCESS
    assert formats.find_by_id("rev_recent").status == GeneratedFormatStatus.PROCESSING
    assert formats.find_by_id("root_processing").status == GeneratedFormatStatus.PROCESSING
    second = service.execute(older_than_minutes=60, apply=True, now=NOW)
    assert second.recovered_ids == ()
    assert second.candidates == ()


def test_already_terminal_revisions_are_not_changed(tmp_path: Path) -> None:
    """Nunca modifica correcciones exitosas o fallidas existentes."""
    _, formats, _, service = setup_database(tmp_path)
    formats.create(make_format("root_success", status=GeneratedFormatStatus.SUCCESS))
    formats.create(make_format(
        "rev_success",
        parent_id="root_success",
        status=GeneratedFormatStatus.SUCCESS,
    ))
    formats.create(make_format("root_failed", status=GeneratedFormatStatus.SUCCESS))
    formats.create(make_format(
        "rev_failed",
        parent_id="root_failed",
        status=GeneratedFormatStatus.FAILED,
    ))
    report = service.execute(older_than_minutes=60, apply=True, now=NOW)
    assert report.candidates == ()
    assert report.recovered_ids == ()
    assert formats.find_by_id("rev_success").status == GeneratedFormatStatus.SUCCESS
    assert formats.find_by_id("rev_failed").error_message == "Error anterior"


def test_late_success_cannot_reactivate_recovered_revision(tmp_path: Path) -> None:
    """La escritura normal está protegida contra una respuesta HTTP tardía."""
    _, formats, _, service = setup_database(tmp_path)
    old = seed_root_and_revision(formats)
    service.execute(older_than_minutes=60, apply=True, now=NOW)
    late = replace(
        old,
        status=GeneratedFormatStatus.SUCCESS,
        content=make_content("respuesta tardía"),
        chunks_used=make_evidence(old.document_id),
        updated_at=NOW + timedelta(seconds=1),
    )
    with pytest.raises(GeneratedFormatRepositoryError, match="estado terminal"):
        formats.update(late)
    recovered = formats.find_by_id("rev_old")
    assert recovered.status == GeneratedFormatStatus.FAILED
    assert recovered.content is None
    assert recovered.revision_of_format_id == "root"
    assert formats.find_by_id("root").content.title == "root"


def test_late_failure_cannot_overwrite_recovery_reason(tmp_path: Path) -> None:
    """Ni siquiera la compensación tardía debe reemplazar el estado final."""
    _, formats, _, service = setup_database(tmp_path)
    old = seed_root_and_revision(formats)
    service.execute(older_than_minutes=60, apply=True, now=NOW)
    with pytest.raises(GeneratedFormatRepositoryError, match="estado terminal"):
        formats.update(replace(
            old,
            status=GeneratedFormatStatus.FAILED,
            error_message="Timeout tardío",
            updated_at=NOW + timedelta(seconds=2),
        ))
    assert "interrumpida" in formats.find_by_id("rev_old").error_message


def test_failed_revision_still_blocks_second_revision(tmp_path: Path) -> None:
    """El índice UNIQUE por raíz continúa vigente después de la recuperación."""
    _, formats, _, service = setup_database(tmp_path)
    seed_root_and_revision(formats)
    service.execute(older_than_minutes=60, apply=True, now=NOW)
    with pytest.raises(GeneratedFormatRepositoryError, match="ya tiene una revisión"):
        formats.create(make_format("rev_duplicate", parent_id="root"))


def test_cutoff_is_inclusive_and_uses_last_update_not_creation(tmp_path: Path) -> None:
    """updated_at en el límite se recupera; una actualización reciente lo protege."""
    _, formats, _, service = setup_database(tmp_path)
    old = seed_root_and_revision(formats, age_minutes=60)
    exact = service.execute(older_than_minutes=60, now=NOW)
    assert [c.format_id for c in exact.candidates] == ["rev_old"]
    formats.update(replace(old, updated_at=NOW - timedelta(minutes=10)))
    assert service.execute(older_than_minutes=60, now=NOW).candidates == ()


@pytest.mark.parametrize("age", [0, -3, True, 1.5, "60"])
def test_service_rejects_invalid_threshold(tmp_path: Path, age: object) -> None:
    """No hay umbral nulo, negativo o ambiguo que cierre revisiones activas."""
    _, _, _, service = setup_database(tmp_path)
    with pytest.raises(ValueError, match="older_than_minutes"):
        service.execute(older_than_minutes=age, now=NOW)


def test_service_rejects_naive_clock(tmp_path: Path) -> None:
    """El reloj de la operación debe tener zona horaria explícita."""
    _, _, _, service = setup_database(tmp_path)
    with pytest.raises(ValueError, match="zona horaria"):
        service.execute(now=datetime(2026, 10, 15, 15))


def test_cli_defaults_to_preview_and_reports_json(tmp_path: Path, capsys) -> None:
    """CLI requiere ruta explícita y no modifica estado sin --apply."""
    path, formats, _, _ = setup_database(tmp_path)
    seed_root_and_revision(formats, age_minutes=150)
    assert main([
        "--database-url", f"sqlite:///{path.as_posix()}",
        "--older-than-minutes", "60",
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["applied"] is False
    assert result["recovered_ids"] == []
    assert result["candidates"][0]["format_id"] == "rev_old"
    assert formats.find_by_id("rev_old").status == GeneratedFormatStatus.PROCESSING


def test_cli_apply_needs_quiescence_confirmation(tmp_path: Path) -> None:
    """Sin confirmación de trabajadores detenidos, --apply se rechaza."""
    path, formats, _, _ = setup_database(tmp_path)
    seed_root_and_revision(formats)
    with pytest.raises(SystemExit) as error:
        main(["--database-url", f"sqlite:///{path.as_posix()}", "--apply"])
    assert error.value.code == 2
    assert formats.find_by_id("rev_old").status == GeneratedFormatStatus.PROCESSING


def test_cli_apply_and_missing_database(tmp_path: Path, capsys) -> None:
    """Aplica con confirmación; se niega a crear accidentalmente otra base."""
    path, formats, _, _ = setup_database(tmp_path)
    seed_root_and_revision(formats)
    assert main([
        "--database-url", f"sqlite:///{path.as_posix()}",
        "--older-than-minutes", "60",
        "--apply", "--acknowledge-workers-stopped",
    ]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["applied"] is True
    assert report["recovered_ids"] == ["rev_old"]
    unknown = tmp_path / "no-existe.db"
    assert main(["--database-url", f"sqlite:///{unknown.as_posix()}"]) == 2
    assert not unknown.exists()
