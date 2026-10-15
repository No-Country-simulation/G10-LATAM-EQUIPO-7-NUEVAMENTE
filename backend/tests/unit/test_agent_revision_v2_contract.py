"""Pruebas del contrato BackendAPI → Agentes de corrección atómica V2.

Se utiliza httpx.MockTransport; los resultados no sustituyen pruebas reales
contra /api/v1/revise cuando Agentes publique su implementación.
"""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from app.application.format_evaluation_feedback_mapper import build_revision_feedback
from app.application.format_revision_service import (
    FormatRevisionIntegrationError,
    FormatRevisionService,
)
from app.application.revision_contract_v2 import (
    RevisionEvaluationContractError,
    build_evaluator_response_v2,
)
from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.format_evaluation import (
    FormatEvaluation,
    HeuristicScoresV2,
    SemanticEvaluationResult,
    SemanticRecommendation,
)
from app.domain.generated_content import TLDRContent
from app.domain.generated_format import ChunkEvidence, GeneratedFormat, GenerationContext
from app.infrastructure.integrations.http_agent_revision_adapter import (
    HTTPAgentRevisionAdapter,
)
from app.ports.agent_revision_port import AgentRevisionInput


class ReadOnlyFormatRepository:
    """Expone exclusivamente el formato original; no persiste correcciones."""

    def __init__(self, original: GeneratedFormat) -> None:
        self._original = original

    def find_by_id(self, format_id: str) -> GeneratedFormat | None:
        return self._original if format_id == self._original.format_id else None


def build_original() -> GeneratedFormat:
    """Generación TLDR válida con el contexto y las evidencias necesarias."""
    return GeneratedFormat(
        format_id="fmt_original",
        document_id="doc_123",
        format_type=GeneratedFormatType.TLDR,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=GenerationContext(
            profile="profesional",
            niche="finanzas",
            detail_level="avanzado",
            learning_objective="Comprender indicadores",
        ),
        content=TLDRContent(
            title="Síntesis inicial",
            summary="Contenido anterior",
            key_points=("Contabilidad",),
            conclusion="Conclusión inicial",
        ),
        chunks_used=(
            ChunkEvidence(
                chunk_id="chunk1",
                document_id="doc_123",
                rank=1,
                score=0.95,
                text="Evidencia factual del documento.",
            ),
        ),
    )


def build_evaluation() -> FormatEvaluation:
    """Evaluación V2 completa, negativa y accionable."""
    return FormatEvaluation(
        evaluation_id="eval_123",
        format_id="fmt_original",
        verdict="requires_revision",
        heuristic_scores=HeuristicScoresV2(
            relevance=4.0,
            coherence=3.0,
            didactic_adaptation=2.0,
            content_support=4.0,
        ),
        semantic_evaluation=SemanticEvaluationResult(
            status="unavailable",
            error_code="not_configured",
            recommendations=(
                SemanticRecommendation(
                    dimension="didactic_adaptation",
                    message="Simplificar tecnicismos",
                    item_id="item_1",
                ),
            ),
        ),
        evaluator_version="2.0.0",
        rubric_version="2.0.0",
    )


def test_canonical_evaluator_response_preserves_v2_fields() -> None:
    original = build_original()
    payload = build_evaluator_response_v2(
        document_id=original.document_id,
        format_type=original.format_type,
        evaluation=build_evaluation(),
    )
    assert set(payload) == {
        "document_id",
        "format",
        "verdict",
        "heuristic_scores",
        "semantic_evaluation",
        "evaluator_version",
        "rubric_version",
    }
    assert payload["document_id"] == "doc_123"
    assert payload["format"] == "tldr"
    assert payload["verdict"] == "requires_revision"
    assert payload["semantic_evaluation"]["error_code"] == "not_configured"
    json.dumps(payload)  # Debe ser JSON serializable, sin tipos internos.


@pytest.mark.parametrize("changes", [
    {"verdict": "approved"},
    {"verdict": None},
    {"evaluator_version": None},
    {"rubric_version": None},
])
def test_incomplete_or_nonnegative_evaluations_are_rejected(changes: dict) -> None:
    original = build_original()
    with pytest.raises(RevisionEvaluationContractError):
        build_evaluator_response_v2(
            document_id=original.document_id,
            format_type=original.format_type,
            evaluation=replace(build_evaluation(), **changes),
        )


