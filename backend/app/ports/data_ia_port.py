"""Puertos tipados para evaluación de calidad mediante Data/IA (V1.1 y V2)."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import FormatEvaluationStatus, GeneratedFormatType
from app.domain.format_evaluation import (
    EvaluationScores,
    EvaluationVerdict,
    HeuristicScoresV2,
    SemanticEvaluationResult,
)
from app.domain.generated_content import GeneratedContent
from app.domain.generated_format import ChunkEvidence, GenerationContext


class DataIAError(Exception):
    """Error de transporte o contrato al solicitar una evaluación a Data/IA."""


@dataclass(frozen=True, slots=True)
class DataIAEvaluationInput:
    """Solicitud canónica: contenido generado, contexto y evidencia RAG."""

    document_id: str
    format_type: GeneratedFormatType
    generated_content: GeneratedContent
    chunks_used: tuple[ChunkEvidence, ...]
    generation_context: GenerationContext


@dataclass(frozen=True, slots=True)
class DataIAEvaluationResult:
    """Respuesta normalizada del evaluador heurístico V1.1 (legacy)."""

    document_id: str
    format_type: GeneratedFormatType
    status: FormatEvaluationStatus
    scores: EvaluationScores
    unsupported_information: bool
    observations: tuple[str, ...]
    evaluator_version: str | None = None
    rubric_version: str | None = None


@dataclass(frozen=True, slots=True)
class DataIAV2EvaluationResult:
    """Respuesta V2 sin combinar puntuaciones heurísticas y semánticas.

    ``verdict`` puede ser None cuando no existen señales suficientes.
    ``semantic_evaluation.status`` es técnico, no un veredicto pedagógico.
    """

    document_id: str
    format_type: GeneratedFormatType
    verdict: EvaluationVerdict | None
    heuristic_scores: HeuristicScoresV2 | None
    semantic_evaluation: SemanticEvaluationResult
    evaluator_version: str
    rubric_version: str


class DataIAPort(Protocol):
    """Servicio de evaluación independiente de HTTP y persistencia."""

    async def evaluate(
        self,
        request: DataIAEvaluationInput,
    ) -> DataIAEvaluationResult | DataIAV2EvaluationResult:
        """Solicita una evaluación de calidad para un formato."""
        ...
