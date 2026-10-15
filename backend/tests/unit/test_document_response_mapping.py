"""Pruebas del mapeo de Document al contrato HTTP DocumentResponse."""

import hashlib

from app.api.v1.endpoints.documents import _to_document_response
from app.domain.document import Document
from app.domain.enums import DocumentStatus


def _build_document(
    *,
    document_title: str | None,
    document_description: str | None,
) -> Document:
    content = b"contenido de prueba"

    return Document(
        document_id="doc_123",
        original_filename="manual.pdf",
        sha256=hashlib.sha256(content).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
        status=DocumentStatus.INDEXED,
        document_title=document_title,
        document_description=document_description,
    )


def test_to_document_response_populates_title_and_summary() -> None:
    """title/summary ya enriquecidos por Agentes llegan al contrato HTTP."""
    document = _build_document(
        document_title="Fundamentos de microservicios",
        document_description="Resumen breve del documento.",
    )

    response = _to_document_response(document)

    assert response.title == "Fundamentos de microservicios"
    assert response.summary == "Resumen breve del documento."


def test_to_document_response_defaults_to_none_when_not_yet_enriched() -> (
    None
):
    """Mientras Agentes no haya respondido, title/summary viajan null."""
    document = _build_document(
        document_title=None,
        document_description=None,
    )

    response = _to_document_response(document)

    assert response.title is None
    assert response.summary is None
