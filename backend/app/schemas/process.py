"""Schemas HTTP relacionados con procesos."""

from datetime import datetime

from pydantic import Field

from app.domain.enums import ProcessStatus
from app.schemas.common import BaseSchema


class ProcessResponse(BaseSchema):
    """Estado público de un proceso de NuevaMente."""

    process_id: str = Field(
        min_length=1,
        description="Identificador único del proceso.",
    )
    document_id: str = Field(
        min_length=1,
        description="Documento asociado al proceso.",
    )
    status: ProcessStatus = Field(
        description="Estado actual del proceso.",
    )
    error_message: str | None = Field(
        default=None,
        description="Descripción del error cuando el proceso falla.",
    )
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None