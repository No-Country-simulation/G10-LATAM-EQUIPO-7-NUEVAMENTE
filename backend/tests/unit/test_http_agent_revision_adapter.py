"""Contratos BackendAPI -> Agentes para una revisión pedagógica atómica.

Son pruebas de contrato con transporte HTTP simulado; no sustituyen E2E
contra los tres servicios reales (se ejecutarán al publicarse /revise).
"""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.generated_content import (
    FlashcardsContent,
    QuizContent,
    TLDRContent,
    VideoScriptContent,
)
from app.domain.generated_format import ChunkEvidence, GenerationContext
from app.domain.revision_feedback import (
    FeedbackScores,
    RevisionFeedback,
    RevisionObservation,
    RevisionRecommendation,
    SemanticReview,
    UnsupportedClaim,
)
from app.infrastructure.integrations.http_agent_revision_adapter import (
    HTTPAgentRevisionAdapter,
)
from app.ports.agent_revision_port import AgentRevisionError, AgentRevisionInput

CONTENT = {
    "title": "APIs REST",
    "summary": "Los recursos se consultan mediante HTTP.",
    "key_points": ["GET consulta un recurso."],
    "conclusion": "REST organiza recursos y operaciones.",
}
EVIDENCE = {
    "chunk_id": "chunk_1",
    "document_id": "doc_123",
    "rank": 1,
    "score": 3.7421,
    "text": "REST usa recursos y métodos HTTP.",
}
SCORES = FeedbackScores(
    relevance=4.5, coherence=4.0, didactic_adaptation=2.5, content_support=5.0
)


def _request() -> AgentRevisionInput:
    """Construye una revisión con evaluación V2 anidada válida."""
    return AgentRevisionInput(
        document_id="doc_123",
        format_type=GeneratedFormatType.TLDR,
        current_content=TLDRContent.from_dict(CONTENT),
        generation_context=GenerationContext(
            profile="beginner", niche="backend", detail_level="medium"
        ),
        chunks_used=(ChunkEvidence(**EVIDENCE),),
        feedback=RevisionFeedback(
            verdict="requires_revision",
            heuristic_scores=SCORES,
            semantic_evaluation=SemanticReview(
                status="success",
                scores=SCORES,
                observations=(
                    RevisionObservation(
                        dimension="didactic_adaptation",
                        severity="medium",
                        message="Falta definir qué es un recurso.",
                    ),
                ),
                recommendations=(
                    RevisionRecommendation(
                        dimension="didactic_adaptation",
                        message="Definir el término recurso.",
                    ),
                ),
                unsupported_information=(
                    UnsupportedClaim(
                        claim="Todos los métodos son seguros.",
                        reason="No está sustentado.",
                        related_chunk_ids=("chunk_1",),
                    ),
                ),
                model="gemini-test",
                prompt_version="v2",
                latency_ms=12,
            ),
        ),
    )


def _success() -> dict[str, object]:
    return {
        "document_id": "doc_123",
        "format": "tldr",
        "status": "success",
        "content": CONTENT,
        "sources_used": [EVIDENCE],
        "error": None,
        "error_message": None,
        "execution_time_seconds": 1.25,
    }


def _failure(http_status: int = 429) -> dict[str, object]:
    return {
        "document_id": "doc_123",
        "format": "tldr",
        "status": "failed",
        "content": None,
        "sources_used": [],
        "error_message": "Límite de cuota agotado.",
        "error": {
            "code": "RESOURCE_EXHAUSTED",
            "message": "Límite de cuota agotado.",
            "retryable": True,
            "http_status": http_status,
            "upstream_status": 429,
            "provider": "gemini",
        },
        "execution_time_seconds": 0.5,
    }


def _execute(response: httpx.Response | None = None, *, handler=None):
    """Ejecuta una invocación del adaptador contra un transporte controlado."""
    def respond(request: httpx.Request) -> httpx.Response:
        return handler(request) if handler else response

    async def run():
        async with httpx.AsyncClient(
            base_url="http://agentes.test", transport=httpx.MockTransport(respond)
        ) as client:
            adapter = HTTPAgentRevisionAdapter(client=client)
            return await adapter.revise_format(_request())

    return asyncio.run(run())


