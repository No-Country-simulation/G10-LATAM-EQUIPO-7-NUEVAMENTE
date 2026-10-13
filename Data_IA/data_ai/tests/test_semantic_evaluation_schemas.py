"""Tests para los schemas internos de evaluación semántica.

Estos tests validan:
- límites de scores;
- valores permitidos de dimensión, severidad y estado;
- invariantes entre status, scores y error_code;
- serialización básica de observaciones, recomendaciones y claims.
"""

import pytest
from pydantic import ValidationError

from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
    SemanticObservation,
    SemanticRecommendation,
    SemanticScores,
    UnsupportedClaim,
)


def _valid_scores() -> SemanticScores:
    """Crea scores semánticos válidos reutilizables."""
    return SemanticScores(
        relevance=4.5,
        coherence=4.2,
        didactic_adaptation=3.8,
        content_support=4.1,
    )


# ============================================================
# SemanticScores
# ============================================================


def test_semantic_scores_accept_valid_values():
    scores = _valid_scores()

    assert scores.relevance == 4.5
    assert scores.coherence == 4.2
    assert scores.didactic_adaptation == 3.8
    assert scores.content_support == 4.1


@pytest.mark.parametrize(
    "field_name",
    [
        "relevance",
        "coherence",
        "didactic_adaptation",
        "content_support",
    ],
)
def test_semantic_scores_accept_lower_boundary(field_name):
    payload = {
        "relevance": 3.0,
        "coherence": 3.0,
        "didactic_adaptation": 3.0,
        "content_support": 3.0,
    }
    payload[field_name] = 1.0

    scores = SemanticScores(**payload)

    assert getattr(scores, field_name) == 1.0


@pytest.mark.parametrize(
    "field_name",
    [
        "relevance",
        "coherence",
        "didactic_adaptation",
        "content_support",
    ],
)
def test_semantic_scores_accept_upper_boundary(field_name):
    payload = {
        "relevance": 3.0,
        "coherence": 3.0,
        "didactic_adaptation": 3.0,
        "content_support": 3.0,
    }
    payload[field_name] = 5.0

    scores = SemanticScores(**payload)

    assert getattr(scores, field_name) == 5.0


@pytest.mark.parametrize(
    "field_name",
    [
        "relevance",
        "coherence",
        "didactic_adaptation",
        "content_support",
    ],
)
def test_semantic_scores_reject_values_below_minimum(field_name):
    payload = {
        "relevance": 3.0,
        "coherence": 3.0,
        "didactic_adaptation": 3.0,
        "content_support": 3.0,
    }
    payload[field_name] = 0.9

    with pytest.raises(ValidationError):
        SemanticScores(**payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "relevance",
        "coherence",
        "didactic_adaptation",
        "content_support",
    ],
)
def test_semantic_scores_reject_values_above_maximum(field_name):
    payload = {
        "relevance": 3.0,
        "coherence": 3.0,
        "didactic_adaptation": 3.0,
        "content_support": 3.0,
    }
    payload[field_name] = 5.1

    with pytest.raises(ValidationError):
        SemanticScores(**payload)


# ============================================================
# SemanticObservation
# ============================================================


def test_semantic_observation_accepts_valid_payload():
    observation = SemanticObservation(
        dimension="didactic_adaptation",
        severity="high",
        message=(
            "El contenido utiliza conceptos avanzados "
            "sin explicación previa."
        ),
        item_id="q2",
    )

    assert observation.dimension == "didactic_adaptation"
    assert observation.severity == "high"
    assert observation.item_id == "q2"


def test_semantic_observation_allows_item_id_none():
    observation = SemanticObservation(
        dimension="coherence",
        severity="medium",
        message="La estructura general presenta un salto lógico.",
    )

    assert observation.item_id is None


def test_semantic_observation_rejects_invalid_dimension():
    with pytest.raises(ValidationError):
        SemanticObservation(
            dimension="accuracy",
            severity="medium",
            message="Problema de prueba.",
        )


def test_semantic_observation_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        SemanticObservation(
            dimension="coherence",
            severity="critical",
            message="Problema de prueba.",
        )


