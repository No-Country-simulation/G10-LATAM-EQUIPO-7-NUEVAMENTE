"""Schemas HTTP para solicitudes de adaptación educativa."""

from typing import Annotated, Literal

from pydantic import (
    ConfigDict,
    Field,
    StringConstraints,
)

from app.domain.enums import ProcessStatus
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


class AdaptationAcceptedResponse(BaseSchema):
    """Respuesta provisional aún no utilizada por un endpoint operativo."""

    process_id: str
    document_id: str
    status: ProcessStatus