from data_ai.evaluation.evaluation_v2_decision import (
    derive_semantic_verdict,
    resolve_evaluation_v2_verdict,
)
from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
    SemanticScores,
)


def _semantic_result(
    *,
    relevance=5.0,
    coherence=5.0,
    didactic_adaptation=5.0,
    content_support=5.0,
):
    return SemanticEvaluationResult(
        status="success",
        scores=SemanticScores(
            relevance=relevance,
            coherence=coherence,
            didactic_adaptation=didactic_adaptation,
            content_support=content_support,
        ),
        observations=[],
        recommendations=[],
        unsupported_information=[],
        error_code=None,
        error_message=None,
        model="test-model",
        prompt_version="test-prompt",
        latency_ms=1,
    )


def test_semantic_scores_all_high_are_approved():
    result = derive_semantic_verdict(
        _semantic_result().scores
    )

    assert result == "approved"


def test_semantic_score_below_four_requires_revision():
    result = derive_semantic_verdict(
        _semantic_result(
            relevance=3.5,
        ).scores
    )

    assert result == "requires_revision"


def test_semantic_score_two_or_less_is_rejected():
    result = derive_semantic_verdict(
        _semantic_result(
            content_support=2.0,
        ).scores
    )

    assert result == "rejected"


def test_matching_approved_signals_are_approved():
    result = resolve_evaluation_v2_verdict(
        heuristic_verdict="approved",
        semantic_evaluation=_semantic_result(),
    )

    assert result == "approved"


def test_matching_rejected_signals_are_rejected():
    result = resolve_evaluation_v2_verdict(
        heuristic_verdict="rejected",
        semantic_evaluation=_semantic_result(
            content_support=1.0,
        ),
    )

    assert result == "rejected"


def test_disagreement_becomes_requires_revision():
    result = resolve_evaluation_v2_verdict(
        heuristic_verdict="rejected",
        semantic_evaluation=_semantic_result(),
    )

    assert result == "requires_revision"


def test_semantic_only_signal_can_produce_verdict():
    result = resolve_evaluation_v2_verdict(
        heuristic_verdict=None,
        semantic_evaluation=_semantic_result(),
    )

    assert result == "approved"


def test_unavailable_semantic_falls_back_to_heuristic():
    semantic = SemanticEvaluationResult(
        status="unavailable",
        scores=None,
        observations=[],
        recommendations=[],
        unsupported_information=[],
        error_code="not_configured",
        error_message="Provider not configured.",
        model=None,
        prompt_version="test-prompt",
        latency_ms=1,
    )

    result = resolve_evaluation_v2_verdict(
        heuristic_verdict="rejected",
        semantic_evaluation=semantic,
    )

    assert result == "rejected"


def test_failed_semantic_falls_back_to_heuristic():
    semantic = SemanticEvaluationResult(
        status="failed",
        scores=None,
        observations=[],
        recommendations=[],
        unsupported_information=[],
        error_code="provider_error",
        error_message="Provider failed.",
        model="test-model",
        prompt_version="test-prompt",
        latency_ms=1,
    )

    result = resolve_evaluation_v2_verdict(
        heuristic_verdict="requires_revision",
        semantic_evaluation=semantic,
    )

    assert result == "requires_revision"