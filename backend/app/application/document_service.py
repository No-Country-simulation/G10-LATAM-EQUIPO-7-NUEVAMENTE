"""Casos de uso relacionados con documentos."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.hashing import calculate_file_sha256
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.ports.document_repository import DocumentRepository
from app.ports.object_storage import (
    ObjectStorageError,
    ObjectStoragePort,
)


class DocumentNotFoundError(Exception):
    """El documento solicitado no existe."""

class DocumentNotStoredError(Exception):
    """El documento existe, pero no tiene un objeto persistente asociado."""

class DocumentStorageError(Exception):
    """No fue posible almacenar el documento de forma persistente."""

class DocumentRetrievalError(Exception):
    """No fue posible recuperar el contenido persistente del documento."""

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

    Esta estructura pertenece a la capa de aplicación y representa el
    resultado de recuperar físicamente un documento. No constituye todavía
    el contrato BackendAPI-RAG.

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
        repository: DocumentRepository,
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
        """Registra un documento validado y detecta contenido duplicado.

        El archivo debe haber superado previamente las validaciones técnicas
        de carga.

        Args:
            local_path: Ruta temporal del documento.
            original_filename: Nombre original recibido.
            content_type: MIME type del documento.
            size_bytes: Tamaño del archivo en bytes.

        Returns:
            Resultado con el documento y un indicador de creación.
        """
        sha256 = calculate_file_sha256(local_path)

        existing_document = self._repository.find_by_sha256(sha256)

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

        document.update_status(DocumentStatus.VALIDATED)
        self._repository.create(document)

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
        document = self.get_document(document_id)

        object_name = self._build_object_name(document)

        document.update_status(DocumentStatus.STORING)
        self._repository.update(document)

        try:
            object_storage.upload_file(
                local_path=local_path,
                object_name=object_name,
                content_type=document.content_type,
            )
        except Exception as exc:
            document.update_status(DocumentStatus.STORAGE_FAILED)
            self._repository.update(document)

            raise DocumentStorageError(
                f"No fue posible almacenar el documento {document_id}."
            ) from exc

        document.assign_oci_object(object_name)
        document.update_status(DocumentStatus.STORED)
        self._repository.update(document)

        return document

    def retrieve_document(
        self,
        *,
        document_id: str,
        object_storage: ObjectStoragePort,
    ) -> RetrievedDocument:
        """Recupera físicamente un documento desde Object Storage.

        El caso de uso obtiene primero la metadata persistida utilizando el
        ``document_id`` canónico de BackendAPI. Posteriormente utiliza el
        ``oci_object_name`` asociado para recuperar el contenido binario.

        Esta operación no realiza extracción, limpieza, chunking, embeddings
        ni indexación. Esas responsabilidades pertenecen al módulo RAG.

        Args:
            document_id: Identificador canónico del documento.
            object_storage: Proveedor de almacenamiento configurado.

        Returns:
            Documento con metadata básica y contenido binario recuperado.

        Raises:
            DocumentNotFoundError: Si el document_id no está registrado.
            DocumentNotStoredError: Si no existe una referencia a Object
                Storage asociada al documento.
            DocumentRetrievalError: Si Object Storage no permite recuperar
                el contenido.
        """
        document = self.get_document(document_id)

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

    def get_document(self, document_id: str) -> Document:
        """Obtiene un documento registrado por su identificador."""
        document = self._repository.find_by_id(document_id)

        if document is None:
            raise DocumentNotFoundError(
                f"No existe el documento {document_id}."
            )

        return document

    @staticmethod
    def _build_object_name(document: Document) -> str:
        """Construye el nombre lógico del objeto persistente."""
        extension = Path(document.original_filename).suffix.lower()

        return (
            f"documents/{document.document_id}/"
            f"original{extension}"
        )