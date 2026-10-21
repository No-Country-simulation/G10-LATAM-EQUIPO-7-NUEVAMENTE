"""Schemas HTTP para generación pública de formatos educativos."""

from typing import Literal

from pydantic import Field, field_validator

from app.domain.enums import GeneratedFormatType
from app.domain.generated_format import GeneratedFormat
from app.schemas.adaptation import (
    AdaptationNiche,
    AdaptationProfile,
    NonEmptyString,
)
from app.schemas.common import BaseSchema


class PublicFormatGenerationRequest(BaseSchema):
    """Solicitud pública para generar uno o varios formatos."""

    formats: list[GeneratedFormatType] = Field(
        min_length=1,
        description="Formatos que se desean generar."
    )
    profile: AdaptationProfile = Field(..., description="Perfil del estudiante.")
    niche: AdaptationNiche = Field(..., description="Área temática.")
    detail_level: NonEmptyString = Field(..., description="Nivel de detalle.")
    learning_objective: str | None = Field(None, description="Objetivo opcional.")

    @field_validator("formats")
    @classmethod
    def validate_unique_formats(
        cls, formats: list[GeneratedFormatType]
    ) -> list[GeneratedFormatType]:
        """Rechaza formatos repetidos dentro de la misma solicitud."""
        if len(formats) != len(set(formats)):
            raise ValueError("formats no puede contener valores duplicados.")
        return formats


class FormatGenerationAttemptResponse(BaseSchema):
    """Intento de generación registrado."""
    
    format_id: str = Field(min_length=1)
    status: str = Field(min_length=1)

    @classmethod
    def from_domain(cls, generated_format: GeneratedFormat) -> "FormatGenerationAttemptResponse":
        return cls(
            format_id=generated_format.format_id,
            status=generated_format.status.value,
        )


class FormatGenerationResponse(BaseSchema):
    """Respuesta aceptada para una generación asíncrona."""

    document_id: str = Field(min_length=1)
    status: Literal["processing"] = "processing"
    formats: dict[GeneratedFormatType, FormatGenerationAttemptResponse]

    @classmethod
    def from_attempts(cls, attempts: tuple[GeneratedFormat, ...]) -> "FormatGenerationResponse":
        if not attempts:
            raise ValueError("La respuesta requiere al menos un intento.")
            
        return cls(
            document_id=attempts[0].document_id,
            formats={
                attempt.format_type: FormatGenerationAttemptResponse.from_domain(attempt)
                for attempt in attempts
            },
        )