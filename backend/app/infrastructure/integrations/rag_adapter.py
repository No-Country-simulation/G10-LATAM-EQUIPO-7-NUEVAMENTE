"""Adaptador de integración entre BackendAPI y el módulo RAG.

La implementación no depende de clases internas del módulo RAG. El entry
point concreto se inyecta y deberá ajustarse cuando el equipo RAG confirme
su interfaz pública definitiva.
"""

from typing import Protocol

from app.ports.rag import (
    RagDocumentInput,
    RagError,
)


class RagEntryPoint(Protocol):
    """Firma mínima esperada del entry point público del módulo RAG.

    Esta interfaz pertenece únicamente al adaptador de infraestructura.
    Si el módulo RAG publica una firma diferente, el cambio debe quedar
    encapsulado en este adaptador sin afectar aplicación ni dominio.
    """

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


class RagAdapter:
    """Implementa RagPort utilizando el entry point público de RAG."""

    def __init__(
        self,
        entry_point: RagEntryPoint,
    ) -> None:
        self._entry_point = entry_point

    async def index_document(
        self,
        document: RagDocumentInput,
    ) -> None:
        """Traduce el contrato BackendAPI al entry point de RAG."""
        try:
            await self._entry_point.index_document(
                document_id=document.document_id,
                filename=document.filename,
                content_type=document.content_type,
                content=document.content,
            )
        except Exception as exc:
            raise RagError(
                "El módulo RAG no pudo recibir el documento "
                f"{document.document_id}."
            ) from exc