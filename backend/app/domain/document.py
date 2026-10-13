"""Entidad de dominio que representa un documento de NuevaMente."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.enums import DocumentStatus
from app.domain.learning_metadata import LearningMetadata


@dataclass(slots=True)
class Document:
    """Documento registrado dentro de NuevaMente.

    Esta entidad representa la metadata interna del documento y no el
    contrato HTTP expuesto al frontend.

    Attributes:
        document_id: Identificador único interno.
        original_filename: Nombre original recibido desde el cliente.
        sha256: Firma SHA-256 del contenido.
        content_type: MIME type detectado o declarado.
        size_bytes: Tamaño del documento en bytes.
        status: Estado actual dentro del flujo de procesamiento.
        oci_object_name: Identificador del objeto persistido en OCI.
        learning_metadata: Metadatos pedagógicos de la adaptación vigente.
        created_at: Fecha de creación del registro.
        updated_at: Fecha de última modificación.
    """

    document_id: str
    original_filename: str
    sha256: str
    content_type: str | None
    size_bytes: int

    status: DocumentStatus = DocumentStatus.RECEIVED
    oci_object_name: str | None = None
    learning_metadata: LearningMetadata | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        """Valida invariantes básicas de la entidad."""
        if not self.document_id.strip():
            raise ValueError("document_id no puede estar vacío.")

        if not self.original_filename.strip():
            raise ValueError("original_filename no puede estar vacío.")

        if self.size_bytes < 0:
            raise ValueError("size_bytes no puede ser negativo.")

        if len(self.sha256) != 64:
            raise ValueError(
                "sha256 debe contener 64 caracteres hexadecimales."
            )

        try:
            int(self.sha256, 16)
        except ValueError as exc:
            raise ValueError(
                "sha256 debe contener únicamente caracteres hexadecimales."
            ) from exc

    def update_status(self, status: DocumentStatus) -> None:
        """Actualiza el estado del documento y su fecha de modificación."""
        self.status = status
        self.updated_at = datetime.now(UTC)

    def assign_oci_object(self, object_name: str) -> None:
        """Asocia el documento con su objeto persistido en OCI."""
        if not object_name.strip():
            raise ValueError("object_name no puede estar vacío.")

        self.oci_object_name = object_name
        self.updated_at = datetime.now(UTC)

    def clear_oci_object(self) -> None:
        """Retira la referencia al objeto OCI durante una compensación."""
        self.oci_object_name = None
        self.updated_at = datetime.now(UTC)

    def assign_learning_metadata(
        self,
        learning_metadata: LearningMetadata,
    ) -> None:
        """Asocia metadata pedagógica estable a nivel de documento.

        La regeneración de Quiz o Flashcards no representa una nueva
        adaptación del documento, por lo que no debe reemplazar metadata
        pedagógica útil ya persistida únicamente por la variabilidad de una
        nueva respuesta del LLM.

        Se permite reemplazar el fallback vacío oficial para que una
        generación posterior pueda recuperar metadata útil si la extracción
        inicial falló.
        """
        empty_metadata = (
            LearningMetadata.empty()
        )

        if (
            self.learning_metadata is not None
            and self.learning_metadata
            != empty_metadata
        ):
            return

        if (
            self.learning_metadata
            == learning_metadata
        ):
            return

        self.learning_metadata = (
            learning_metadata
        )
        self.updated_at = datetime.now(UTC)
