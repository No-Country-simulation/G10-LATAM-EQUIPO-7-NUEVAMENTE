"""Casos de uso relacionados con documentos."""

import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.hashing import calculate_file_sha256
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.ports.document_repository_port import (
    DocumentRepositoryError,
    DocumentRepositoryPort,
)
from app.ports.object_storage_port import (
    ObjectStorageError,
    ObjectStoragePort,
)

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    """El documento solicitado no existe."""


class DocumentNotStoredError(Exception):
    """El documento existe, pero no tiene un objeto persistente asociado."""


class DocumentStorageError(Exception):
    """No fue posible completar el almacenamiento persistente."""


class DocumentStorageConsistencyError(DocumentStorageError):
    """No fue posible restaurar la consistencia tras un fallo de persistencia."""


class DocumentRetrievalError(Exception):
    """No fue posible recuperar el contenido persistente del documento."""


class DocumentIndexingStateError(Exception):
    """El documento no puede realizar la transición de indexación solicitada."""


@dataclass(frozen=True, slots=True)
class DocumentRegistrationResult:
    """Resultado del registro de un documento.

    Attributes:
        document: Documento registrado o previamente existente.
        created: Indica si se creó un nuevo registro.
    """

    document: Document
    created: bool


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    """Documento recuperado desde el almacenamiento persistente.

    Attributes:
        document_id: Identificador canónico generado por BackendAPI.
        filename: Nombre original con el que se registró el documento.
        content_type: MIME type registrado para el documento.
        content: Contenido binario recuperado desde Object Storage.
    """

    document_id: str
    filename: str
    content_type: str | None
    content: bytes


