"""Tests de integración interna para Evaluation V2 service."""

from typing import Any

import pytest

from data_ai.evaluation.evaluation_v2_service import (
    evaluate_content_v2,
)
from data_ai.evaluation.semantic_evaluator import (
    SemanticEvaluator,
)
from data_ai.evaluation.semantic_provider import (
    SemanticProvider,
    SemanticProviderExecutionError,
    SemanticProviderNotConfiguredError,
)
from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    GenerationContext,
    TLDRContent,
)


class FakeSemanticProvider(
    SemanticProvider
):
    """Provider controlado para tests sin red."""

    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._error = error
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str | None:
        return "fake-semantic-model"

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        self.calls += 1

        if self._error is not None:
            raise self._error

        if self._payload is None:
            raise RuntimeError(
                "Fake provider payload not configured."
            )

        return self._payload


def _content() -> TLDRContent:
    return TLDRContent(
        title="Arquitectura backend",
        summary=(
            "Una arquitectura backend organiza "
            "servicios y lógica de negocio."
        ),
        key_points=[
            "Organiza servicios.",
            "Separa responsabilidades.",
        ],
        conclusion=(
            "La separación ayuda al mantenimiento."
        ),
    )


def _context() -> GenerationContext:
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="medium",
        learning_objective=(
            "Comprender arquitectura backend."
        ),
    )


def _chunks() -> list[ChunkUsed]:
    return [
        ChunkUsed(
            chunk_id="chunk_1",
            document_id="doc_123",
            rank=1,
            score=1.0,
            text=(
                "Una arquitectura backend organiza "
                "servicios, lógica de negocio y "
                "responsabilidades."
            ),
        ),
    ]


def _success_payload() -> dict[str, Any]:
    return {
        "scores": {
            "relevance": 4.5,
            "coherence": 4.5,
            "didactic_adaptation": 4.0,
            "content_support": 4.5,
        },
        "observations": [
            {
                "dimension": (
                    "didactic_adaptation"
                ),
                "severity": "low",
                "message": (
                    "El contenido puede explicar "
                    "un concepto con mayor detalle."
                ),
                "item_id": None,
            }
        ],
        "recommendations": [
            {
                "dimension": (
                    "didactic_adaptation"
                ),
                "message": (
                    "Agregar una definición breve."
                ),
                "item_id": None,
            }
        ],
        "unsupported_information": [],
    }


def test_service_combines_heuristic_and_semantic_evaluation():
    provider = FakeSemanticProvider(
        payload=_success_payload()
    )

    semantic_evaluator = (
        SemanticEvaluator(provider)
    )

    result = evaluate_content_v2(
        document_id="doc_123",
        content_format="tldr",
        generated_content=_content(),
        chunks_used=_chunks(),
        generation_context=_context(),
        semantic_evaluator=semantic_evaluator,
    )

    assert result.document_id == "doc_123"
    assert result.format == "tldr"

    assert result.heuristic_scores is not None

    assert (
        result.semantic_evaluation.status
        == "success"
    )

    assert (
        result.semantic_evaluation.scores
        is not None
    )

    assert provider.calls == 1


def test_service_keeps_scores_separate():
    provider = FakeSemanticProvider(
        payload=_success_payload()
    )

    result = evaluate_content_v2(
        document_id="doc_123",
        content_format="tldr",
        generated_content=_content(),
        chunks_used=_chunks(),
        generation_context=_context(),
        semantic_evaluator=(
            SemanticEvaluator(provider)
        ),
    )

    assert result.heuristic_scores is not None

    semantic_scores = (
        result.semantic_evaluation.scores
    )

    assert semantic_scores is not None

    dumped = result.model_dump()

    assert "heuristic_scores" in dumped

    assert (
        "scores"
        in dumped["semantic_evaluation"]
    )

    assert "final_score" not in dumped
    assert "combined_score" not in dumped
    assert "weighted_score" not in dumped


def test_semantic_provider_failure_does_not_break_heuristic_result():
    provider = FakeSemanticProvider(
        error=SemanticProviderExecutionError(
            "Provider failure.",
            provider="fake",
            model="fake-semantic-model",
        )
    )

    result = evaluate_content_v2(
        document_id="doc_123",
        content_format="tldr",
        generated_content=_content(),
        chunks_used=_chunks(),
        generation_context=_context(),
        semantic_evaluator=(
            SemanticEvaluator(provider)
        ),
    )

    assert result.heuristic_scores is not None

    assert result.verdict is not None

    assert (
        result.semantic_evaluation.status
        == "failed"
    )

    assert (
        result.semantic_evaluation.error_code
        == "provider_error"
    )


def test_unconfigured_semantic_provider_uses_controlled_fallback():
    provider = FakeSemanticProvider(
        error=(
            SemanticProviderNotConfiguredError(
                "Provider not configured.",
                provider="fake",
                model=None,
            )
        )
    )

    result = evaluate_content_v2(
        document_id="doc_123",
        content_format="tldr",
        generated_content=_content(),
        chunks_used=_chunks(),
        generation_context=_context(),
        semantic_evaluator=(
            SemanticEvaluator(provider)
        ),
    )

    assert result.heuristic_scores is not None

    assert result.verdict is not None

    assert (
        result.semantic_evaluation.status
        == "unavailable"
    )

    assert (
        result.semantic_evaluation.error_code
        == "not_configured"
    )


def test_service_uses_semantic_chunks_as_factual_evidence():
    provider = FakeSemanticProvider(
        payload=_success_payload()
    )

    evaluator = SemanticEvaluator(
        provider
    )

    result = evaluate_content_v2(
        document_id="doc_123",
        content_format="tldr",
        generated_content=_content(),
        chunks_used=_chunks(),
        generation_context=_context(),
        semantic_evaluator=evaluator,
    )

    assert (
        result.semantic_evaluation.status
        == "success"
    )


@pytest.mark.parametrize(
    "content_format",
    [
        "tldr",
    ],
)
def test_service_returns_requested_format(
    content_format,
):
    provider = FakeSemanticProvider(
        payload=_success_payload()
    )

    result = evaluate_content_v2(
        document_id="doc_123",
        content_format=content_format,
        generated_content=_content(),
        chunks_used=_chunks(),
        generation_context=_context(),
        semantic_evaluator=(
            SemanticEvaluator(provider)
        ),
    )

    assert result.format == content_format