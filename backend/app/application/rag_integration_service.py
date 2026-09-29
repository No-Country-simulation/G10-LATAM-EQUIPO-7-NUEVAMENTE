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
    """No fue posible completar la indexación mediante RAG."""


class RAGIntegrationService:
    """Orquesta la indexación de documentos almacenados mediante RAG.

    BackendAPI conserva el control del documento original y lo recupera
    desde Object Storage utilizando su document_id canónico. RAG recibe
    únicamente el documento necesario para ejecutar extracción, limpieza,
    chunking, embeddings e indexación.

    Este servicio no implementa ninguna operación interna del pipeline RAG.
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
        """Recupera desde OCI e indexa un documento mediante RAG.

        El contenido binario se recupera antes de marcar el documento como
        INDEXING. Así, un fallo al recuperar OCI continúa siendo un problema
        de almacenamiento y no se registra erróneamente como fallo de RAG.

        Args:
            document_id: Identificador canónico generado por BackendAPI.

        Raises:
            DocumentNotFoundError: Si el documento no está registrado.
            DocumentNotStoredError: Si no posee un objeto persistido.
            DocumentRetrievalError: Si no puede recuperarse desde OCI.
            DocumentIndexingStateError: Si el documento no puede iniciar
                una nueva indexación.
            RAGIntegrationError: Si RAG rechaza o falla durante la
                indexación.
        """
        retrieved_document = (
            self._document_service.retrieve_document(
                document_id=document_id,
                object_storage=self._object_storage,
            )
        )

        self._document_service.start_indexing(
            document_id
        )

        rag_document = self._build_rag_document(
            retrieved_document
        )

        try:
            await self._rag.index_document(
                rag_document
            )

        except RAGError as exc:
            self._document_service.fail_indexing(
                document_id
            )

            raise RAGIntegrationError(
                "No fue posible indexar el documento "
                f"{document_id} mediante RAG."
            ) from exc

        self._document_service.complete_indexing(
            document_id
        )

    @staticmethod
    def _build_rag_document(
        document: RetrievedDocument,
    ) -> RAGDocumentInput:
        """Transforma el documento recuperado al contrato interno de RAG."""
        return RAGDocumentInput(
            document_id=document.document_id,
            filename=document.filename,
            content_type=document.content_type,
            content=document.content,
        )