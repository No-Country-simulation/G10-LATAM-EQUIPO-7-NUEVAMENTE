"""Pruebas de contrato, persistencia e historial por ciclo de revisión."""

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.application.format_revision_history_service import (
    FormatRevisionHistoryService,
)
from app.domain.document import Document
from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.format_evaluation import FormatEvaluation, HeuristicScoresV2
from app.domain.generated_content import (
    FlashcardItem,
    FlashcardsContent,
    QuizContent,
    QuizQuestion,
)
from app.domain.generated_format import ChunkEvidence, GeneratedFormat, GenerationContext
from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_format_evaluation_repository_adapter import (
    SQLiteFormatEvaluationRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryError
from app.schemas.revision_cycle import RevisionHistoryResponse


def make_document(identifier: str) -> Document:
    """Construye un documento independiente con hash único."""
    data = identifier.encode("utf-8")
    return Document(
        document_id=identifier,
        original_filename=f"{identifier}.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(data),
    )


def make_quiz(
    identifier: str,
    *,
    document_id: str = "doc_a",
    revision_of_format_id: str | None = None,
    created_at: datetime | None = None,
) -> GeneratedFormat:
    """Crea un Quiz válido con las evidencias obligatorias."""
    now = created_at or datetime.now(UTC)
    return GeneratedFormat(
        format_id=identifier,
        document_id=document_id,
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=GenerationContext(
            profile="beginner",
            niche="technology",
            detail_level="detailed",
            learning_objective="Comprender microservicios",
        ),
        content=QuizContent(
            title="Quiz de microservicios",
            instructions="Selecciona la respuesta correcta.",
            questions=(
                QuizQuestion(
                    question_id="q1",
                    question="¿Qué es un microservicio?",
                    options=("Servicio independiente", "Una tabla"),
                    correct_answer="Servicio independiente",
                    explanation="Puede desplegarse separadamente.",
                ),
            ),
        ),
        chunks_used=(
            ChunkEvidence(
                chunk_id=f"{document_id}_0",
                document_id=document_id,
                rank=1,
                score=0.9,
                text="Los microservicios son desplegables independientemente.",
            ),
        ),
        revision_of_format_id=revision_of_format_id,
        created_at=now,
        updated_at=now,
    )


def repositories(tmp_path: Path):
    """Inicializa repositorios reales aislados por prueba."""
    db = SQLiteDatabase(f"sqlite:///{(tmp_path / 'revision.db').as_posix()}")
    db.initialize()
    docs = SQLiteDocumentRepositoryAdapter(db)
    formats = SQLiteGeneratedFormatRepositoryAdapter(db)
    evaluations = SQLiteFormatEvaluationRepositoryAdapter(db)
    return db, docs, formats, evaluations


def test_domain_rejects_self_reference_and_empty_reference() -> None:
    """La entidad no puede crear ciclos autorreferentes."""
    with pytest.raises(ValueError, match="sí mismo"):
        make_quiz("original", revision_of_format_id="original")
    with pytest.raises(ValueError, match="no vacía"):
        make_quiz("revision", revision_of_format_id=" ")


def test_roundtrip_and_one_revision_per_root(tmp_path: Path) -> None:
    """Guarda relación válida y rechaza una segunda corrección."""
    _, docs, formats, _ = repositories(tmp_path)
    docs.create(make_document("doc_a"))
    formats.create(make_quiz("original"))
    formats.create(make_quiz("revision", revision_of_format_id="original"))
    assert formats.find_by_id("original").revision_of_format_id is None
    assert formats.find_by_id("revision").revision_of_format_id == "original"
    with pytest.raises(GeneratedFormatRepositoryError, match="revisión"):
        formats.create(make_quiz("revision2", revision_of_format_id="original"))


def test_revision_cannot_change_document_or_type_or_chain(tmp_path: Path) -> None:
    """Las referencias cruzadas y las cadenas de revisión se rechazan."""
    _, docs, formats, _ = repositories(tmp_path)
    docs.create(make_document("doc_a"))
    docs.create(make_document("doc_b"))
    formats.create(make_quiz("original"))
    with pytest.raises(GeneratedFormatRepositoryError, match="mismo documento"):
        formats.create(make_quiz(
            "wrong-doc", document_id="doc_b", revision_of_format_id="original"
        ))
    incompatible = replace(
        make_quiz("wrong-type", revision_of_format_id="original"),
        format_type=GeneratedFormatType.FLASHCARDS,
        content=FlashcardsContent(
            title="Tarjetas técnicas",
            instructions="Repasar",
            cards=(FlashcardItem(card_id="c1", front="A", back="B"),),
        ),
    )
    with pytest.raises(GeneratedFormatRepositoryError, match="tipo de formato"):
        formats.create(incompatible)
    with pytest.raises(GeneratedFormatRepositoryError, match="No existe"):
        formats.create(make_quiz("missing", revision_of_format_id="absent"))
    formats.create(make_quiz("revision", revision_of_format_id="original"))
    with pytest.raises(GeneratedFormatRepositoryError, match="encadenadas"):
        formats.create(make_quiz("chained", revision_of_format_id="revision"))


def test_revision_reference_is_immutable(tmp_path: Path) -> None:
    """Un update no puede convertir una generación raíz en corrección."""
    _, docs, formats, _ = repositories(tmp_path)
    docs.create(make_document("doc_a"))
    original = make_quiz("original")
    formats.create(original)
    with pytest.raises(GeneratedFormatRepositoryError, match="identidad"):
        formats.update(replace(original, revision_of_format_id="other"))


def test_history_does_not_reuse_evaluation_from_previous_cycle(tmp_path: Path) -> None:
    """La evaluación vigente pertenece al formato del mismo ciclo."""
    _, docs, formats, evaluations = repositories(tmp_path)
    docs.create(make_document("doc_a"))
    t = datetime(2026, 10, 1, tzinfo=UTC)
    root1 = make_quiz("root1", created_at=t)
    child1 = make_quiz("child1", revision_of_format_id="root1", created_at=t + timedelta(hours=1))
    root2 = make_quiz("root2", created_at=t + timedelta(days=1))
    formats.create(root1)
    formats.create(child1)
    formats.create(root2)
    evaluations.create(FormatEvaluation(
        evaluation_id="eval-root1", format_id="root1", verdict="rejected",
        heuristic_scores=HeuristicScoresV2(2.0, 2.0, 2.0, 2.0),
        created_at=t,
    ))
    evaluations.create(FormatEvaluation(
        evaluation_id="eval-child1", format_id="child1", verdict="approved",
        heuristic_scores=HeuristicScoresV2(4.0, 4.0, 4.0, 4.0),
        created_at=t + timedelta(hours=2),
    ))
    service = FormatRevisionHistoryService(
        document_repository=docs,
        generated_format_repository=formats,
        evaluation_repository=evaluations,
    )
    history = service.get_history("doc_a", GeneratedFormatType.QUIZ)
    assert [x.original.generated_format.format_id for x in history.cycles] == ["root2", "root1"]
    assert history.cycles[0].latest_evaluation is None
    assert history.cycles[1].latest_evaluation.format_id == "child1"
    response = RevisionHistoryResponse.from_domain(history).model_dump(mode="json")
    assert response["cycles"][1]["revision"]["revision_of_format_id"] == "root1"
    assert response["cycles"][1]["latest_evaluation"]["verdict"] == "approved"


def test_new_database_schema_and_reinitialize(tmp_path: Path) -> None:
    """Una migración repetida conserva la referencia y el índice."""
    db, docs, formats, _ = repositories(tmp_path)
    docs.create(make_document("doc_a"))
    formats.create(make_quiz("original"))
    formats.create(make_quiz("revision", revision_of_format_id="original"))
    db.initialize()
    with db.connect() as connection:
        columns = [
            row["name"]
            for row in connection.execute("PRAGMA table_info(generated_formats)")
        ]
        assert "revision_of_format_id" in columns
    assert formats.find_by_id("revision").revision_of_format_id == "original"


def test_migrates_database_without_revision_column(tmp_path: Path) -> None:
    """La BD anterior a Sprint 4 conserva registros al agregar la columna."""
    from app.infrastructure.persistence.database import (
        _DOCUMENTS_TABLE_SQL,
        _GENERATED_FORMATS_TABLE_SQL,
    )

    db = SQLiteDatabase(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    legacy_ddl = _GENERATED_FORMATS_TABLE_SQL.replace(
        "    revision_of_format_id TEXT,\n", ""
    )
    with db.connect() as connection:
        connection.execute(_DOCUMENTS_TABLE_SQL)
        connection.execute(legacy_ddl)
        connection.execute(
            """INSERT INTO documents
              (document_id, original_filename, sha256, content_type,
               size_bytes, status, created_at, updated_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("doc_a", "doc_a.pdf", "a" * 64, "application/pdf", 5,
             "stored", "2026-10-01", "2026-10-01"),
        )
        connection.execute(
            """INSERT INTO generated_formats
              (format_id, document_id, format_type, status,
               profile, niche, detail_level, created_at, updated_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("root", "doc_a", "quiz", "failed", "beginner", "technology",
             "detailed", "2026-10-01", "2026-10-01"),
        )
    db.initialize()
    with db.connect() as connection:
        row = connection.execute(
            "SELECT revision_of_format_id FROM generated_formats WHERE format_id = 'root'"
        ).fetchone()
        assert row is not None and row["revision_of_format_id"] is None
    db.initialize()


def test_http_returns_typed_history(tmp_path: Path) -> None:
    """La API expone el contrato de historial y la identidad de cada versión."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_format_revision_history_service
    from app.api.v1.endpoints.format_revision_history import router

    _, docs, formats, evals = repositories(tmp_path)
    docs.create(make_document("doc_a"))
    formats.create(make_quiz("root"))
    service = FormatRevisionHistoryService(
        document_repository=docs,
        generated_format_repository=formats,
        evaluation_repository=evals,
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_format_revision_history_service] = lambda: service
    client = TestClient(app)
    response = client.get("/api/v1/documents/doc_a/formats/quiz/history")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["cycles"][0]["original"]["format_id"] == "root"
    assert result["cycles"][0]["revision"] is None
    assert result["cycles"][0]["latest_evaluation"] is None


def test_legacy_table_rebuild_preserves_revision_reference(tmp_path: Path) -> None:
    """La reconstrucción por CHECK antiguo no descarta revision_of_format_id."""
    from app.infrastructure.persistence.database import (
        _DOCUMENTS_TABLE_SQL,
        _GENERATED_FORMATS_TABLE_SQL,
    )

    db = SQLiteDatabase(f"sqlite:///{(tmp_path / 'old-check.db').as_posix()}")
    old_schema = _GENERATED_FORMATS_TABLE_SQL.replace(
        "                'quiz',\n"
        "                'flashcards',\n"
        "                'tldr',\n"
        "                'video_script'",
        "                'quiz',\n"
        "                'flashcards'",
    )
    assert old_schema != _GENERATED_FORMATS_TABLE_SQL
    with db.connect() as connection:
        connection.execute(_DOCUMENTS_TABLE_SQL)
        connection.execute(old_schema)
        connection.execute(
            """INSERT INTO documents
              (document_id, original_filename, sha256, content_type,
               size_bytes, status, created_at, updated_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("doc_a", "doc_a.pdf", "a" * 64, "application/pdf", 5,
             "stored", "2026-10-01", "2026-10-01"),
        )
        for identifier, parent in (("root", None), ("revision", "root")):
            connection.execute(
                """INSERT INTO generated_formats
                    (format_id, document_id, revision_of_format_id,
                     format_type, status, profile, niche, detail_level,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (identifier, "doc_a", parent, "quiz", "failed", "beginner",
                 "technology", "detailed", "2026-10-01", "2026-10-01"),
            )
    db.initialize()
    with db.connect() as connection:
        row = connection.execute(
            """SELECT revision_of_format_id FROM generated_formats
               WHERE format_id = 'revision'"""
        ).fetchone()
        assert row is not None and row["revision_of_format_id"] == "root"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
