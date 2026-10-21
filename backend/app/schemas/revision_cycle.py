"""Contratos HTTP de consulta de ciclos de revisión y evaluación."""

from datetime import datetime

from app.application.format_revision_history_service import (
    FormatRevisionCycle,
    FormatRevisionHistory,
    RevisionHistoryItem,
)
from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.format_evaluation import (
    EvaluationScores,
    EvaluationVerdict,
    FormatEvaluation,
    HeuristicScoresV2,
    SemanticEvaluationResult,
)
from app.schemas.common import BaseSchema


class RevisionEvaluationResponse(BaseSchema):
    """Evaluación histórica V1 o V2, sin perder la información semántica."""

    evaluation_id: str
    format_id: str
    status: FormatEvaluationStatus | None
    scores: EvaluationScores | None
    verdict: EvaluationVerdict | None
    heuristic_scores: HeuristicScoresV2 | None
    semantic_evaluation: SemanticEvaluationResult | None
    observations: tuple[str, ...]
    unsupported_information: bool
    evaluator_version: str | None
    rubric_version: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, value: FormatEvaluation) -> "RevisionEvaluationResponse":
        """Convierte la entidad persistida a su contrato HTTP tipado."""
        return cls(
            evaluation_id=value.evaluation_id,
            format_id=value.format_id,
            status=value.status,
            scores=value.scores,
            verdict=value.verdict,
            heuristic_scores=value.heuristic_scores,
            semantic_evaluation=value.semantic_evaluation,
            observations=value.observations,
            unsupported_information=value.unsupported_information,
            evaluator_version=value.evaluator_version,
            rubric_version=value.rubric_version,
            created_at=value.created_at,
        )


class RevisionFormatResponse(BaseSchema):
    """Identidad y estado de una versión, junto a sus evaluaciones."""

    format_id: str
    status: GeneratedFormatStatus
    revision_of_format_id: str | None
    created_at: datetime
    updated_at: datetime
    evaluations: tuple[RevisionEvaluationResponse, ...]

    @classmethod
    def from_domain(cls, item: RevisionHistoryItem) -> "RevisionFormatResponse":
        """Serializa una versión persistida y su historial de evaluaciones."""
        value = item.generated_format
        return cls(
            format_id=value.format_id,
            status=value.status,
            revision_of_format_id=value.revision_of_format_id,
            created_at=value.created_at,
            updated_at=value.updated_at,
            evaluations=tuple(
                RevisionEvaluationResponse.from_domain(e) for e in item.evaluations
            ),
        )


class RevisionCycleResponse(BaseSchema):
    """Ciclo con su revisión opcional y resultado vigente."""

    original: RevisionFormatResponse
    revision: RevisionFormatResponse | None
    latest_evaluation: RevisionEvaluationResponse | None

    @classmethod
    def from_domain(cls, value: FormatRevisionCycle) -> "RevisionCycleResponse":
        """Convierte un ciclo del caso de uso a un contrato público."""
        return cls(
            original=RevisionFormatResponse.from_domain(value.original),
            revision=(
                RevisionFormatResponse.from_domain(value.revision)
                if value.revision is not None else None
            ),
            latest_evaluation=(
                RevisionEvaluationResponse.from_domain(value.latest_evaluation)
                if value.latest_evaluation is not None else None
            ),
        )


class RevisionHistoryResponse(BaseSchema):
    """Respuesta histórica ordenada desde el ciclo más reciente."""

    document_id: str
    format_type: GeneratedFormatType
    cycles: tuple[RevisionCycleResponse, ...]

    @classmethod
    def from_domain(cls, value: FormatRevisionHistory) -> "RevisionHistoryResponse":
        """Convierte el resultado de consulta completo a JSON tipado."""
        return cls(
            document_id=value.document_id,
            format_type=value.format_type,
            cycles=tuple(RevisionCycleResponse.from_domain(c) for c in value.cycles),
        )