def test_revision_sends_full_v2_feedback_and_evidence() -> None:
    """No pierde scores, errores semánticos, afirmaciones ni chunks en el request."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/revise"
        body = json.loads(request.content)
        assert body["document_id"] == "doc_123"
        assert body["format"] == "tldr"
        assert body["current_content"] == CONTENT
        assert body["chunks_used"] == [EVIDENCE]
        assert body["generation_context"] == {
            "profile": "beginner", "niche": "backend", "detail_level": "medium"
        }
        assert body["feedback"]["verdict"] == "requires_revision"
        assert body["feedback"]["heuristic_scores"]["didactic_adaptation"] == 2.5
        semantic = body["feedback"]["semantic_evaluation"]
        assert semantic["observations"][0]["severity"] == "medium"
        assert semantic["recommendations"][0]["message"] == "Definir el término recurso."
        assert semantic["unsupported_information"][0]["related_chunk_ids"] == ["chunk_1"]
        assert semantic["model"] == "gemini-test"
        return httpx.Response(200, json=_success())

    assert _execute(handler=handler).status == GeneratedFormatStatus.SUCCESS


def test_revision_returns_canonical_content_and_complete_evidence() -> None:
    result = _execute(httpx.Response(200, json=_success()))
    assert isinstance(result.content, TLDRContent)
    assert result.content.summary == CONTENT["summary"]
    assert result.chunks_used == (ChunkEvidence(**EVIDENCE),)
    assert result.execution_time_seconds == 1.25
    assert result.error is None


def test_revision_preserves_structured_429_without_retry() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, json=_failure())

    result = _execute(handler=handler)
    assert len(calls) == 1
    assert result.status == GeneratedFormatStatus.FAILED
    assert result.content is None
    assert result.chunks_used == ()
    assert result.error.code == "RESOURCE_EXHAUSTED"
    assert result.error.retryable is True
    assert result.error.upstream_status == 429


def test_revision_no_results_is_atomic() -> None:
    payload = _failure(http_status=404)
    payload["status"] = "no_results"
    payload["error"]["code"] = "NO_CONTEXT"
    result = _execute(httpx.Response(404, json=payload))
    assert result.status == GeneratedFormatStatus.NO_RESULTS
    assert result.content is None


@pytest.mark.parametrize("change", ["document_id", "format"])
def test_revision_rejects_mismatched_identity(change: str) -> None:
    payload = _success()
    payload[change] = "other" if change == "document_id" else "quiz"
    with pytest.raises(AgentRevisionError, match="respuesta de revisión inválida"):
        _execute(httpx.Response(200, json=payload))


def test_revision_rejects_invalid_canonical_content() -> None:
    payload = _success()
    payload["content"] = {"title": "sin datos"}
    with pytest.raises(AgentRevisionError):
        _execute(httpx.Response(200, json=payload))


def test_revision_rejects_missing_sources_in_success() -> None:
    payload = _success()
    payload["sources_used"] = []
    with pytest.raises(AgentRevisionError):
        _execute(httpx.Response(200, json=payload))


def test_revision_rejects_http_body_mismatch() -> None:
    with pytest.raises(AgentRevisionError):
        _execute(httpx.Response(200, json=_failure()))
    with pytest.raises(AgentRevisionError):
        _execute(httpx.Response(429, json=_success()))
    with pytest.raises(AgentRevisionError):
        _execute(httpx.Response(207, json=_success()))


def test_revision_rejects_non_contractual_422() -> None:
    with pytest.raises(AgentRevisionError, match="HTTP 422"):
        _execute(httpx.Response(422, json={"detail": "invalid input"}))


def test_revision_translates_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(AgentRevisionError, match="superó el tiempo permitido"):
        _execute(handler=handler)


def test_revision_rejects_invalid_request_without_external_call() -> None:
    request = _request()
    with pytest.raises(ValueError, match="evidencia"):
        replace(request, chunks_used=())
    with pytest.raises(ValueError, match="accionable"):
        replace(
            request.feedback,
            semantic_evaluation=replace(
                request.feedback.semantic_evaluation,
                observations=(), recommendations=(), unsupported_information=(),
            ),
        )
    with pytest.raises(ValueError, match="veredicto negativo"):
        replace(request.feedback, verdict="approved")


def test_revision_fallback_with_semantic_failure_is_explicit() -> None:
    """Evaluación semántica fallida puede viajar si hay hallazgos accionables."""
    request = _request()
    semantic = replace(
        request.feedback.semantic_evaluation,
        status="failed",
        scores=None,
        error_code="timeout",
        observations=(),
        recommendations=(
            RevisionRecommendation(
                dimension="relevance", message="Reorientar la explicación."
            ),
        ),
        unsupported_information=(),
    )
    fallback = replace(request.feedback, semantic_evaluation=semantic)
    assert fallback.heuristic_scores == SCORES
    assert fallback.semantic_evaluation.error_code == "timeout"


@pytest.mark.parametrize(
    ("format_type", "content"),
    [
        (
            GeneratedFormatType.QUIZ,
            {
                "title": "Quiz",
                "instructions": "Responde.",
                "questions": [
                    {
                        "question_id": "q1",
                        "question": "¿Qué consulta recursos?",
                        "options": ["GET", "DELETE"],
                        "correct_answer": "GET",
                        "explanation": "GET consulta recursos.",
                    }
                ],
            },
        ),
        (
            GeneratedFormatType.FLASHCARDS,
            {
                "title": "Tarjetas",
                "instructions": "Repasa.",
                "cards": [{"card_id": "c1", "front": "REST", "back": "Estilo de arquitectura."}],
            },
        ),
        (GeneratedFormatType.TLDR, CONTENT),
        (
            GeneratedFormatType.VIDEO_SCRIPT,
            {
                "title": "Video REST",
                "estimated_duration_minutes": 1,
                "scenes": [
                    {
                        "scene_id": "s1",
                        "title": "Escena inicial",
                        "visual_description": "Servidor HTTP",
                        "narration": "Esto es REST",
                        "duration_seconds": 10,
                    }
                ],
            },
        ),
    ],
)
def test_revision_accepts_all_canonical_content_formats(format_type, content) -> None:
    """Los cuatro formatos se deserializan con su validador canónico."""
    payload = _success()
    payload["format"] = format_type.value
    payload["content"] = content
    request = replace(
        _request(),
        format_type=format_type,
        current_content={
            GeneratedFormatType.QUIZ: QuizContent,
            GeneratedFormatType.FLASHCARDS: FlashcardsContent,
            GeneratedFormatType.TLDR: TLDRContent,
            GeneratedFormatType.VIDEO_SCRIPT: VideoScriptContent,
        }[format_type].from_dict(content),
    )

    def handler(_request_http):
        return httpx.Response(200, json=payload)

    async def run():
        async with httpx.AsyncClient(
            base_url="http://agentes.test", transport=httpx.MockTransport(handler)
        ) as client:
            return await HTTPAgentRevisionAdapter(client=client).revise_format(request)

    result = asyncio.run(run())
    assert result.content.to_dict() == content


def test_revision_rejects_format_content_type_mismatch() -> None:
    with pytest.raises(ValueError, match="no coincide"):
        replace(_request(), format_type=GeneratedFormatType.QUIZ)
