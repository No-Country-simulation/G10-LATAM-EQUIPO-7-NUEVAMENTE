"""Tests para SemanticEvaluator.

Estos tests validan:
- construcción del flujo de éxito;
- mapping de errores normalizados;
- manejo de salida inválida;
- propagación de metadata;
- uso de chunks_used como evidencia;
- construcción básica del prompt.
"""

from typing import Any

from data_ai.evaluation.semantic_evaluator import (
    SEMANTIC_PROMPT_VERSION,
    SYSTEM_PROMPT,
    SemanticEvaluator,
    build_semantic_user_prompt,
)
from data_ai.evaluation.semantic_provider import (
    SemanticProvider,
    SemanticProviderExecutionError,
    SemanticProviderNotConfiguredError,
    SemanticProviderTimeoutError,
    SemanticProviderInvalidOutputError, # <--- AGREGAMOS ESTE IMPORT
)


class FakeSemanticProvider(SemanticProvider):
    """Provider fake configurable para pruebas del evaluador."""

    def __init__(
        self,
        *,
        response: dict[str, Any] | None = None,
        error: Exception | None = None,
        provider_name: str = "fake",
        model_name: str | None = "fake-model",
    ) -> None:
        self._response = response
        self._error = error
        self._provider_name = provider_name
        self._model_name = model_name

        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str | None:
        return self._model_name

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt

        if self._error is not None:
            raise self._error

        if self._response is None:
            return {}

        return self._response


def _valid_provider_response() -> dict[str, Any]:
    """Crea una salida semántica válida de proveedor."""
    return {
        "scores": {
            "relevance": 4.5,
            "coherence": 4.2,
            "didactic_adaptation": 3.7,
            "content_support": 4.1,
        },
        "observations": [
            {
                "dimension": "didactic_adaptation",
                "severity": "medium",
                "message": (
                    "El contenido utiliza algunos términos "
                    "avanzados sin explicación previa."
                ),
                "item_id": None,
            }
        ],
        "recommendations": [
            {
                "dimension": "didactic_adaptation",
                "message": (
                    "Definir los conceptos avanzados antes "
                    "de utilizarlos."
                ),
                "item_id": None,
            }
        ],
        "unsupported_information": [],
    }


def _generated_content() -> dict[str, Any]:
    return {
        "title": "Introducción a REST",
        "summary": (
            "REST es un estilo arquitectónico para "
            "sistemas distribuidos."
        ),
        "key_points": [
            "Utiliza recursos.",
            "Emplea métodos HTTP.",
        ],
        "conclusion": (
            "REST facilita la construcción de APIs."
        ),
    }


def _generation_context() -> dict[str, Any]:
    return {
        "profile": "junior",
        "niche": "backend",
        "detail_level": "medium",
        "learning_objective": (
            "Comprender los fundamentos de APIs REST"
        ),
    }


def _chunks_used() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "chunk_id": "chunk_001",
            "document_id": "doc_123",
            "score": 4.2,
            "text": (
                "REST es un estilo arquitectónico que "
                "utiliza recursos y métodos HTTP."
            ),
        }
    ]


# ============================================================
# Prompt construction
# ============================================================


def test_system_prompt_contains_required_dimensions():
    assert "relevance" in SYSTEM_PROMPT
    assert "coherence" in SYSTEM_PROMPT
    assert "didactic_adaptation" in SYSTEM_PROMPT
    assert "content_support" in SYSTEM_PROMPT


def test_system_prompt_enforces_chunks_as_factual_evidence():
    assert "ÚNICA evidencia factual válida" in SYSTEM_PROMPT
    assert "chunks_used" in SYSTEM_PROMPT