class DocumentService:
    """Orquesta los casos de uso asociados a documentos."""

    def __init__(
        self,
        repository: DocumentRepositoryPort,
    ) -> None:
        self._repository = repository

    def register_document(
        self,
        *,
        local_path: Path,
        original_filename: str,
        content_type: str | None,
        size_bytes: int,
    ) -> DocumentRegistrationResult:
        """Registra un documento validado y detecta contenido duplicado."""
        sha256 = calculate_file_sha256(
            local_path
        )

        existing_document = (
            self._repository.find_by_sha256(
                sha256
            )
        )

        if existing_document is not None:
            return DocumentRegistrationResult(
                document=existing_document,
                created=False,
            )

        document = Document(
            document_id=f"doc_{uuid4().hex}",
            original_filename=original_filename,
            sha256=sha256,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        document.update_status(
            DocumentStatus.VALIDATED
        )

        self._repository.create(
            document
        )

        return DocumentRegistrationResult(
            document=document,
            created=True,
        )

    def store_document(
        self,
        *,
        document_id: str,
        local_path: Path,
        object_storage: ObjectStoragePort,
    ) -> Document:
        """Almacena permanentemente un documento previamente registrado."""
        document = self.get_document(
            document_id
        )

        object_name = self._build_object_name(
            document
        )

        document.update_status(
            DocumentStatus.STORING
        )

        self._repository.update(
            document
        )

        try:
            object_storage.upload_file(
                local_path=local_path,
                object_name=object_name,
                content_type=document.content_type,
            )
        except ObjectStorageError as exc:
            document.update_status(
                DocumentStatus.STORAGE_FAILED
            )

            self._repository.update(
                document
            )

            raise DocumentStorageError(
                f"No fue posible almacenar el documento {document_id}."
            ) from exc

        document.assign_oci_object(
            object_name
        )

        document.update_status(
            DocumentStatus.STORED
        )

        try:
            self._repository.update(
                document
            )
        except DocumentRepositoryError as exc:
            self._compensate_failed_storage_persistence(
                document=document,
                object_name=object_name,
                object_storage=object_storage,
            )

            raise DocumentStorageError(
                "No fue posible confirmar el almacenamiento del documento "
                f"{document_id}; la carga en Object Storage fue revertida."
            ) from exc

        return document

    def retrieve_document(
        self,
        *,
        document_id: str,
        object_storage: ObjectStoragePort,
    ) -> RetrievedDocument:
        """Recupera físicamente un documento desde Object Storage."""
        document = self.get_document(
            document_id
        )

        if document.oci_object_name is None:
            raise DocumentNotStoredError(
                f"El documento {document_id} no tiene "
                "un objeto almacenado asociado."
            )

        try:
            content = object_storage.download_file(
                document.oci_object_name
            )
        except ObjectStorageError as exc:
            raise DocumentRetrievalError(
                f"No fue posible recuperar el documento {document_id}."
            ) from exc

        return RetrievedDocument(
            document_id=document.document_id,
            filename=document.original_filename,
            content_type=document.content_type,
            content=content,
        )

    def start_indexing(
        self,
        document_id: str,
    ) -> Document:
        """Marca un documento almacenado como en proceso de indexación."""
        return self._transition_indexing_status(
            document_id=document_id,
            allowed_from={
                DocumentStatus.STORED,
                DocumentStatus.INDEXING_FAILED,
            },
            target=DocumentStatus.INDEXING,
        )

    def complete_indexing(
        self,
        document_id: str,
    ) -> Document:
        """Marca como indexado un documento cuya indexación terminó."""
        return self._transition_indexing_status(
            document_id=document_id,
            allowed_from={
                DocumentStatus.INDEXING,
            },
            target=DocumentStatus.INDEXED,
        )

    def fail_indexing(
        self,
        document_id: str,
    ) -> Document:
        """Marca como fallida una indexación previamente iniciada."""
        return self._transition_indexing_status(
            document_id=document_id,
            allowed_from={
                DocumentStatus.INDEXING,
            },
            target=DocumentStatus.INDEXING_FAILED,
        )

    def get_document(
        self,
        document_id: str,
    ) -> Document:
        """Obtiene un documento registrado por su identificador."""
        document = self._repository.find_by_id(
            document_id
        )

        if document is None:
            raise DocumentNotFoundError(
                f"No existe el documento {document_id}."
            )

        return document

    def _transition_indexing_status(
        self,
        *,
        document_id: str,
        allowed_from: set[DocumentStatus],
        target: DocumentStatus,
    ) -> Document:
        """Ejecuta y persiste una transición controlada de indexación."""
        document = self.get_document(
            document_id
        )

        if document.status not in allowed_from:
            allowed_values = ", ".join(
                sorted(
                    status.value
                    for status in allowed_from
                )
            )

            raise DocumentIndexingStateError(
                f"El documento {document_id} está en estado "
                f"{document.status.value} y no puede pasar a "
                f"{target.value}. Estados permitidos: "
                f"{allowed_values}."
            )

        document.update_status(
            target
        )

        self._repository.update(
            document
        )

        return document

    def _compensate_failed_storage_persistence(
        self,
        *,
        document: Document,
        object_name: str,
        object_storage: ObjectStoragePort,
    ) -> None:
        """Compensa una carga OCI cuya metadata final no pudo persistirse."""
        try:
            object_storage.delete_object(
                object_name
            )
        except ObjectStorageError as exc:
            logger.exception(
                "No fue posible compensar el objeto %s del documento %s.",
                object_name,
                document.document_id,
            )

            raise DocumentStorageConsistencyError(
                f"El documento {document.document_id} quedó en un estado "
                "inconsistente: la carga en Object Storage finalizó, "
                "la metadata no pudo persistirse y tampoco fue posible "
                "eliminar el objeto durante la compensación."
            ) from exc

        document.clear_oci_object()

        document.update_status(
            DocumentStatus.STORAGE_FAILED
        )

        try:
            self._repository.update(
                document
            )
        except DocumentRepositoryError as exc:
            logger.exception(
                "El objeto del documento %s fue compensado, pero no fue "
                "posible persistir el estado STORAGE_FAILED.",
                document.document_id,
            )

            raise DocumentStorageConsistencyError(
                f"El objeto del documento {document.document_id} fue "
                "eliminado de Object Storage, pero no fue posible "
                "registrar STORAGE_FAILED en persistencia."
            ) from exc

    @staticmethod
    def _build_object_name(
        document: Document,
    ) -> str:
        """Construye el nombre lógico del objeto persistente."""
        extension = Path(
            document.original_filename
        ).suffix.lower()

        return (
            f"documents/{document.document_id}/"
            f"original{extension}"
        )