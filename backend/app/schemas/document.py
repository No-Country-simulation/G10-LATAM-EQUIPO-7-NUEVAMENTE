"""Schemas HTTP relacionados con documentos."""

from datetime import datetime

from pydantic import Field

from app.domain.enums import DocumentStatus
from app.domain.learning_metadata import LearningMetadata
from app.schemas.common import BaseSchema


class DocumentBaseResponse(BaseSchema):
    """Información común expuesta de un documento."""

    document_id: str = Field(
        min_length=1,
        description="Identificador único del documento.",
    )
    filename: str = Field(
        min_length=1,
        description="Nombre original del documento.",
    )
    status: DocumentStatus = Field(
        description="Estado actual del documento.",
    )


class DocumentCreatedResponse(DocumentBaseResponse):
    """Respuesta al finalizar la carga y procesamiento del documento."""

    duplicate: bool = Field(
        default=False,
        description=(
            "Indica si el contenido ya estaba registrado."
        ),
    )


class DocumentListItemResponse(DocumentBaseResponse):
    """Metadata de un documento expuesta en la biblioteca."""

    content_type: str | None = Field(
        default=None,
        description="Tipo MIME del documento.",
    )
    size_bytes: int = Field(
        ge=0,
        description="Tamaño del documento en bytes.",
    )
    created_at: datetime
    updated_at: datetime


class LearningMetadataResponse(BaseSchema):
    """Metadatos pedagógicos generados para la adaptación del documento."""

    key_concepts: list[str] = Field(
        default_factory=list,
        description=(
            "Conceptos o ideas principales identificados "
            "en el documento."
        ),
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description=(
            "Conocimientos previos recomendados para estudiar "
            "el contenido."
        ),
    )
    estimated_time_minutes: int = Field(
        ge=0,
        description=(
            "Tiempo estimado de estudio expresado en minutos."
        ),
    )

    @classmethod
    def from_domain(
        cls,
        metadata: LearningMetadata,
    ) -> "LearningMetadataResponse":
        """Convierte el value object de dominio al contrato HTTP."""
        return cls(
            key_concepts=list(
                metadata.key_concepts
            ),
            prerequisites=list(
                metadata.prerequisites
            ),
            estimated_time_minutes=(
                metadata.estimated_time_minutes
            ),
        )


class DocumentResponse(DocumentListItemResponse):
    """Información pública detallada de un documento."""

    title: str | None = Field(
        default=None,
        description=(
            "Título enriquecido del documento cuando esté disponible."
        ),
    )
    summary: str | None = Field(
        default=None,
        description=(
            "Resumen breve del documento cuando esté disponible."
        ),
    )
    learning_metadata: (
        LearningMetadataResponse | None
    ) = Field(
        default=None,
        description=(
            "Metadatos pedagógicos de la adaptación. "
            "Puede ser null mientras la generación no haya "
            "producido todavía una respuesta válida de Agentes."
        ),
    )


class DocumentListResponse(BaseSchema):
    """Listado de documentos disponibles en la biblioteca."""

    documents: list[DocumentListItemResponse] = Field(
        default_factory=list,
        description=(
            "Documentos activos disponibles para consulta "
            "desde la biblioteca."
        ),
    )
