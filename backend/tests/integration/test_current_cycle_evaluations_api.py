"""Pruebas HTTP de la proyección de evaluaciones del ciclo vigente.

Ejercitan el endpoint con repositorios SQLite reales y el cliente HTTP de
FastAPI; no dependen de Agentes, Data/IA ni OCI.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.document import Document
from app.domain.enums import DocumentStatus, GeneratedFormatStatus, GeneratedFormatType
from app.domain.format_evaluation import FormatEvaluation, HeuristicScoresV2
from app.domain.generated_content import TLDRContent
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

DOCUMENT_ID = "doc_current_cycle"
BASE_TIME = datetime(2026, 10, 15, 10, tzinfo=UTC)


def build_repositories(tmp_path: Path):
    """Construye repositorios aislados sobre la BD de la fixture HTTP."""
    database = SQLiteDatabase(
        f"sqlite:///{(tmp_path / 'nuevamente_test.db').as_posix()}"
    )
    database.initialize()
    return (
        SQLiteDocumentRepositoryAdapter(database),
        SQLiteGeneratedFormatRepositoryAdapter(database),
        SQLiteFormatEvaluationRepositoryAdapter(database),
    )


def insert_document(documents: SQLiteDocumentRepositoryAdapter) -> None:
    """Registra un documento indexado para consultar sus formatos."""
    documents.create(
        Document(
            document_id=DOCUMENT_ID,
            original_filename="manual.txt",
            sha256=hashlib.sha256(DOCUMENT_ID.encode()).hexdigest(),
            content_type="text/plain",
            size_bytes=100,
            status=DocumentStatus.INDEXED,
        )
    )


def make_format(
    identifier: str,
    *,
    created_at: datetime = BASE_TIME,
    status: GeneratedFormatStatus = GeneratedFormatStatus.SUCCESS,
    revision_of: str | None = None,
) -> GeneratedFormat:
    """Representa TLDR con contenido y evidencia cuando hay éxito."""
    successful = status == GeneratedFormatStatus.SUCCESS
    return GeneratedFormat(
        format_id=identifier,
        document_id=DOCUMENT_ID,
        format_type=GeneratedFormatType.TLDR,
        status=status,
        generation_context=GenerationContext(
            profile="beginner",
            niche="technology",
            detail_level="detailed",
        ),
        content=(
            TLDRContent(
                title=f"Contenido {identifier}",
                summary="Síntesis del documento.",
                key_points=("Idea esencial",),
                conclusion="Conclusión útil.",
            )
            if successful
            else None
        ),
        chunks_used=(
            (
                ChunkEvidence(
                    chunk_id="c1",
                    document_id=DOCUMENT_ID,
                    rank=1,
                    score=0.9,
                    text="Fragmento documentado.",
                ),
            )
            if successful
            else ()
        ),
        error_message=(
            "Error simulado." if status == GeneratedFormatStatus.FAILED else None
        ),
        revision_of_format_id=revision_of,
        created_at=created_at,
        updated_at=created_at,
    )


def insert_evaluation(
    evaluations: SQLiteFormatEvaluationRepositoryAdapter,
    identifier: str,
    format_id: str,
    *,
    created_at: datetime,
    verdict: str,
) -> None:
    """Persiste una evaluación V2 genuina para la versión indicada."""
    evaluations.create(
        FormatEvaluation(
            evaluation_id=identifier,
            format_id=format_id,
            verdict=verdict,
            heuristic_scores=HeuristicScoresV2(4.0, 3.0, 4.0, 4.0),
            created_at=created_at,
        )
    )


def fetch_tldr(client: TestClient, api_prefix: str) -> dict:
    """Solicita el contrato público y devuelve la sección TLDR."""
    response = client.get(f"{api_prefix}/documents/{DOCUMENT_ID}/formats")
    assert response.status_code == 200, response.text
    return response.json()["formats"]["tldr"]


def test_original_has_one_current_evaluation(
    client: TestClient, api_prefix: str, tmp_path: Path
) -> None:
    """Un contenido sin revisión entrega su evaluación V2."""
    docs, formats, evaluations = build_repositories(tmp_path)
    insert_document(docs)
    formats.create(make_format("original"))
    insert_evaluation(
        evaluations, "ev_original", "original",
        created_at=BASE_TIME + timedelta(minutes=5), verdict="approved",
    )

    tldr = fetch_tldr(client, api_prefix)
    assert tldr["format_id"] == "original"
    assert tldr["evaluation"]["evaluation_id"] == "ev_original"
    assert [item["evaluation_id"] for item in tldr["evaluations"]] == ["ev_original"]
    assert tldr["evaluations"][0]["heuristic_scores"]["relevance"] == 4.0


def test_revised_content_has_latest_first_and_only_current_cycle(
    client: TestClient, api_prefix: str, tmp_path: Path
) -> None:
    """Devuelve evaluaciones de raíz y corrección con la más reciente primero."""
    docs, formats, evaluations = build_repositories(tmp_path)
    insert_document(docs)
    formats.create(make_format("original"))
    formats.create(make_format(
        "revision", created_at=BASE_TIME + timedelta(hours=1), revision_of="original"
    ))
    insert_evaluation(
        evaluations, "ev_original", "original",
        created_at=BASE_TIME + timedelta(minutes=3), verdict="requires_revision",
    )
    insert_evaluation(
        evaluations, "ev_revision", "revision",
        created_at=BASE_TIME + timedelta(hours=2), verdict="approved",
    )

    tldr = fetch_tldr(client, api_prefix)
    assert tldr["format_id"] == "revision"
    assert tldr["content"]["title"] == "Contenido revision"
    assert tldr["revision_of_format_id"] == "original"
    assert tldr["evaluation"]["evaluation_id"] == "ev_revision"
    assert [item["evaluation_id"] for item in tldr["evaluations"]] == [
        "ev_revision", "ev_original"
    ]


def test_new_regeneration_does_not_inherit_previous_cycle(
    client: TestClient, api_prefix: str, tmp_path: Path
) -> None:
    """La regeneración exitosa tiene solo sus propias métricas."""
    docs, formats, evaluations = build_repositories(tmp_path)
    insert_document(docs)
    formats.create(make_format("original"))
    formats.create(make_format(
        "revision", revision_of="original", created_at=BASE_TIME + timedelta(hours=1)
    ))
    formats.create(make_format("new_root", created_at=BASE_TIME + timedelta(days=1)))
    insert_evaluation(
        evaluations, "ev_original", "original",
        created_at=BASE_TIME + timedelta(minutes=3), verdict="requires_revision",
    )
    insert_evaluation(
        evaluations, "ev_revision", "revision",
        created_at=BASE_TIME + timedelta(hours=2), verdict="approved",
    )

    tldr = fetch_tldr(client, api_prefix)
    assert tldr["format_id"] == "new_root"
    assert tldr["evaluation"] is None
    assert tldr["evaluations"] == []


def test_failed_regeneration_keeps_previous_content_and_metrics(
    client: TestClient, api_prefix: str, tmp_path: Path
) -> None:
    """Si el último intento falla, el fallback apunta al ciclo del contenido."""
    docs, formats, evaluations = build_repositories(tmp_path)
    insert_document(docs)
    formats.create(make_format("original"))
    formats.create(make_format(
        "revision", revision_of="original", created_at=BASE_TIME + timedelta(hours=1)
    ))
    formats.create(make_format(
        "failed_new_root", status=GeneratedFormatStatus.FAILED,
        created_at=BASE_TIME + timedelta(days=1),
    ))
    insert_evaluation(
        evaluations, "ev_original", "original",
        created_at=BASE_TIME + timedelta(minutes=3), verdict="requires_revision",
    )
    insert_evaluation(
        evaluations, "ev_revision", "revision",
        created_at=BASE_TIME + timedelta(hours=2), verdict="approved",
    )

    tldr = fetch_tldr(client, api_prefix)
    assert tldr["format_id"] == "revision"
    assert tldr["evaluation"]["format_id"] == "revision"
    assert [item["evaluation_id"] for item in tldr["evaluations"]] == [
        "ev_revision", "ev_original"
    ]


def test_revised_content_without_reevaluation_does_not_inherit_verdict(
    client: TestClient, api_prefix: str, tmp_path: Path
) -> None:
    """La evaluación singular de una corrección sin reevaluar permanece nula."""
    docs, formats, evaluations = build_repositories(tmp_path)
    insert_document(docs)
    formats.create(make_format("original"))
    formats.create(make_format(
        "revision", revision_of="original", created_at=BASE_TIME + timedelta(hours=1)
    ))
    insert_evaluation(
        evaluations, "ev_original", "original",
        created_at=BASE_TIME + timedelta(minutes=3), verdict="requires_revision",
    )

    tldr = fetch_tldr(client, api_prefix)
    assert tldr["format_id"] == "revision"
    assert tldr["evaluation"] is None
    assert [item["format_id"] for item in tldr["evaluations"]] == ["original"]


def test_active_regeneration_does_not_show_old_metrics(
    client: TestClient, api_prefix: str, tmp_path: Path
) -> None:
    """Un intento en proceso muestra solo evaluaciones de su nuevo ciclo."""
    docs, formats, evaluations = build_repositories(tmp_path)
    insert_document(docs)
    formats.create(make_format("original"))
    formats.create(make_format(
        "processing_root", status=GeneratedFormatStatus.PROCESSING,
        created_at=BASE_TIME + timedelta(days=1),
    ))
    insert_evaluation(
        evaluations, "ev_original", "original",
        created_at=BASE_TIME + timedelta(minutes=3), verdict="approved",
    )

    tldr = fetch_tldr(client, api_prefix)
    assert tldr["format_id"] == "processing_root"
    assert tldr["status"] == "processing"
    assert tldr["evaluation"] is None
    assert tldr["evaluations"] == []


def test_unevaluated_content_preserves_previous_http_fields(
    client: TestClient, api_prefix: str, tmp_path: Path
) -> None:
    """La API conserva el contrato previo aunque aún falten métricas."""
    docs, formats, _ = build_repositories(tmp_path)
    insert_document(docs)
    formats.create(make_format("original"))

    tldr = fetch_tldr(client, api_prefix)
    assert tldr["status"] == "success"
    assert tldr["revision_of_format_id"] is None
    assert tldr["error_message"] is None
    assert tldr["content"]["summary"] == "Síntesis del documento."
    assert tldr["evaluation"] is None
    assert tldr["evaluations"] == []