def test_build_semantic_user_prompt_contains_format():
    prompt = build_semantic_user_prompt(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert "tldr" in prompt


def test_build_semantic_user_prompt_contains_generated_content():
    prompt = build_semantic_user_prompt(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert "Introducción a REST" in prompt
    assert "REST facilita la construcción de APIs." in prompt


def test_build_semantic_user_prompt_contains_generation_context():
    prompt = build_semantic_user_prompt(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert "junior" in prompt
    assert "backend" in prompt
    assert "Comprender los fundamentos de APIs REST" in prompt


def test_build_semantic_user_prompt_contains_chunks():
    prompt = build_semantic_user_prompt(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert "chunk_001" in prompt
    assert "REST es un estilo arquitectónico" in prompt


def test_build_semantic_user_prompt_marks_generation_context_as_non_factual():
    prompt = build_semantic_user_prompt(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert "generation_context NO es evidencia factual" in prompt


# ============================================================
# Success path
# ============================================================


def test_semantic_evaluator_returns_success():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "success"
    assert result.scores is not None
    assert result.error_code is None
    assert result.error_message is None


def test_semantic_evaluator_maps_scores():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.scores is not None
    assert result.scores.relevance == 4.5
    assert result.scores.coherence == 4.2
    assert result.scores.didactic_adaptation == 3.7
    assert result.scores.content_support == 4.1


def test_semantic_evaluator_maps_observations():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.dimension == "didactic_adaptation"
    assert observation.severity == "medium"


def test_semantic_evaluator_maps_recommendations():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert len(result.recommendations) == 1

    recommendation = result.recommendations[0]

    assert (
        recommendation.dimension
        == "didactic_adaptation"
    )


def test_semantic_evaluator_maps_unsupported_information():
    response = _valid_provider_response()

    response["unsupported_information"] = [
        {
            "claim": (
                "REST requiere mantener estado entre requests."
            ),
            "reason": (
                "Los chunks no respaldan esta afirmación."
            ),
            "item_id": None,
            "related_chunk_ids": [
                "chunk_001",
            ],
        }
    ]

    provider = FakeSemanticProvider(
        response=response,
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert len(result.unsupported_information) == 1

    unsupported = result.unsupported_information[0]

    assert (
        unsupported.claim
        == "REST requiere mantener estado entre requests."
    )

    assert unsupported.related_chunk_ids == [
        "chunk_001",
    ]


def test_semantic_evaluator_preserves_model_name():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
        model_name="fake-semantic-v1",
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.model == "fake-semantic-v1"


def test_semantic_evaluator_preserves_prompt_version():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.prompt_version == SEMANTIC_PROMPT_VERSION


def test_semantic_evaluator_accepts_custom_prompt_version():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(
        provider,
        prompt_version="semantic-evaluator-test",
    )

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert (
        result.prompt_version
        == "semantic-evaluator-test"
    )


def test_semantic_evaluator_reports_non_negative_latency():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.latency_ms is not None
    assert result.latency_ms >= 0


def test_semantic_evaluator_passes_prompts_to_provider():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert provider.last_system_prompt == SYSTEM_PROMPT
    assert provider.last_user_prompt is not None

    assert (
        "CONTENIDO GENERADO A EVALUAR"
        in provider.last_user_prompt
    )

    assert (
        "EVIDENCIA FACTUAL"
        in provider.last_user_prompt
    )


# ============================================================
# Not configured
# ============================================================


def test_semantic_evaluator_maps_not_configured():
    provider = FakeSemanticProvider(
        error=SemanticProviderNotConfiguredError(
            "Semantic provider is not configured.",
            provider="gemini",
            model=None,
        ),
        model_name=None,
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "unavailable"
    assert result.scores is None
    assert result.error_code == "not_configured"

    assert (
        "not configured"
        in result.error_message.lower()
    )


# ============================================================
# Timeout
# ============================================================


def test_semantic_evaluator_maps_timeout():
    provider = FakeSemanticProvider(
        error=SemanticProviderTimeoutError(
            "Provider timed out.",
            provider="gemini",
            model="gemini-test-model",
        ),
        model_name="gemini-test-model",
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.scores is None
    assert result.error_code == "timeout"

    assert result.model == "gemini-test-model"


# ============================================================
# Provider execution error
# ============================================================


def test_semantic_evaluator_maps_provider_execution_error():
    provider = FakeSemanticProvider(
        error=SemanticProviderExecutionError(
            "Provider failed.",
            provider="gemini",
            model="gemini-test-model",
        ),
        model_name="gemini-test-model",
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.scores is None
    assert result.error_code == "provider_error"


# ============================================================
# Invalid output
# ============================================================

def test_semantic_evaluator_maps_provider_invalid_output_error():
    provider = FakeSemanticProvider(
        error=SemanticProviderInvalidOutputError(
            "Gemini returned invalid structured output.",
            provider="gemini",
            model="gemini-test",
        ),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.scores is None
    assert result.error_code == "invalid_output"

def test_semantic_evaluator_maps_missing_scores_to_invalid_output():
    provider = FakeSemanticProvider(
        response={
            "observations": [],
            "recommendations": [],
            "unsupported_information": [],
        },
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.scores is None
    assert result.error_code == "invalid_output"


def test_semantic_evaluator_maps_invalid_score_to_invalid_output():
    response = _valid_provider_response()

    response["scores"]["relevance"] = 8.0

    provider = FakeSemanticProvider(
        response=response,
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.scores is None
    assert result.error_code == "invalid_output"


def test_semantic_evaluator_maps_invalid_dimension_to_invalid_output():
    response = _valid_provider_response()

    response["observations"] = [
        {
            "dimension": "accuracy",
            "severity": "high",
            "message": "Dimensión inválida.",
        }
    ]

    provider = FakeSemanticProvider(
        response=response,
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.error_code == "invalid_output"


def test_semantic_evaluator_maps_non_dict_output_to_invalid_output():
    provider = FakeSemanticProvider(
        response=["invalid"],  # type: ignore[arg-type]
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.error_code == "invalid_output"


# ============================================================
# Unexpected errors
# ============================================================


def test_semantic_evaluator_maps_unexpected_error_to_provider_error():
    provider = FakeSemanticProvider(
        error=RuntimeError(
            "Unexpected low-level failure."
        ),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "failed"
    assert result.scores is None
    assert result.error_code == "provider_error"

    assert (
        "Unexpected semantic provider failure"
        in result.error_message
    )


# ============================================================
# Empty optional collections
# ============================================================


def test_semantic_evaluator_accepts_scores_only_payload():
    provider = FakeSemanticProvider(
        response={
            "scores": {
                "relevance": 5.0,
                "coherence": 5.0,
                "didactic_adaptation": 5.0,
                "content_support": 5.0,
            }
        },
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=_chunks_used(),
    )

    assert result.status == "success"
    assert result.observations == []
    assert result.recommendations == []
    assert result.unsupported_information == []


# ============================================================
# JSON-compatible input
# ============================================================


def test_semantic_evaluator_accepts_empty_chunks_list():
    provider = FakeSemanticProvider(
        response=_valid_provider_response(),
    )

    evaluator = SemanticEvaluator(provider)

    result = evaluator.evaluate(
        content_format="tldr",
        generated_content=_generated_content(),
        generation_context=_generation_context(),
        chunks_used=[],
    )

    assert result.status == "success"

    assert provider.last_user_prompt is not None
    assert "[]" in provider.last_user_prompt