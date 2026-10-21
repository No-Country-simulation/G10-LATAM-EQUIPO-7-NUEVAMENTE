"""Pruebas de contrato BackendAPI -> Data/IA Evaluation V2.

No dependen de credenciales Gemini ni de servicios externos: usan transporte
HTTP simulado y repositorios en memoria para validar dominio y orquestación.
"""

import asyncio
import json
from copy import deepcopy

import httpx
import pytest

from app.application.format_evaluation_service import (
    EvaluationResponseMismatchError,
    FormatEvaluationService,
)
from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.generated_content import QuizContent, QuizQuestion
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.infrastructure.integrations.http_data_ia_adapter import HTTPDataIAAdapter
from app.infrastructure.integrations.http_data_ia_v2_mapper import (
    parse_evaluation_v2,
)
from app.ports.data_ia_port import (
    DataIAError,
    DataIAEvaluationInput,
    DataIAV2EvaluationResult,
)


def _request() -> DataIAEvaluationInput:
    """Generación ya validada con evidencia verificable."""
    return DataIAEvaluationInput(
        document_id="doc_123",
        format_type=GeneratedFormatType.QUIZ,
        generated_content=QuizContent(
            title="Arquitectura de sistemas",
            instructions="Selecciona una respuesta.",
            questions=(
                QuizQuestion(
                    question_id="q1",
                    question="¿Quién coordina los servicios?",
                    options=("BackendAPI", "Frontend"),
                    correct_answer="BackendAPI",
                    explanation="BackendAPI coordina las integraciones.",
                ),
            ),
        ),
        chunks_used=(
            ChunkEvidence(
                chunk_id="chunk_1",
                document_id="doc_123",
                rank=1,
                score=0.98,
                text="BackendAPI coordina las integraciones.",
            ),
        ),
        generation_context=GenerationContext(
            profile="intermediate",
            niche="backend",
            detail_level="detailed",
            learning_objective="Comprender la arquitectura.",
        ),
    )


def _response() -> dict[str, object]:
    """Ejemplo de JSON V2 público con observaciones estructuradas."""
    return {
        "document_id": "doc_123",
        "format": "quiz",
        "verdict": "requires_revision",
        "heuristic_scores": {
            "relevance": 4.0,
            "coherence": 4.5,
            "didactic_adaptation": 3.0,
            "content_support": 5.0,
        },
        "semantic_evaluation": {
            "status": "success",
            "scores": {
                "relevance": 4.7,
                "coherence": 4.1,
                "didactic_adaptation": 2.7,
                "content_support": 4.5,
            },
            "observations": [
                {
                    "dimension": "didactic_adaptation",
                    "severity": "high",
                    "message": "El nivel técnico es superior al público.",
                    "item_id": "q1",
                }
            ],
            "recommendations": [
                {
                    "dimension": "didactic_adaptation",
                    "message": "Explicar primero los conceptos básicos.",
                    "item_id": "q1",
                }
            ],
            "unsupported_information": [
                {
                    "claim": "Afirmación no sustentada.",
                    "reason": "No figura en el material de origen.",
                    "item_id": "q1",
                    "related_chunk_ids": ["chunk_1"],
                }
            ],
            "error_code": None,
            "model": "gemini-test",
            "prompt_version": "semantic-v1",
            "latency_ms": 27,
        },
        "evaluator_version": "2.0.0",
        "rubric_version": "2.0.0",
    }


