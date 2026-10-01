"""Pruebas de los contratos HTTP de documentos."""

from datetime import UTC, datetime

from app.domain.enums import (
    DocumentStatus,
)
from app.schemas.document import (
    DocumentCreatedResponse,
    DocumentResponse,
)


def test_document_created_response() -> None:
    """Expone únicamente el resultado de procesamiento del documento."""
    response = DocumentCreatedResponse(
        document_id="doc_123",
        filename="manual.pdf",
        status=DocumentStatus.INDEXED,
        duplicate=False,
    )

    assert (
        response.document_id
        == "doc_123"
    )
    assert (
        response.filename
        == "manual.pdf"
    )
    assert (
        response.status
        == DocumentStatus.INDEXED
    )
    assert response.duplicate is False

    assert (
        "formats"
        not in response.model_dump()
    )


def test_document_response() -> None:
    """Expone metadata base y campos enriquecidos opcionales."""
    now = datetime.now(
        UTC
    )

    response = DocumentResponse(
        document_id="doc_123",
        filename="manual.pdf",
        status=DocumentStatus.INDEXED,
        content_type="application/pdf",
        size_bytes=100,
        created_at=now,
        updated_at=now,
    )

    assert response.size_bytes == 100
    assert response.title is None
    assert response.summary is None
    assert response.estimated_time is None