"""Casos de uso relacionados con documentos."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.hashing import calculate_file_sha256
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.ports.document_repository import DocumentRepository
from app.ports.object_storage import ObjectStoragePort


class DocumentNotFoundError(Exception):
    """El documento solicitado no existe."""


class DocumentStorageError(Exception):
    """No fue posible almacenar el documento de forma persistente."""


@dataclass(frozen=True, slots=True)
class DocumentRegistrationResult:
    """Resultado del registro de un documento.

    Attributes:
        document: Documento registrado o previamente existente.
        created: Indica si se creó un nuevo registro.
    """

    document: Document
    created: bool


class DocumentService:
    """Orquesta los casos de uso asociados a documentos."""

    def __init__(
        self,
        repository: DocumentRepository,
        object_storage: ObjectStoragePort,
    ) -> None:
        self._repository = repository
        self._object_storage = object_storage

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
    ) -> Document:
        """Almacena permanentemente un documento previamente registrado."""
        document = self.get_document(document_id)

        object_name = self._build_object_name(document)

        document.update_status(DocumentStatus.STORING)
        self._repository.update(document)

        try:
            self._object_storage.upload_file(
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