def test_semantic_observation_rejects_empty_message():
    with pytest.raises(ValidationError):
        SemanticObservation(
            dimension="coherence",
            severity="medium",
            message="",
        )


# ============================================================
# SemanticRecommendation
# ============================================================


def test_semantic_recommendation_accepts_valid_payload():
    recommendation = SemanticRecommendation(
        dimension="didactic_adaptation",
        message=(
            "Explicar primero qué es un contenedor antes "
            "de introducir orquestación."
        ),
        item_id="q2",
    )

    assert recommendation.dimension == "didactic_adaptation"
    assert recommendation.item_id == "q2"


def test_semantic_recommendation_allows_item_id_none():
    recommendation = SemanticRecommendation(
        dimension="relevance",
        message="Reorientar el contenido hacia el objetivo principal.",
    )

    assert recommendation.item_id is None


def test_semantic_recommendation_rejects_invalid_dimension():
    with pytest.raises(ValidationError):
        SemanticRecommendation(
            dimension="pedagogy",
            message="Ajustar el contenido.",
        )


def test_semantic_recommendation_rejects_empty_message():
    with pytest.raises(ValidationError):
        SemanticRecommendation(
            dimension="relevance",
            message="",
        )


# ============================================================
# UnsupportedClaim
# ============================================================


def test_unsupported_claim_accepts_valid_payload():
    claim = UnsupportedClaim(
        claim="Docker reemplaza completamente a Kubernetes.",
        reason=(
            "Los chunks no respaldan una relación de reemplazo "
            "entre ambas tecnologías."
        ),
        item_id="q3",
        related_chunk_ids=[
            "chunk_001",
            "chunk_002",
        ],
    )

    assert claim.item_id == "q3"
    assert claim.related_chunk_ids == [
        "chunk_001",
        "chunk_002",
    ]


def test_unsupported_claim_defaults_related_chunk_ids_to_empty_list():
    claim = UnsupportedClaim(
        claim="Afirmación no respaldada.",
        reason="No existe evidencia suficiente.",
    )

    assert claim.related_chunk_ids == []
    assert claim.item_id is None


def test_unsupported_claim_uses_independent_default_lists():
    first = UnsupportedClaim(
        claim="Primera afirmación.",
        reason="Sin evidencia.",
    )

    second = UnsupportedClaim(
        claim="Segunda afirmación.",
        reason="Sin evidencia.",
    )

    first.related_chunk_ids.append("chunk_001")

    assert first.related_chunk_ids == ["chunk_001"]
    assert second.related_chunk_ids == []


def test_unsupported_claim_rejects_empty_claim():
    with pytest.raises(ValidationError):
        UnsupportedClaim(
            claim="",
            reason="No existe evidencia suficiente.",
        )


def test_unsupported_claim_rejects_empty_reason():
    with pytest.raises(ValidationError):
        UnsupportedClaim(
            claim="Afirmación de prueba.",
            reason="",
        )


# ============================================================
# SemanticEvaluationResult - success
# ============================================================


def test_semantic_result_success_accepts_scores():
    result = SemanticEvaluationResult(
        status="success",
        scores=_valid_scores(),
    )

    assert result.status == "success"
    assert result.scores is not None
    assert result.error_code is None


def test_semantic_result_success_accepts_complete_payload():
    result = SemanticEvaluationResult(
        status="success",
        scores=_valid_scores(),
        observations=[
            SemanticObservation(
                dimension="didactic_adaptation",
                severity="medium",
                message="El nivel puede simplificarse.",
            )
        ],
        recommendations=[
            SemanticRecommendation(
                dimension="didactic_adaptation",
                message="Definir los conceptos avanzados.",
            )
        ],
        unsupported_information=[
            UnsupportedClaim(
                claim="Afirmación no sustentada.",
                reason="No está respaldada por los chunks.",
            )
        ],
        model="semantic-model",
        prompt_version="semantic-evaluator-v0.1",
        latency_ms=850,
    )

    assert result.status == "success"
    assert len(result.observations) == 1
    assert len(result.recommendations) == 1
    assert len(result.unsupported_information) == 1
    assert result.latency_ms == 850


