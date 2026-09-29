"""Puerto de integración entre BackendAPI y Agentes."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    GeneratedContent,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GenerationContext,
)


class AgentsError(Exception):
    """Error durante una operación solicitada a Agentes."""


@dataclass(frozen=True, slots=True)
class AgentGenerationInput:
    """Solicitud normalizada de generación educativa."""

    document_id: str
    formats: tuple[GeneratedFormatType, ...]
    generation_context: GenerationContext


@dataclass(frozen=True, slots=True)
class AgentGeneratedFormatResult:
    """Resultado atómico recibido desde Agentes."""

    format_type: GeneratedFormatType
    status: GeneratedFormatStatus
    content: GeneratedContent | None
    chunks_used: tuple[ChunkEvidence, ...]
    error_message: str | None = None

    def __post_init__(self) -> None:
        if (
            self.status
            == GeneratedFormatStatus.SUCCESS
        ):
            if self.content is None:
                raise ValueError(
                    "Agentes debe devolver content "
                    "para una generación exitosa."
                )

            if not self.chunks_used:
                raise ValueError(
                    "Agentes debe devolver chunks_used completos "
                    "para una generación exitosa."
                )


@dataclass(frozen=True, slots=True)
class AgentGenerationResult:
    """Respuesta completa de una solicitud de generación."""

    document_id: str
    results: tuple[
        AgentGeneratedFormatResult,
        ...
    ]


class AgentsPort(Protocol):
    """Operaciones de Agentes requeridas por BackendAPI."""

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
        """Genera Quiz y/o Flashcards para un documento indexado."""
        ...