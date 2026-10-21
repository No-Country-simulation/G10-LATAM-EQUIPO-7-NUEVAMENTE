"""Tests para Evaluation Contract V2."""

import pytest
from pydantic import ValidationError

from data_ai.schemas.evaluation_v2 import (
    EvaluationResponseV2,
    HeuristicScoresV2,
)
from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
    SemanticScores,
)


def _heuristic_scores() -> HeuristicScoresV2:
    return HeuristicScoresV2(
        relevance=4.0,
        coherence=4.0,
        didactic_adaptation=3.0,
        content_support=4.0,
    )


def _semantic_success() -> SemanticEvaluationResult:
    return SemanticEvaluationResult(
        status="success",
        scores=SemanticScores(
            relevance=4.5,
            coherence=4.4,
            didactic_adaptation=4.0,
            content_support=4.2,
        ),
        observations=[],
        recommendations=[],
        unsupported_information=[],
        model="fake-model",
        prompt_version="semantic-evaluator-v0.1",
        latency_ms=10,
    )


def _semantic_failed() -> SemanticEvaluationResult:
    return SemanticEvaluationResult(
        status="failed",
        scores=None,
        observations=[],
        recommendations=[],
        unsupported_information=[],
        error_code="provider_error",
        error_message="Provider failed.",
        model="fake-model",
        prompt_version="semantic-evaluator-v0.1",
        latency_ms=10,
    )


def _semantic_unavailable() -> SemanticEvaluationResult:
    return SemanticEvaluationResult(
        status="unavailable",
        scores=None,
        observations=[],
        recommendations=[],
        unsupported_information=[],
        error_code="not_configured",
        error_message="Provider not configured.",
        model=None,
        prompt_version="semantic-evaluator-v0.1",
        latency_ms=0,
    )


def test_heuristic_scores_accept_valid_values():
    scores = _heuristic_scores()

    assert scores.relevance == 4.0
    assert scores.coherence == 4.0
    assert scores.didactic_adaptation == 3.0
    assert scores.content_support == 4.0


@pytest.mark.parametrize(
    "field",
    [
        "relevance",
        "coherence",
        "didactic_adaptation",
        "content_support",
    ],
)
def test_heuristic_scores_reject_values_below_one(
    field,
):
    payload = {
        "relevance": 4.0,
        "coherence": 4.0,
        "didactic_adaptation": 4.0,
        "content_support": 4.0,
    }

    payload[field] = 0.9

    with pytest.raises(ValidationError):
        HeuristicScoresV2(**payload)


@pytest.mark.parametrize(
    "field",
    [
        "relevance",
        "coherence",
        "didactic_adaptation",
        "content_support",
    ],
)
def test_heuristic_scores_reject_values_above_five(
    field,
):
    payload = {
        "relevance": 4.0,
        "coherence": 4.0,
        "didactic_adaptation": 4.0,
        "content_support": 4.0,
    }

    payload[field] = 5.1

    with pytest.raises(ValidationError):
        HeuristicScoresV2(**payload)


@pytest.mark.parametrize(
    "verdict",
    [
        "approved",
        "requires_revision",
        "rejected",
    ],
)
def test_response_accepts_canonical_verdicts(
    verdict,
):
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict=verdict,
        heuristic_scores=_heuristic_scores(),
        semantic_evaluation=_semantic_success(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    assert result.verdict == verdict


@pytest.mark.parametrize(
    "legacy_verdict",
    [
        "aprobado",
        "requiere_revision",
        "rechazado",
    ],
)
def test_response_rejects_legacy_verdict_vocabulary(
    legacy_verdict,
):
    with pytest.raises(ValidationError):
        EvaluationResponseV2(
            document_id="doc_123",
            format="tldr",
            verdict=legacy_verdict,
            heuristic_scores=_heuristic_scores(),
            semantic_evaluation=_semantic_success(),
            evaluator_version="2.0.0",
            rubric_version="1.0.0",
        )


def test_response_keeps_semantic_evaluation_nested():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict="approved",
        heuristic_scores=_heuristic_scores(),
        semantic_evaluation=_semantic_success(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    dumped = result.model_dump()

    assert "semantic_evaluation" in dumped
    assert "scores" in dumped["semantic_evaluation"]

    assert (
        dumped["semantic_evaluation"]["status"]
        == "success"
    )


def test_failed_semantic_can_use_heuristic_fallback():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict="requires_revision",
        heuristic_scores=_heuristic_scores(),
        semantic_evaluation=_semantic_failed(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    assert result.verdict == "requires_revision"
    assert result.semantic_evaluation.status == "failed"


def test_unavailable_semantic_can_use_heuristic_fallback():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict="requires_revision",
        heuristic_scores=_heuristic_scores(),
        semantic_evaluation=_semantic_unavailable(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    assert result.verdict == "requires_revision"

    assert (
        result.semantic_evaluation.status
        == "unavailable"
    )


def test_semantic_success_can_produce_verdict_without_heuristic():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict="approved",
        heuristic_scores=None,
        semantic_evaluation=_semantic_success(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    assert result.verdict == "approved"


def test_no_valid_signal_requires_null_verdict():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict=None,
        heuristic_scores=None,
        semantic_evaluation=_semantic_failed(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    assert result.verdict is None


def test_no_valid_signal_rejects_fabricated_verdict():
    with pytest.raises(
        ValidationError,
        match="verdict must be None",
    ):
        EvaluationResponseV2(
            document_id="doc_123",
            format="tldr",
            verdict="rejected",
            heuristic_scores=None,
            semantic_evaluation=_semantic_failed(),
            evaluator_version="2.0.0",
            rubric_version="1.0.0",
        )


def test_unavailable_semantic_without_heuristic_requires_null_verdict():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict=None,
        heuristic_scores=None,
        semantic_evaluation=_semantic_unavailable(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    assert result.verdict is None


@pytest.mark.parametrize(
    "content_format",
    [
        "quiz",
        "flashcards",
        "tldr",
        "video_script",
    ],
)
def test_response_supports_all_four_formats(
    content_format,
):
    result = EvaluationResponseV2(
        document_id="doc_123",
        format=content_format,
        verdict="approved",
        heuristic_scores=_heuristic_scores(),
        semantic_evaluation=_semantic_success(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    assert result.format == content_format


def test_response_does_not_expose_final_score():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict="approved",
        heuristic_scores=_heuristic_scores(),
        semantic_evaluation=_semantic_success(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    dumped = result.model_dump()

    assert "final_score" not in dumped
    assert "combined_score" not in dumped
    assert "weighted_score" not in dumped


def test_response_does_not_expose_backend_cycle_metadata():
    result = EvaluationResponseV2(
        document_id="doc_123",
        format="tldr",
        verdict="approved",
        heuristic_scores=_heuristic_scores(),
        semantic_evaluation=_semantic_success(),
        evaluator_version="2.0.0",
        rubric_version="1.0.0",
    )

    dumped = result.model_dump()

    assert "evaluation_id" not in dumped
    assert "attempt" not in dumped
    assert "max_attempts" not in dumped
    assert "history" not in dumped