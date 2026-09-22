"""Contrato provisional entre BackendAPI y el módulo RAG."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RagDocumentInput:
    """Documento entregado al módulo RAG para indexación.

    Este contrato es provisional hasta cerrar la integración definitiva
    entre BackendAPI y el equipo RAG.
    """

    document_id: str
    filename: str
    content_type: str | None
    content: bytes


class RagPort(Protocol):
    """Operaciones de RAG requeridas por BackendAPI."""

    async def index_document(
        self,
        document: RagDocumentInput,
    ) -> None:
        """Solicita la indexación semántica de un documento."""
        ...