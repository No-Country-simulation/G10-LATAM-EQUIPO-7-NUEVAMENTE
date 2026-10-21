"""Pruebas unitarias del dominio de evaluaciones (V1 y V2)."""

import pytest

from app.domain.enums import FormatEvaluationStatus
from app.domain.format_evaluation import (
    EvaluationScores,
    FormatEvaluation,
    HeuristicScoresV2,
    SemanticEvaluationResult,
    SemanticObservation,
    SemanticRecommendation,
    SemanticScores,
    UnsupportedClaim,
)

# ---------------------------------------------------------------------------
# HeuristicScoresV2 / SemanticScores — rango 1.0-5.0
# ---------------------------------------------------------------------------


def test_heuristic_scores_v2_rejects_value_below_range() -> None:
    """Un score V2 menor a 1.0 es inválido."""
    with pytest.raises(ValueError, match="relevance"):
        HeuristicScoresV2(
            relevance=0.9,
            coherence=3.0,
            didactic_adaptation=3.0,
            content_support=3.0,
        )


def test_heuristic_scores_v2_rejects_value_above_range() -> None:
    """Un score V2 mayor a 5.0 es inválido."""
    with pytest.raises(ValueError, match="content_support"):
        HeuristicScoresV2(
            relevance=3.0,
            coherence=3.0,
            didactic_adaptation=3.0,
            content_support=5.1,
        )


def test_semantic_scores_accepts_boundary_values() -> None:
    """Los extremos 1.0 y 5.0 son válidos."""
    scores = SemanticScores(
        relevance=1.0,
        coherence=5.0,
        didactic_adaptation=1.0,
        content_support=5.0,
    )
    assert scores.relevance == 1.0
    assert scores.content_support == 5.0


# ---------------------------------------------------------------------------
# SemanticEvaluationResult — consistencia status/scores/error_code
# ---------------------------------------------------------------------------


def _scores() -> SemanticScores:
    return SemanticScores(
        relevance=4.0,
        coherence=4.0,
        didactic_adaptation=4.0,
        content_support=4.0,
    )


def test_semantic_evaluation_success_requires_scores() -> None:
    """status='success' sin scores debe rechazarse."""
    with pytest.raises(ValueError, match="scores"):
        SemanticEvaluationResult(status="success", scores=None)


def test_semantic_evaluation_success_rejects_error_code() -> None:
    """status='success' no debe traer error_code."""
    with pytest.raises(ValueError, match="error_code"):
        SemanticEvaluationResult(
            status="success",
            scores=_scores(),
            error_code="timeout",
        )


def test_semantic_evaluation_failed_requires_error_code() -> None:
    """status='failed' sin error_code debe rechazarse."""
    with pytest.raises(ValueError, match="error_code"):
        SemanticEvaluationResult(status="failed", scores=None)


def test_semantic_evaluation_failed_rejects_scores() -> None:
    """status='failed' no debe traer scores."""
    with pytest.raises(ValueError, match="scores"):
        SemanticEvaluationResult(
            status="failed",
            scores=_scores(),
            error_code="timeout",
        )


def test_semantic_evaluation_failed_rejects_not_configured() -> None:
    """error_code='not_configured' pertenece a 'unavailable', no a 'failed'."""
    with pytest.raises(ValueError, match="unavailable"):
        SemanticEvaluationResult(
            status="failed",
            error_code="not_configured",
        )


def test_semantic_evaluation_unavailable_requires_not_configured() -> None:
    """status='unavailable' debe usar error_code='not_configured'."""
    with pytest.raises(ValueError, match="not_configured"):
        SemanticEvaluationResult(
            status="unavailable",
            error_code="timeout",
        )


def test_semantic_evaluation_unavailable_rejects_scores() -> None:
    """status='unavailable' no debe traer scores."""
    with pytest.raises(ValueError, match="scores"):
        SemanticEvaluationResult(
            status="unavailable",
            scores=_scores(),
            error_code="not_configured",
        )


def test_semantic_evaluation_rejects_negative_latency() -> None:
    """latency_ms no puede ser negativo."""
    with pytest.raises(ValueError, match="latency_ms"):
        SemanticEvaluationResult(
            status="success",
            scores=_scores(),
            latency_ms=-1,
        )


