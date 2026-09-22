"""Schemas HTTP relacionados con documentos."""

from datetime import datetime

from pydantic import Field

from app.domain.enums import DocumentStatus
from app.schemas.common import BaseSchema


class DocumentCreatedResponse(BaseSchema):
    """Respuesta después de identificar correctamente un documento."""

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
    duplicate: bool = Field(
        default=False,
        description="Indica si el contenido ya estaba registrado.",
    )


class DocumentResponse(DocumentCreatedResponse):
    """Información pública detallada de un documento."""

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