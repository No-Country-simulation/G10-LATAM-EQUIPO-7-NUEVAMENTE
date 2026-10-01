"""Schemas HTTP para solicitudes de adaptación educativa."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import GeneratedFormat
from app.schemas.common import BaseSchema

NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

AdaptationProfile = Literal[
    "beginner",
    "intermediate",
    "advanced",
]

AdaptationNiche = Literal[
    "general",
    "backend",
    "health",
    "legal",
    "business",
    "humanities",
]


class AdaptationRequest(BaseSchema):
    """Contexto pedagógico requerido para adaptar un documento.

    Frontend proporciona el documento y los parámetros pedagógicos.
    Backend decide internamente los formatos que deben generarse
    durante Sprint 2: Quiz y Flashcards.

    ``detail_level`` permanece como texto no vacío hasta que Frontend
    y Agentes acuerden un conjunto cerrado de valores.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    document_id: NonEmptyString = Field(
        description="Documento que será utilizado como fuente.",
    )

    profile: AdaptationProfile = Field(
        description="Perfil educativo del destinatario.",
    )

    niche: AdaptationNiche = Field(
        description="Área temática o contexto de aplicación.",
    )

    detail_level: NonEmptyString = Field(
        description="Nivel de detalle esperado durante la generación.",
    )

    learning_objective: NonEmptyString | None = Field(
        default=None,
        description=(
            "Objetivo de aprendizaje específico, cuando sea informado."
        ),
    )


class AdaptationResultResponse(BaseSchema):
    """Resultado resumido de un formato procesado."""

    format: GeneratedFormatType = Field(
        description="Formato educativo procesado.",
    )

    status: GeneratedFormatStatus = Field(
        description="Resultado de la generación del formato.",
    )

    error_message: str | None = Field(
        default=None,
        description="Detalle del fallo cuando el formato no fue generado.",
    )

    @classmethod
    def from_domain(
        cls,
        generated_format: GeneratedFormat,
    ) -> "AdaptationResultResponse":
        """Convierte una generación al contrato resumido de adaptación."""
        return cls(
            format=generated_format.format_type,
            status=generated_format.status,
            error_message=generated_format.error_message,
        )


class AdaptationResponse(BaseSchema):
    """Resultado de ejecutar la adaptación educativa."""

    document_id: NonEmptyString = Field(
        description="Documento que fue procesado.",
    )

    results: list[AdaptationResultResponse] = Field(
        min_length=1,
        description=(
            "Resultado de cada formato solicitado automáticamente."
        ),
    )