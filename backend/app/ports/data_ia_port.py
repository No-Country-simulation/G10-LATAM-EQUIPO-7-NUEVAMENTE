"""Puerto interno para evaluación de calidad mediante Data/IA."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatType,
)
from app.domain.format_evaluation import (
    EvaluationScores,
)
from app.domain.generated_content import (
    GeneratedContent,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GenerationContext,
)


class DataIAError(Exception):
    """Error durante una evaluación solicitada a Data/IA."""


@dataclass(frozen=True, slots=True)
class DataIAEvaluationInput:
    """Contrato interno necesario para llamar a Data/IA."""

    document_id: str
    format_type: GeneratedFormatType
    generated_content: GeneratedContent
    chunks_used: tuple[ChunkEvidence, ...]
    generation_context: GenerationContext


@dataclass(frozen=True, slots=True)
class DataIAEvaluationResult:
    """Resultado normalizado recibido desde Data/IA."""

    document_id: str
    format_type: GeneratedFormatType
    status: FormatEvaluationStatus
    scores: EvaluationScores
    unsupported_information: bool
    observations: tuple[str, ...]
    evaluator_version: str | None = None
    rubric_version: str | None = None


class DataIAPort(Protocol):
    """Operaciones de Data/IA requeridas por BackendAPI."""

    async def evaluate(
        self,
        request: DataIAEvaluationInput,
    ) -> DataIAEvaluationResult:
        """Evalúa la calidad de un formato generado."""
        ...