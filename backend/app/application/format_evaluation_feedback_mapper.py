"""Transforma Evaluation V2 persistida en feedback canónico para Agentes.

No ejecuta HTTP ni modifica estados. Evaluaciones V1, aprobadas o sin
observaciones accionables no generan solicitudes de corrección.
"""

from app.domain.format_evaluation import FormatEvaluation
from app.domain.revision_feedback import (
    FeedbackScores,
    RevisionFeedback,
    RevisionObservation,
    RevisionRecommendation,
    SemanticReview,
    UnsupportedClaim,
)


def build_revision_feedback(evaluation: FormatEvaluation) -> RevisionFeedback | None:
    """Convierte una evaluación V2 negativa con hallazgos en feedback tipado.

    Returns:
        RevisionFeedback si existe una señal accionable; de lo contrario None.
        No convierte evaluaciones V1 en V2 ni inventa recomendaciones.
    """
    if evaluation.verdict not in ("requires_revision", "rejected"):
        return None

    semantic = evaluation.semantic_evaluation
    if semantic is None or not (
        semantic.observations
        or semantic.recommendations
        or semantic.unsupported_information
    ):
        return None

    heuristic_scores = None
    if evaluation.heuristic_scores is not None:
        heuristic_scores = FeedbackScores(
            relevance=evaluation.heuristic_scores.relevance,
            coherence=evaluation.heuristic_scores.coherence,
            didactic_adaptation=evaluation.heuristic_scores.didactic_adaptation,
            content_support=evaluation.heuristic_scores.content_support,
        )

    semantic_scores = None
    if semantic.scores is not None:
        semantic_scores = FeedbackScores(
            relevance=semantic.scores.relevance,
            coherence=semantic.scores.coherence,
            didactic_adaptation=semantic.scores.didactic_adaptation,
            content_support=semantic.scores.content_support,
        )

    return RevisionFeedback(
        verdict=evaluation.verdict,
        heuristic_scores=heuristic_scores,
        semantic_evaluation=SemanticReview(
            status=semantic.status,
            scores=semantic_scores,
            observations=tuple(
                RevisionObservation(
                    dimension=item.dimension,
                    severity=item.severity,
                    message=item.message,
                    item_id=item.item_id,
                )
                for item in semantic.observations
            ),
            recommendations=tuple(
                RevisionRecommendation(
                    dimension=item.dimension,
                    message=item.message,
                    item_id=item.item_id,
                )
                for item in semantic.recommendations
            ),
            unsupported_information=tuple(
                UnsupportedClaim(
                    claim=item.claim,
                    reason=item.reason,
                    item_id=item.item_id,
                    related_chunk_ids=item.related_chunk_ids,
                )
                for item in semantic.unsupported_information
            ),
            error_code=semantic.error_code,
            error_message=semantic.error_message,
            model=semantic.model,
            prompt_version=semantic.prompt_version,
            latency_ms=semantic.latency_ms,
        ),
    )
