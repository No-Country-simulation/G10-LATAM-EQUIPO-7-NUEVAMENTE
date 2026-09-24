"""Pruebas de los contratos HTTP de documentos."""

from datetime import UTC, datetime

from app.domain.enums import DocumentStatus
from app.schemas.document import (
    DocumentCreatedResponse,
    DocumentResponse,
)


def test_document_created_response() -> None:
    response = DocumentCreatedResponse(
        document_id="doc_123",
        filename="manual.pdf",
        status=DocumentStatus.STORED,
    )

    assert response.document_id == "doc_123"
    assert response.status == DocumentStatus.STORED


def test_document_response() -> None:
    now = datetime.now(UTC)

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