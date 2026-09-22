"""Schemas HTTP relacionados con documentos."""

from datetime import datetime

from pydantic import Field

from app.domain.enums import DocumentStatus
from app.schemas.common import BaseSchema


class DocumentUploadResponse(BaseSchema):
    """Respuesta después de recibir temporalmente un documento."""

    filename: str = Field(
        min_length=1,
        description="Nombre saneado utilizado para el almacenamiento temporal.",
    )
    original_filename: str = Field(
        min_length=1,
        description="Nombre original recibido desde el cliente.",
    )
    content_type: str | None = Field(
        default=None,
        description="Tipo MIME informado durante la carga.",
    )
    size_bytes: int = Field(
        ge=0,
        description="Tamaño recibido del documento en bytes.",
    )

class DocumentCreatedResponse(BaseSchema):
    """Respuesta después de registrar correctamente un documento."""

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