"""Pruebas unitarias del adapter provisional BackendAPI-RAG."""

import asyncio

import pytest

from app.infrastructure.integrations.rag_entry_point_adapter import (
    RAGEntryPointAdapter,
)
from app.ports.rag_port import (
    RAGDocumentInput,
    RAGError,
)


class RecordingRAGEntryPoint:
    """Entry point controlado que registra los argumentos recibidos."""

    def __init__(self) -> None:
        self.received: dict[
            str,
            object,
        ] | None = None

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


class FailingRAGEntryPoint:
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


def test_rag_entry_point_adapter_maps_document_contract() -> None:
    """Traduce correctamente el contrato interno al entry point."""
    entry_point = RecordingRAGEntryPoint()

    adapter = RAGEntryPointAdapter(
        entry_point=entry_point
    )

    document = RAGDocumentInput(
        document_id="doc_123",
        filename="manual.pdf",
        content_type="application/pdf",
        content=b"contenido",
    )

    asyncio.run(
        adapter.index_document(
            document
        )
    )

    assert entry_point.received == {
        "document_id": "doc_123",
        "filename": "manual.pdf",
        "content_type": "application/pdf",
        "content": b"contenido",
    }


def test_rag_entry_point_adapter_translates_external_error() -> None:
    """Convierte errores del entry point externo a RAGError."""
    adapter = RAGEntryPointAdapter(
        entry_point=FailingRAGEntryPoint()
    )

    document = RAGDocumentInput(
        document_id="doc_123",
        filename="manual.pdf",
        content_type="application/pdf",
        content=b"contenido",
    )

    with pytest.raises(
        RAGError,
        match=(
            "El módulo RAG no pudo recibir "
            "el documento doc_123."
        ),
    ):
        asyncio.run(
            adapter.index_document(
                document
            )
        )