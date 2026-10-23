"""Tests para Evaluation V2 builder."""

import pytest

from data_ai.evaluation.config import (
    EVALUATOR_VERSION,
    RUBRIC_VERSION,
)
from data_ai.evaluation.evaluation_v2_builder import (
    build_evaluation_response_v2,
)
from data_ai.schemas.evaluation import (
    EvaluacionReviewerContract,
)
from data_ai.schemas.format_evaluation import (
    EvaluationScores,
)
from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
    SemanticScores,
)


def _heuristic_result(
    status: str = "aprobado",
) -> EvaluacionReviewerContract:
    return EvaluacionReviewerContract(
        status=status,
        scores=EvaluationScores(
            relevancia=5,
            coherencia=4,
            adaptacion_didactica=3,
            informacion_respaldada=4,
        ),
        informacion_no_respaldada=False,
        observaciones=[
            "Resultado heurístico de prueba."
        ],
    )


def _semantic_success() -> SemanticEvaluationResult:
    return SemanticEvaluationResult(
        status="success",
        scores=SemanticScores(
            relevance=4.5,
            coherence=4.3,
            didactic_adaptation=4.0,
            content_support=4.2,
        ),
        observations=[],
        recommendations=[],
        unsupported_information=[],
        error_code=None,
        error_message=None,
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


def test_builder_maps_heuristic_result_to_v2():
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="tldr",
        heuristic_result=_heuristic_result(),
        semantic_evaluation=_semantic_success(),
    )

    assert result.document_id == "doc_123"
    assert result.format == "tldr"

    assert result.verdict == "approved"

    assert result.heuristic_scores is not None
    assert result.heuristic_scores.relevance == 5.0
    assert result.heuristic_scores.coherence == 4.0

    assert (
        result.heuristic_scores.didactic_adaptation
        == 3.0
    )

    assert (
        result.heuristic_scores.content_support
        == 4.0
    )


@pytest.mark.parametrize(
    (
        "legacy_status",
        "expected_verdict",
    ),
    [
        (
            "aprobado",
            "approved",
        ),
        (
            "requiere_revision",
            "requires_revision",
        ),
        (
            "rechazado",
            "requires_revision",
        ),
    ],
)
def test_builder_maps_all_legacy_verdicts(
    legacy_status,
    expected_verdict,
):
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="quiz",
        heuristic_result=_heuristic_result(
            legacy_status
        ),
        semantic_evaluation=_semantic_success(),
    )

    assert result.verdict == expected_verdict


def test_builder_preserves_semantic_result():
    semantic_result = _semantic_success()

    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="flashcards",
        heuristic_result=_heuristic_result(),
        semantic_evaluation=semantic_result,
    )

    assert (
        result.semantic_evaluation
        == semantic_result
    )


def test_failed_semantic_keeps_heuristic_verdict():
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="tldr",
        heuristic_result=_heuristic_result(
            "requiere_revision"
        ),
        semantic_evaluation=_semantic_failed(),
    )

    assert (
        result.verdict
        == "requires_revision"
    )

    assert (
        result.semantic_evaluation.status
        == "failed"
    )


def test_unavailable_semantic_keeps_heuristic_verdict():
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="video_script",
        heuristic_result=_heuristic_result(
            "rechazado"
        ),
        semantic_evaluation=(
            _semantic_unavailable()
        ),
    )

    assert result.verdict == "rejected"

    assert (
        result.semantic_evaluation.status
        == "unavailable"
    )


def test_missing_heuristic_produces_no_verdict_when_semantic_fails():
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="quiz",
        heuristic_result=None,
        semantic_evaluation=_semantic_failed(),
    )

    assert result.verdict is None
    assert result.heuristic_scores is None


def test_missing_heuristic_uses_valid_semantic_verdict():
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="quiz",
        heuristic_result=None,
        semantic_evaluation=_semantic_success(),
    )

    assert result.verdict == "approved"
    assert result.heuristic_scores is None

    assert (
        result.semantic_evaluation.status
        == "success"
    )

def test_builder_uses_current_versions_by_default():
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="tldr",
        heuristic_result=_heuristic_result(),
        semantic_evaluation=_semantic_success(),
    )

    assert (
        result.evaluator_version
        == EVALUATOR_VERSION
    )

    assert (
        result.rubric_version
        == RUBRIC_VERSION
    )


def test_builder_allows_explicit_versions():
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format="tldr",
        heuristic_result=_heuristic_result(),
        semantic_evaluation=_semantic_success(),
        evaluator_version="2.0.0-test",
        rubric_version="2.0.0-test",
    )

    assert (
        result.evaluator_version
        == "2.0.0-test"
    )

    assert (
        result.rubric_version
        == "2.0.0-test"
    )


@pytest.mark.parametrize(
    "content_format",
    [
        "quiz",
        "flashcards",
        "tldr",
        "video_script",
    ],
)
def test_builder_supports_all_formats(
    content_format,
):
    result = build_evaluation_response_v2(
        document_id="doc_123",
        content_format=content_format,
        heuristic_result=_heuristic_result(),
        semantic_evaluation=_semantic_success(),
    )

    assert result.format == content_format