def test_semantic_result_success_requires_scores():
    with pytest.raises(
        ValidationError,
        match="must include scores",
    ):
        SemanticEvaluationResult(
            status="success",
            scores=None,
        )


def test_semantic_result_success_rejects_error_code():
    with pytest.raises(
        ValidationError,
        match="must not include error_code",
    ):
        SemanticEvaluationResult(
            status="success",
            scores=_valid_scores(),
            error_code="provider_error",
        )


# ============================================================
# SemanticEvaluationResult - failed
# ============================================================


@pytest.mark.parametrize(
    "error_code",
    [
        "timeout",
        "provider_error",
        "invalid_output",
    ],
)
def test_semantic_result_failed_accepts_valid_error_codes(
    error_code,
):
    result = SemanticEvaluationResult(
        status="failed",
        scores=None,
        error_code=error_code,
        error_message="Semantic evaluation failed.",
    )

    assert result.status == "failed"
    assert result.scores is None
    assert result.error_code == error_code


def test_semantic_result_failed_requires_error_code():
    with pytest.raises(
        ValidationError,
        match="must include error_code",
    ):
        SemanticEvaluationResult(
            status="failed",
            scores=None,
        )


def test_semantic_result_failed_rejects_scores():
    with pytest.raises(
        ValidationError,
        match="must not include scores",
    ):
        SemanticEvaluationResult(
            status="failed",
            scores=_valid_scores(),
            error_code="timeout",
        )


def test_semantic_result_failed_rejects_not_configured():
    with pytest.raises(
        ValidationError,
        match="must use status='unavailable'",
    ):
        SemanticEvaluationResult(
            status="failed",
            scores=None,
            error_code="not_configured",
        )


# ============================================================
# SemanticEvaluationResult - unavailable
# ============================================================


def test_semantic_result_unavailable_accepts_not_configured():
    result = SemanticEvaluationResult(
        status="unavailable",
        scores=None,
        error_code="not_configured",
        error_message="Semantic evaluator is not configured.",
    )

    assert result.status == "unavailable"
    assert result.scores is None
    assert result.error_code == "not_configured"


def test_semantic_result_unavailable_rejects_scores():
    with pytest.raises(
        ValidationError,
        match="must not include scores",
    ):
        SemanticEvaluationResult(
            status="unavailable",
            scores=_valid_scores(),
            error_code="not_configured",
        )


@pytest.mark.parametrize(
    "error_code",
    [
        None,
        "timeout",
        "provider_error",
        "invalid_output",
    ],
)
def test_semantic_result_unavailable_requires_not_configured(
    error_code,
):
    with pytest.raises(
        ValidationError,
        match="must use error_code='not_configured'",
    ):
        SemanticEvaluationResult(
            status="unavailable",
            scores=None,
            error_code=error_code,
        )


# ============================================================
# Additional validation
# ============================================================


def test_semantic_result_rejects_invalid_status():
    with pytest.raises(ValidationError):
        SemanticEvaluationResult(
            status="pending",
            scores=None,
        )


def test_semantic_result_rejects_negative_latency():
    with pytest.raises(ValidationError):
        SemanticEvaluationResult(
            status="success",
            scores=_valid_scores(),
            latency_ms=-1,
        )


def test_semantic_result_uses_independent_default_lists():
    first = SemanticEvaluationResult(
        status="success",
        scores=_valid_scores(),
    )

    second = SemanticEvaluationResult(
        status="success",
        scores=_valid_scores(),
    )

    first.observations.append(
        SemanticObservation(
            dimension="coherence",
            severity="low",
            message="Observación de prueba.",
        )
    )

    assert len(first.observations) == 1
    assert second.observations == []


def test_semantic_result_serializes_with_model_dump():
    result = SemanticEvaluationResult(
        status="success",
        scores=_valid_scores(),
        model="semantic-model",
        prompt_version="semantic-evaluator-v0.1",
        latency_ms=1200,
    )

    payload = result.model_dump()

    assert payload["status"] == "success"
    assert payload["scores"]["relevance"] == 4.5
    assert payload["model"] == "semantic-model"
    assert payload["prompt_version"] == "semantic-evaluator-v0.1"
    assert payload["latency_ms"] == 1200