def test_v2_request_rejects_partial_metadata() -> None:
    original = build_original()
    feedback = build_revision_feedback(build_evaluation())
    assert feedback is not None
    with pytest.raises(ValueError, match="requiere IDs"):
        AgentRevisionInput(
            document_id=original.document_id,
            format_type=original.format_type,
            current_content=original.content,
            generation_context=original.generation_context,
            chunks_used=original.chunks_used,
            feedback=feedback,
            revision_id="fmt_rev_1",
        )


def test_http_contract_v2_sends_full_evaluation_and_validates_response_ids() -> None:
    """El adaptador debe emitir el contrato nuevo sin campos legacy."""
    original = build_original()
    evaluation = build_evaluation()
    feedback = build_revision_feedback(evaluation)
    assert feedback is not None
    contract = build_evaluator_response_v2(
        document_id=original.document_id,
        format_type=original.format_type,
        evaluation=evaluation,
    )
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/revise"
        body = json.loads(request.content)
        captured.append(body)
        assert body["revision_id"] == "fmt_rev_1"
        assert body["original_format_id"] == "fmt_original"
        assert body["previous_content"] == original.content.to_dict()
        assert body["chunks_used"] == [c.to_dict() for c in original.chunks_used]
        assert body["generation_context"]["profile"] == "profesional"
        assert body["evaluator_response"] == json.loads(json.dumps(contract))
        assert "current_content" not in body
        assert "feedback" not in body
        return httpx.Response(200, json={
            "revision_id": body["revision_id"],
            "original_format_id": body["original_format_id"],
            "document_id": body["document_id"],
            "format": body["format"],
            "status": "success",
            "content": original.content.to_dict(),
            "sources_used": [c.to_dict() for c in original.chunks_used],
            "execution_time_seconds": 0.8,
            "error": None,
            "error_message": None,
        })

    async def exercise() -> None:
        async with httpx.AsyncClient(
            base_url="http://agents.test",
            transport=httpx.MockTransport(handler),
        ) as client:
            service = FormatRevisionService(
                generated_format_repository=ReadOnlyFormatRepository(original),
                agent_revision=HTTPAgentRevisionAdapter(client=client),
            )
            result = await service.request_revision(
                format_id=original.format_id,
                feedback=feedback,
                revision_id="fmt_rev_1",
                evaluator_response=contract,
            )
            assert result.status == GeneratedFormatStatus.SUCCESS
            assert result.document_id == original.document_id

    asyncio.run(exercise())
    assert len(captured) == 1  # Sin reintentos HTTP adicionales.


@pytest.mark.parametrize(("field", "wrong_id"), [
    ("revision_id", "different"),
    ("revision_id", None),
    ("original_format_id", "different"),
    ("original_format_id", None),
])
def test_http_rejects_missing_or_mismatched_revision_identity(
    field: str, wrong_id: str | None
) -> None:
    original = build_original()
    evaluation = build_evaluation()
    feedback = build_revision_feedback(evaluation)
    assert feedback is not None
    contract = build_evaluator_response_v2(
        document_id=original.document_id,
        format_type=original.format_type,
        evaluation=evaluation,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        response_body = {
            "revision_id": body["revision_id"],
            "original_format_id": body["original_format_id"],
            "document_id": body["document_id"],
            "format": body["format"],
            "status": "success",
            "content": original.content.to_dict(),
            "sources_used": [c.to_dict() for c in original.chunks_used],
            "execution_time_seconds": 0.3,
        }
        response_body[field] = wrong_id
        return httpx.Response(200, json=response_body)

    async def exercise() -> None:
        async with httpx.AsyncClient(
            base_url="http://agents.test",
            transport=httpx.MockTransport(handler),
        ) as client:
            service = FormatRevisionService(
                generated_format_repository=ReadOnlyFormatRepository(original),
                agent_revision=HTTPAgentRevisionAdapter(client=client),
            )
            with pytest.raises(FormatRevisionIntegrationError):
                await service.request_revision(
                    format_id=original.format_id,
                    feedback=feedback,
                    revision_id="fmt_rev_1",
                    evaluator_response=contract,
                )

    asyncio.run(exercise())
