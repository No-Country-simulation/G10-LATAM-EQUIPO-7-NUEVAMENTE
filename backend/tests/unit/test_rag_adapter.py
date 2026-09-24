"""Pruebas unitarias del adaptador BackendAPI-RAG."""

import asyncio

import pytest

from app.infrastructure.integrations.rag_adapter import (
    RagAdapter,
)
from app.ports.rag import (
    RagDocumentInput,
    RagError,
)


class RecordingRagEntryPoint:
    """Entry point controlado que registra los argumentos recibidos."""

    def __init__(self) -> None:
        self.received: dict[str, object] | None = None

    async def index_document(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> None:
        self.received = {
            "document_id": document_id,
            "filename": filename,
            "content_type": content_type,
            "content": content,
        }


class FailingRagEntryPoint:
    """Entry point que simula un fallo interno de RAG."""

    async def index_document(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> None:
        raise RuntimeError(
            "Fallo simulado del entry point RAG."
        )


def test_rag_adapter_maps_document_contract() -> None:
    """Traduce correctamente RagDocumentInput al entry point."""
    entry_point = RecordingRagEntryPoint()

    adapter = RagAdapter(
        entry_point=entry_point
    )

    document = RagDocumentInput(
        document_id="doc_123",
        filename="manual.pdf",
        content_type="application/pdf",
        content=b"contenido",
    )

    asyncio.run(
        adapter.index_document(document)
    )

    assert entry_point.received == {
        "document_id": "doc_123",
        "filename": "manual.pdf",
        "content_type": "application/pdf",
        "content": b"contenido",
    }


def test_rag_adapter_translates_external_error() -> None:
    """Convierte errores del entry point externo a RagError."""
    adapter = RagAdapter(
        entry_point=FailingRagEntryPoint()
    )

    document = RagDocumentInput(
        document_id="doc_123",
        filename="manual.pdf",
        content_type="application/pdf",
        content=b"contenido",
    )

    with pytest.raises(
        RagError,
        match="El módulo RAG no pudo recibir el documento doc_123.",
    ):
        asyncio.run(
            adapter.index_document(document)
        )