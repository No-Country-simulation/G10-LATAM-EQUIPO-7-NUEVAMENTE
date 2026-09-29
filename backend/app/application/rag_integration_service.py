"""Casos de uso para la integración entre BackendAPI y RAG."""

from app.application.document_service import (
    DocumentService,
    RetrievedDocument,
)
from app.ports.object_storage_port import (
    ObjectStoragePort,
)
from app.ports.rag_port import (
    RAGDocumentInput,
    RAGError,
    RAGPort,
)


class RAGIntegrationError(Exception):
    """No fue posible entregar el documento al módulo RAG."""


class RAGIntegrationService:
    """Orquesta la entrega de documentos almacenados al módulo RAG.

    La aplicación recupera el documento utilizando las capacidades de
    BackendAPI y posteriormente lo transforma al contrato definido por
    ``RAGPort``.

    Este servicio no implementa extracción, limpieza, chunking, embeddings,
    almacenamiento vectorial ni retrieval semántico.
    """

    def __init__(
        self,
        *,
        document_service: DocumentService,
        object_storage: ObjectStoragePort,
        rag: RAGPort,
    ) -> None:
        self._document_service = document_service
        self._object_storage = object_storage
        self._rag = rag

    async def index_document(
        self,
        document_id: str,
    ) -> None:
        """Recupera un documento y lo entrega al módulo RAG.

        Args:
            document_id: Identificador canónico generado por BackendAPI.

        Raises:
            DocumentNotFoundError: Si el documento no está registrado.
            DocumentNotStoredError: Si no posee un objeto persistido.
            DocumentRetrievalError: Si no puede recuperarse desde storage.
            RAGIntegrationError: Si RAG rechaza o falla al recibirlo.
        """
        retrieved_document = (
            self._document_service.retrieve_document(
                document_id=document_id,
                object_storage=self._object_storage,
            )
        )

        rag_document = self._build_rag_document(
            retrieved_document
        )

        try:
            await self._rag.index_document(
                rag_document
            )

        except RAGError as exc:
            raise RAGIntegrationError(
                "No fue posible entregar el documento "
                f"{document_id} al módulo RAG."
            ) from exc

    @staticmethod
    def _build_rag_document(
        document: RetrievedDocument,
    ) -> RAGDocumentInput:
        """Transforma el resultado de Backend al contrato BackendAPI-RAG."""
        return RAGDocumentInput(
            document_id=document.document_id,
            filename=document.filename,
            content_type=document.content_type,
            content=document.content,
        )