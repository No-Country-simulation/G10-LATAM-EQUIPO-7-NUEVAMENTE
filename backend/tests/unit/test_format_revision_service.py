"""Pruebas del caso de uso que invoca al Agente Revisor."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from app.application.format_revision_service import (
    FormatRevisionIntegrationError,
    FormatRevisionService,
    RevisionResultMismatchError,
    RevisionSourceNotFoundError,
    RevisionSourceNotReadyError,
)
from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.generated_content import TLDRContent
from app.domain.generated_format import ChunkEvidence, GeneratedFormat, GenerationContext
from app.domain.revision_feedback import (
    FeedbackScores,
    RevisionFeedback,
    RevisionRecommendation,
    SemanticReview,
)
from app.infrastructure.integrations.http_agent_revision_adapter import (
    HTTPAgentRevisionAdapter,
)
from app.ports.agent_revision_port import (
    AgentRevisionError,
    AgentRevisionInput,
    AgentRevisionResult,
)


class SpyGeneratedFormatRepository:
    """Implementa solo lectura; falla si el caso de uso intenta escribir."""

    def __init__(self, original: GeneratedFormat | None) -> None:
        self.original = original
        self.lookups: list[str] = []

    def find_by_id(self, format_id: str) -> GeneratedFormat | None:
        self.lookups.append(format_id)
        return self.original if self.original and self.original.format_id == format_id else None

    def create(self, generated_format: GeneratedFormat) -> GeneratedFormat:
        raise AssertionError("La tarjeta #69 no debe persistir versiones.")

    def update(self, generated_format: GeneratedFormat) -> GeneratedFormat:
        raise AssertionError("La tarjeta #69 no debe sobrescribir contenido.")

    def find_by_document_id(self, document_id: str) -> list[GeneratedFormat]:
        raise AssertionError("No se necesita consultar el historial completo.")


class SpyAgentRevision:
    """Puerto simulado que conserva las entradas recibidas."""

    def __init__(
        self,
        result: AgentRevisionResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.requests: list[AgentRevisionInput] = []

    async def revise_format(self, request: AgentRevisionInput) -> AgentRevisionResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _source(status: GeneratedFormatStatus = GeneratedFormatStatus.SUCCESS) -> GeneratedFormat:
    return GeneratedFormat(
        format_id="fmt_original",
        document_id="doc_123",
        format_type=GeneratedFormatType.TLDR,
        status=status,
        generation_context=GenerationContext(
            profile="beginner",
            niche="backend",
            detail_level="medium",
            learning_objective="Comprender arquitectura de software",
        ),
        content=(
            TLDRContent(
                title="Versión inicial",
                summary="Resumen inicial",
                key_points=("Arquitectura",),
                conclusion="Conclusión inicial",
            )
            if status == GeneratedFormatStatus.SUCCESS
            else None
        ),
        chunks_used=(
            (ChunkEvidence(
                chunk_id="chunk_1",
                document_id="doc_123",
                rank=1,
                score=0.9,
                text="Texto original validado.",
            ),)
            if status == GeneratedFormatStatus.SUCCESS
            else ()
        ),
    )


def _feedback() -> RevisionFeedback:
    return RevisionFeedback(
        verdict="requires_revision",
        heuristic_scores=FeedbackScores(
            relevance=4,
            coherence=3,
            didactic_adaptation=2,
            content_support=4,
        ),
        semantic_evaluation=SemanticReview(
            status="unavailable",
            error_code="not_configured",
            recommendations=(RevisionRecommendation(
                dimension="didactic_adaptation",
                message="Simplificar términos técnicos.",
            ),),
        ),
    )


def _result(
    status: GeneratedFormatStatus = GeneratedFormatStatus.SUCCESS,
) -> AgentRevisionResult:
    original = _source()
    return AgentRevisionResult(
        document_id=original.document_id,
        format_type=original.format_type,
        status=status,
        content=(
            TLDRContent(
                title="Versión revisada",
                summary="Resumen revisado",
                key_points=("Arquitectura clara",),
                conclusion="Nueva conclusión",
            )
            if status == GeneratedFormatStatus.SUCCESS
            else None
        ),
        chunks_used=original.chunks_used if status == GeneratedFormatStatus.SUCCESS else (),
        execution_time_seconds=1.5,
    )


def test_revision_loads_canonical_source_and_calls_port_once() -> None:
    source = _source()
    repository = SpyGeneratedFormatRepository(source)
    reviewer = SpyAgentRevision(result=_result())
    service = FormatRevisionService(
        generated_format_repository=repository,
        agent_revision=reviewer,
    )
    response = asyncio.run(service.request_revision(format_id="fmt_original", feedback=_feedback()))
    assert response.content is not None
    assert response.content.to_dict()["title"] == "Versión revisada"
    assert repository.lookups == ["fmt_original"]
    assert len(reviewer.requests) == 1
    request = reviewer.requests[0]
    assert request.document_id == "doc_123"
    assert request.format_type == GeneratedFormatType.TLDR
    assert request.current_content is source.content
    assert request.generation_context is source.generation_context
    assert request.chunks_used is source.chunks_used
    assert request.feedback == _feedback()
    assert repository.original is source  # La fuente válida no se sobrescribe.


def test_revision_rejects_unknown_source_without_http() -> None:
    reviewer = SpyAgentRevision(result=_result())
    service = FormatRevisionService(
        generated_format_repository=SpyGeneratedFormatRepository(None),
        agent_revision=reviewer,
    )
    with pytest.raises(RevisionSourceNotFoundError, match="fmt_original"):
        asyncio.run(service.request_revision(format_id="fmt_original", feedback=_feedback()))
    assert reviewer.requests == []


@pytest.mark.parametrize("status", [
    GeneratedFormatStatus.PROCESSING,
    GeneratedFormatStatus.FAILED,
    GeneratedFormatStatus.NO_RESULTS,
])
def test_revision_rejects_non_success_source(status: GeneratedFormatStatus) -> None:
    reviewer = SpyAgentRevision(result=_result())
    service = FormatRevisionService(
        generated_format_repository=SpyGeneratedFormatRepository(_source(status=status)),
        agent_revision=reviewer,
    )
    with pytest.raises(RevisionSourceNotReadyError, match="success"):
        asyncio.run(service.request_revision(format_id="fmt_original", feedback=_feedback()))
    assert reviewer.requests == []


def test_revision_rejects_empty_format_id() -> None:
    service = FormatRevisionService(
        generated_format_repository=SpyGeneratedFormatRepository(_source()),
        agent_revision=SpyAgentRevision(result=_result()),
    )
    with pytest.raises(ValueError, match="format_id"):
        asyncio.run(service.request_revision(format_id=" ", feedback=_feedback()))


@pytest.mark.parametrize("field,invalid", [
    ("document_id", "doc_wrong"),
    ("format_type", GeneratedFormatType.QUIZ),
])
def test_revision_rejects_provider_identity_mismatch(field: str, invalid: object) -> None:
    reviewer = SpyAgentRevision(
        result=replace(_result(GeneratedFormatStatus.FAILED), **{field: invalid})
    )
    service = FormatRevisionService(
        generated_format_repository=SpyGeneratedFormatRepository(_source()),
        agent_revision=reviewer,
    )
    with pytest.raises(RevisionResultMismatchError):
        asyncio.run(service.request_revision(format_id="fmt_original", feedback=_feedback()))


def test_revision_translates_provider_failure_without_retry() -> None:
    reviewer = SpyAgentRevision(error=AgentRevisionError("Agentes fuera de servicio"))
    source = _source()
    service = FormatRevisionService(
        generated_format_repository=SpyGeneratedFormatRepository(source),
        agent_revision=reviewer,
    )
    with pytest.raises(FormatRevisionIntegrationError, match="fmt_original"):
        asyncio.run(service.request_revision(format_id="fmt_original", feedback=_feedback()))
    assert len(reviewer.requests) == 1
    assert source.content is not None
    assert source.content.title == "Versión inicial"


@pytest.mark.parametrize("status", [
    GeneratedFormatStatus.FAILED,
    GeneratedFormatStatus.NO_RESULTS,
])
def test_revision_keeps_provider_terminal_failure_as_result(
    status: GeneratedFormatStatus,
) -> None:
    source = _source()
    reviewer = SpyAgentRevision(result=_result(status=status))
    service = FormatRevisionService(
        generated_format_repository=SpyGeneratedFormatRepository(source),
        agent_revision=reviewer,
    )
    result = asyncio.run(service.request_revision(format_id="fmt_original", feedback=_feedback()))
    assert result.status == status
    assert result.content is None
    assert source.content is not None
    assert len(reviewer.requests) == 1


def test_revision_can_call_http_adapter_through_port() -> None:
    """Integración local app -> puerto -> adaptador -> HTTP simulado (NO E2E real)."""
    original = _source()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/revise"
        payload = json.loads(request.content)
        assert payload["document_id"] == original.document_id
        assert payload["current_content"] == original.content.to_dict()
        assert payload["chunks_used"] == [chunk.to_dict() for chunk in original.chunks_used]
        assert payload["feedback"]["verdict"] == "requires_revision"
        result = _result()
        assert result.content is not None
        return httpx.Response(200, json={
            "document_id": result.document_id,
            "format": result.format_type.value,
            "status": result.status.value,
            "content": result.content.to_dict(),
            "sources_used": [chunk.to_dict() for chunk in result.chunks_used],
            "execution_time_seconds": result.execution_time_seconds,
            "error": None,
            "error_message": None,
        })

    async def run_test() -> AgentRevisionResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://agents.test",
        ) as client:
            service = FormatRevisionService(
                generated_format_repository=SpyGeneratedFormatRepository(original),
                agent_revision=HTTPAgentRevisionAdapter(client=client),
            )
            return await service.request_revision(format_id="fmt_original", feedback=_feedback())

    result = asyncio.run(run_test())
    assert result.status == GeneratedFormatStatus.SUCCESS
    assert result.content is not None
    assert result.content.title == "Versión revisada"
