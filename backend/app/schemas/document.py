"""Schemas HTTP relacionados con documentos."""

from datetime import datetime

from pydantic import Field

from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatType,
)
from app.schemas.common import BaseSchema
from app.schemas.generated_format import (
    GeneratedFormatResponse,
)


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
    """Respuesta del flujo completo de carga y adaptación."""

    duplicate: bool = Field(
        default=False,
        description=(
            "Indica si el contenido ya estaba registrado."
        ),
    )

    formats: dict[
        GeneratedFormatType,
        GeneratedFormatResponse,
    ] = Field(
        min_length=1,
        description=(
            "Quiz y Flashcards producidos durante "
            "la adaptación del documento."
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
    estimated_time: str | None = Field(
        default=None,
        description=(
            "Tiempo estimado de estudio cuando esté disponible."
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