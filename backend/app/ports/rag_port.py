"""Puerto para la integración entre BackendAPI y RAG."""

from dataclasses import dataclass
from typing import Protocol


class RAGError(Exception):
    """Error general durante una operación solicitada a RAG."""


@dataclass(frozen=True, slots=True)
class RAGDocumentInput:
    """Documento entregado por BackendAPI al módulo RAG.

    BackendAPI recupera físicamente el archivo desde Object Storage antes
    de construir este contrato. RAG no necesita conocer detalles de OCI
    ni referencias internas de almacenamiento.

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


class RAGPort(Protocol):
    """Define las operaciones de RAG requeridas por BackendAPI."""

    async def index_document(
        self,
        document: RAGDocumentInput,
    ) -> None:
        """Entrega un documento al módulo RAG para su indexación.

        Args:
            document: Documento recuperado y preparado por BackendAPI.

        Raises:
            RAGError: Si RAG no acepta o no puede procesar la solicitud.
        """
        ...