def test_semantic_evaluation_success_is_valid_with_findings() -> None:
    """Un resultado 'success' con hallazgos estructurados es válido."""
    result = SemanticEvaluationResult(
        status="success",
        scores=_scores(),
        observations=(
            SemanticObservation(
                dimension="didactic_adaptation",
                severity="high",
                message="Usa jerga avanzada sin explicarla.",
                item_id="q1",
            ),
        ),
        recommendations=(
            SemanticRecommendation(
                dimension="didactic_adaptation",
                message="Explicar los conceptos básicos primero.",
                item_id="q1",
            ),
        ),
        unsupported_information=(
            UnsupportedClaim(
                claim="Docker reemplaza a Kubernetes.",
                reason="Los chunks no respaldan la afirmación.",
                related_chunk_ids=("chunk_1",),
            ),
        ),
        model="gemini-test",
        prompt_version="v0.1",
        latency_ms=120,
    )

    assert result.observations[0].severity == "high"
    assert result.recommendations[0].dimension == "didactic_adaptation"
    assert result.unsupported_information[0].related_chunk_ids == (
        "chunk_1",
    )


def test_semantic_observation_rejects_empty_message() -> None:
    """Una observación sin mensaje es inválida."""
    with pytest.raises(ValueError, match="message"):
        SemanticObservation(
            dimension="coherence",
            severity="low",
            message="   ",
        )


def test_unsupported_claim_rejects_empty_reason() -> None:
    """Una afirmación no respaldada debe traer una razón concreta."""
    with pytest.raises(ValueError, match="reason"):
        UnsupportedClaim(claim="Afirmación X.", reason="")


# ---------------------------------------------------------------------------
# FormatEvaluation — compatibilidad V1/V2 en la misma entidad
# ---------------------------------------------------------------------------


def test_format_evaluation_requires_at_least_one_signal() -> None:
    """Una evaluación completamente vacía (ni V1 ni V2) es inválida."""
    with pytest.raises(ValueError, match="al menos una señal"):
        FormatEvaluation(
            evaluation_id="eval_1",
            format_id="fmt_1",
        )


def test_format_evaluation_v1_requires_scores_when_status_present() -> None:
    """Un status V1 sin scores asociados es un dato incompleto inválido."""
    with pytest.raises(ValueError, match="scores"):
        FormatEvaluation(
            evaluation_id="eval_1",
            format_id="fmt_1",
            status=FormatEvaluationStatus.APPROVED,
        )


def test_format_evaluation_v1_only_is_valid_and_not_v2() -> None:
    """Una evaluación V1 completa sigue siendo válida y no se marca V2."""
    evaluation = FormatEvaluation(
        evaluation_id="eval_1",
        format_id="fmt_1",
        status=FormatEvaluationStatus.APPROVED,
        scores=EvaluationScores(
            relevance=5,
            coherence=5,
            didactic_adaptation=4,
            content_support=5,
        ),
    )

    assert evaluation.is_v2 is False
    assert evaluation.verdict is None
    assert evaluation.semantic_evaluation is None


def test_format_evaluation_v2_only_is_valid_and_marked_v2() -> None:
    """Una evaluación V2 'pura' (sin campos V1) es válida y se marca V2."""
    evaluation = FormatEvaluation(
        evaluation_id="eval_2",
        format_id="fmt_2",
        verdict="requires_revision",
        heuristic_scores=HeuristicScoresV2(
            relevance=4.0,
            coherence=4.0,
            didactic_adaptation=2.5,
            content_support=4.0,
        ),
        semantic_evaluation=SemanticEvaluationResult(
            status="unavailable",
            error_code="not_configured",
        ),
    )

    assert evaluation.is_v2 is True
    assert evaluation.status is None
    assert evaluation.scores is None


def test_format_evaluation_v2_with_null_verdict_and_only_semantic_signal() -> None:
    """verdict=None es válido si existe al menos semantic_evaluation."""
    evaluation = FormatEvaluation(
        evaluation_id="eval_3",
        format_id="fmt_3",
        semantic_evaluation=SemanticEvaluationResult(
            status="success",
            scores=_scores(),
        ),
    )

    assert evaluation.is_v2 is True
    assert evaluation.verdict is None