def _run_adapter(payload: object) -> DataIAV2EvaluationResult:
    """Ejecuta el adaptador con la ruta V2 y respuesta simulada."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/evaluate/v2"
        body = json.loads(request.content)
        assert body["document_id"] == "doc_123"
        assert body["format"] == "quiz"
        assert len(body["chunks_used"]) == 1
        assert body["generation_context"]["profile"] == "intermediate"
        return httpx.Response(200, json=payload)

    async def run() -> DataIAV2EvaluationResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate/v2",
            )
            result = await adapter.evaluate(_request())
            assert isinstance(result, DataIAV2EvaluationResult)
            return result

    return asyncio.run(run())


def test_v2_adapter_preserves_independent_scores_and_feedback() -> None:
    result = _run_adapter(_response())
    assert result.verdict == "requires_revision"
    assert result.heuristic_scores is not None
    assert result.heuristic_scores.didactic_adaptation == 3.0
    semantic = result.semantic_evaluation
    assert semantic.status == "success"
    assert semantic.scores is not None
    assert semantic.scores.didactic_adaptation == 2.7
    assert semantic.observations[0].item_id == "q1"
    assert semantic.recommendations[0].dimension == "didactic_adaptation"
    assert semantic.unsupported_information[0].related_chunk_ids == ("chunk_1",)
    assert semantic.model == "gemini-test"
    assert semantic.latency_ms == 27


def test_v2_adapter_preserves_semantic_unavailable_without_fake_scores() -> None:
    payload = _response()
    payload["verdict"] = "approved"
    payload["semantic_evaluation"] = {
        "status": "unavailable",
        "scores": None,
        "error_code": "not_configured",
    }
    result = _run_adapter(payload)
    assert result.verdict == "approved"
    assert result.heuristic_scores is not None
    assert result.semantic_evaluation.status == "unavailable"
    assert result.semantic_evaluation.scores is None


def test_v2_adapter_allows_no_verdict_and_no_scores() -> None:
    payload = _response()
    payload["verdict"] = None
    payload["heuristic_scores"] = None
    payload["semantic_evaluation"] = {
        "status": "failed",
        "scores": None,
        "error_code": "timeout",
        "error_message": "Gemini no respondió a tiempo.",
    }
    result = _run_adapter(payload)
    assert result.verdict is None
    assert result.heuristic_scores is None
    assert result.semantic_evaluation.status == "failed"


@pytest.mark.parametrize(
    "tamper",
    [
        "old_contract",
        "invalid_heuristic_score",
        "invalid_semantic_score",
        "contradictory_semantic_status",
        "unsupported_verdict",
        "verdict_without_evidence",
    ],
)
def test_v2_adapter_rejects_inconsistent_response(tamper: str) -> None:
    payload = deepcopy(_response())
    if tamper == "old_contract":
        payload = {"document_id": "doc_123", "format": "quiz", "status": "aprobado"}
    elif tamper == "invalid_heuristic_score":
        payload["heuristic_scores"]["relevance"] = 6.0
    elif tamper == "invalid_semantic_score":
        payload["semantic_evaluation"]["scores"]["coherence"] = 0.0
    elif tamper == "contradictory_semantic_status":
        payload["semantic_evaluation"]["status"] = "unavailable"
    elif tamper == "unsupported_verdict":
        payload["verdict"] = "unknown"
    elif tamper == "verdict_without_evidence":
        payload["heuristic_scores"] = None
        payload["semantic_evaluation"] = {
            "status": "unavailable",
            "error_code": "not_configured",
        }
    with pytest.raises(DataIAError, match="respuesta de evaluación inválida"):
        _run_adapter(payload)


def test_v2_mapper_does_not_combine_scores() -> None:
    result = parse_evaluation_v2(_response())
    assert result.heuristic_scores is not None
    assert result.semantic_evaluation.scores is not None
    assert not hasattr(result, "final_score")
    assert not hasattr(result, "combined_score")


class _GeneratedRepository:
    def __init__(self, generated_format: GeneratedFormat):
        self.generated_format = generated_format

    def find_by_id(self, format_id: str) -> GeneratedFormat | None:
        return (
            self.generated_format
            if self.generated_format.format_id == format_id
            else None
        )


class _EvaluationRepository:
    def __init__(self):
        self.created = []

    def create(self, evaluation):
        self.created.append(evaluation)
        return evaluation


class _DataIAStub:
    def __init__(self, result: DataIAV2EvaluationResult):
        self.result = result

    async def evaluate(self, request: DataIAEvaluationInput):
        return self.result


def _generated_format() -> GeneratedFormat:
    request = _request()
    return GeneratedFormat(
        format_id="fmt_initial_123",
        document_id=request.document_id,
        format_type=request.format_type,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=request.generation_context,
        content=request.generated_content,
        chunks_used=request.chunks_used,
    )


def test_service_persists_v2_and_preserves_original_generated_content() -> None:
    generated = _generated_format()
    repository = _EvaluationRepository()
    result = parse_evaluation_v2(_response())
    service = FormatEvaluationService(
        generated_format_repository=_GeneratedRepository(generated),
        evaluation_repository=repository,
        data_ia=_DataIAStub(result),
    )
    evaluation = asyncio.run(service.evaluate_format(generated.format_id))
    assert evaluation.is_v2
    assert evaluation.format_id == generated.format_id
    assert evaluation.verdict == "requires_revision"
    assert evaluation.heuristic_scores == result.heuristic_scores
    assert evaluation.semantic_evaluation == result.semantic_evaluation
    assert evaluation.status is None
    assert evaluation.scores is None
    assert repository.created == [evaluation]
    assert generated.content is not None
    assert generated.status == GeneratedFormatStatus.SUCCESS


def test_service_persists_v2_with_no_verdict() -> None:
    generated = _generated_format()
    repository = _EvaluationRepository()
    payload = _response()
    payload["verdict"] = None
    payload["heuristic_scores"] = None
    payload["semantic_evaluation"] = {
        "status": "unavailable",
        "error_code": "not_configured",
    }
    service = FormatEvaluationService(
        generated_format_repository=_GeneratedRepository(generated),
        evaluation_repository=repository,
        data_ia=_DataIAStub(parse_evaluation_v2(payload)),
    )
    evaluation = asyncio.run(service.evaluate_format(generated.format_id))
    assert evaluation.verdict is None
    assert evaluation.is_v2
    assert evaluation.semantic_evaluation is not None
    assert evaluation.semantic_evaluation.status == "unavailable"
    assert len(repository.created) == 1


def test_service_rejects_mismatched_document_before_persistence() -> None:
    generated = _generated_format()
    repository = _EvaluationRepository()
    payload = _response()
    payload["document_id"] = "other_doc"
    service = FormatEvaluationService(
        generated_format_repository=_GeneratedRepository(generated),
        evaluation_repository=repository,
        data_ia=_DataIAStub(parse_evaluation_v2(payload)),
    )
    with pytest.raises(EvaluationResponseMismatchError):
        asyncio.run(service.evaluate_format(generated.format_id))
    assert repository.created == []
