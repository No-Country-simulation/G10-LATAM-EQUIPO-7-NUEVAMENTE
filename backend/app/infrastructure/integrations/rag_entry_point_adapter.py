"""Adaptador provisional entre BackendAPI y un entry point de RAG.

Este adapter representa la integración previa a la comunicación HTTP.
Permite mantener desacoplada la capa de aplicación mientras se define
e implementa el endpoint público del módulo RAG.
"""

from typing import Protocol

from app.ports.rag_port import (
    RAGDocumentInput,
    RAGError,
)


class RAGEntryPoint(Protocol):
    """Firma mínima esperada de un entry point de RAG."""

    async def index_document(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> None:
        """Recibe un documento desde BackendAPI para indexación."""
        ...


class RAGEntryPointAdapter:
    """Implementa RAGPort utilizando un entry point inyectado."""

    def __init__(
        self,
        entry_point: RAGEntryPoint,
    ) -> None:
        self._entry_point = entry_point

    async def index_document(
        self,
        document: RAGDocumentInput,
    ) -> None:
        """Traduce el contrato interno al entry point de RAG."""
        try:
            await self._entry_point.index_document(
                document_id=document.document_id,
                filename=document.filename,
                content_type=document.content_type,
                content=document.content,
            )

        except Exception as exc:
            raise RAGError(
                "El módulo RAG no pudo recibir el documento "
                f"{document.document_id}."
            ) from exc