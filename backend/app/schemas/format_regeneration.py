"""Schemas HTTP para regeneración de formatos educativos."""

from typing import Literal

from pydantic import Field, field_validator

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
)
from app.schemas.common import BaseSchema


class FormatRegenerationRequest(BaseSchema):
    """Solicitud de regeneración de uno o varios formatos."""

    formats: list[
        GeneratedFormatType
    ] = Field(
        min_length=1,
        description=(
            "Formatos que deben iniciar un nuevo intento "
            "de generación."
        ),
    )

    @field_validator(
        "formats"
    )
    @classmethod
    def validate_unique_formats(
        cls,
        formats: list[
            GeneratedFormatType
        ],
    ) -> list[
        GeneratedFormatType
    ]:
        """Rechaza formatos repetidos dentro de la misma solicitud."""
        if len(formats) != len(set(formats)):
            raise ValueError(
                "formats no puede contener valores duplicados."
            )

        return formats


class FormatRegenerationAttemptResponse(
    BaseSchema
):
    """Intento nuevo registrado por una solicitud de regeneración."""

    format_id: str = Field(
        min_length=1,
    )
    status: GeneratedFormatStatus

    @classmethod
    def from_domain(
        cls,
        generated_format: GeneratedFormat,
    ) -> "FormatRegenerationAttemptResponse":
        """Convierte un intento persistido al contrato HTTP."""
        return cls(
            format_id=generated_format.format_id,
            status=generated_format.status,
        )


class FormatRegenerationResponse(BaseSchema):
    """Respuesta aceptada para una regeneración asíncrona."""

    document_id: str = Field(
        min_length=1,
    )
    status: Literal[
        "processing"
    ] = "processing"
    formats: dict[
        GeneratedFormatType,
        FormatRegenerationAttemptResponse,
    ]

    @classmethod
    def from_attempts(
        cls,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
    ) -> "FormatRegenerationResponse":
        """Construye la respuesta a partir de los nuevos intentos."""
        if not attempts:
            raise ValueError(
                "La respuesta requiere al menos un intento."
            )

        document_ids = {
            attempt.document_id
            for attempt in attempts
        }

        if len(document_ids) != 1:
            raise ValueError(
                "Todos los intentos deben pertenecer "
                "al mismo documento."
            )

        return cls(
            document_id=attempts[0].document_id,
            formats={
                attempt.format_type: (
                    FormatRegenerationAttemptResponse
                    .from_domain(
                        attempt
                    )
                )
                for attempt in attempts
            },
        )
