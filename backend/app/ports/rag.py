"""Contrato entre BackendAPI y el módulo RAG."""

from dataclasses import dataclass
from typing import Protocol


class RagError(Exception):
    """Error general durante una operación solicitada al módulo RAG."""


@dataclass(frozen=True, slots=True)
class RagDocumentInput:
    """Documento entregado por BackendAPI al módulo RAG.

    BackendAPI es responsable de recuperar físicamente el archivo desde
    Object Storage antes de construir este contrato. RAG no necesita conocer
    detalles de OCI ni referencias internas de almacenamiento.

    Attributes:
        document_id: Identificador canónico generado por BackendAPI.
        filename: Nombre original del documento.
        content_type: MIME type registrado, cuando está disponible.
        content: Contenido binario completo recuperado por BackendAPI.
    """

    document_id: str
    filename: str
    content_type: str | None
    content: bytes


class RagPort(Protocol):
    """Operaciones del módulo RAG requeridas por BackendAPI."""

    async def index_document(
        self,
        document: RagDocumentInput,
    ) -> None:
        """Entrega un documento al módulo RAG para iniciar su indexación.

        Args:
            document: Documento recuperado y preparado por BackendAPI.

        Raises:
            RagError: Si el módulo RAG no acepta o no puede procesar
                la solicitud.
        """
        ...