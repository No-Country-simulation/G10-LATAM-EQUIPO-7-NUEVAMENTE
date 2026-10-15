"""Pruebas unitarias de la orquestación de una sola corrección."""

import asyncio
from dataclasses import replace

import pytest

from app.application.format_auto_revision_service import (
    FormatAutoReevaluationError,
    FormatAutoRevisionError,
    FormatAutoRevisionService,
)
from app.application.format_evaluation_feedback_mapper import build_revision_feedback
from app.application.format_revision_service import FormatRevisionIntegrationError
from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.format_evaluation import (
    EvaluationScores,
    FormatEvaluation,
    HeuristicScoresV2,
    SemanticEvaluationResult,
    SemanticRecommendation,
)
from app.domain.generated_content import TLDRContent
from app.domain.generated_format import ChunkEvidence, GeneratedFormat, GenerationContext
from app.ports.agent_revision_port import AgentRevisionResult


class MemoryFormats:
    """Implementación mínima del repositorio para verificar persistencia."""

    def __init__(self, original: GeneratedFormat) -> None:
        self.items = {original.format_id: original}
        self.created: list[GeneratedFormat] = []
        self.updated: list[GeneratedFormat] = []

    def find_by_document_id(self, document_id: str) -> list[GeneratedFormat]:
        return [item for item in self.items.values() if item.document_id == document_id]

    def find_by_id(self, format_id: str) -> GeneratedFormat | None:
        return self.items.get(format_id)

    def create(self, item: GeneratedFormat) -> GeneratedFormat:
        if any(i.revision_of_format_id == item.revision_of_format_id
               for i in self.items.values() if item.revision_of_format_id is not None):
            raise ValueError("Revisión duplicada")
        self.items[item.format_id] = item
        self.created.append(item)
        return item

    def update(self, item: GeneratedFormat) -> GeneratedFormat:
        self.items[item.format_id] = item
        self.updated.append(item)
        return item


class StubRevision:
    """Simula el revisor sin realizar HTTP."""

    def __init__(self, result: AgentRevisionResult | None = None, error=None) -> None:
        self.calls = 0
        self.result = result
        self.error = error

    async def request_revision(
        self, *, format_id: str, feedback,
        revision_id: str | None = None,
        evaluator_response: dict[str, object] | None = None,
    ):
        assert revision_id is not None
        assert evaluator_response is not None
        assert evaluator_response["verdict"] in ("requires_revision", "rejected")
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert format_id == "fmt_base"
        assert feedback.verdict in ("requires_revision", "rejected")
        assert self.result is not None
        return self.result


class StubEvaluator:
    """Simula la reevaluación de la versión corregida."""

    def __init__(self, error=None) -> None:
        self.calls: list[str] = []
        self.error = error

    async def evaluate_format(self, format_id: str):
        self.calls.append(format_id)
        if self.error is not None:
            raise self.error


def source() -> GeneratedFormat:
    return GeneratedFormat(
        format_id="fmt_base",
        document_id="doc_1",
        format_type=GeneratedFormatType.TLDR,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=GenerationContext(
            profile="beginner", niche="software", detail_level="medium",
        ),
        content=TLDRContent(
            title="Original", summary="Resumen original",
            key_points=("Concepto",), conclusion="Conclusión",
        ),
        chunks_used=(ChunkEvidence(
            chunk_id="c1", document_id="doc_1", rank=1,
            score=0.9, text="Evidencia factual.",
        ),),
    )


def evaluation(verdict: str = "requires_revision", actionable: bool = True) -> FormatEvaluation:
    return FormatEvaluation(
        evaluation_id="eval_1",
        format_id="fmt_base",
        verdict=verdict,
        evaluator_version="2.0.0",
        rubric_version="2.0.0",
        heuristic_scores=HeuristicScoresV2(
            relevance=4.0, coherence=3.0,
            didactic_adaptation=2.0, content_support=4.0,
        ),
        semantic_evaluation=SemanticEvaluationResult(
            status="unavailable",
            error_code="not_configured",
            recommendations=(
                (SemanticRecommendation(
                    dimension="didactic_adaptation",
                    message="Simplificar lenguaje.",
                ),) if actionable else ()
            ),
        ),
    )


def result(status: GeneratedFormatStatus = GeneratedFormatStatus.SUCCESS) -> AgentRevisionResult:
    original = source()
    return AgentRevisionResult(
        document_id=original.document_id,
        format_type=original.format_type,
        status=status,
        content=(
            TLDRContent(
                title="Revisado", summary="Resumen corregido",
                key_points=("Claridad",), conclusion="Nueva conclusión",
            ) if status == GeneratedFormatStatus.SUCCESS else None
        ),
        chunks_used=(original.chunks_used if status == GeneratedFormatStatus.SUCCESS else ()),
        execution_time_seconds=1.0,
    )


def build_service(original=None, agent=None, evaluator=None):
    formats = MemoryFormats(original or source())
    agent = agent or StubRevision(result())
    evaluator = evaluator or StubEvaluator()
    service = FormatAutoRevisionService(
        generated_format_repository=formats,
        format_revision_service=agent,
        format_evaluation_service=evaluator,
    )
    return service, formats, agent, evaluator


def test_mapper_only_converts_actionable_negative_v2() -> None:
    assert build_revision_feedback(evaluation("approved")) is None
    assert build_revision_feedback(evaluation(actionable=False)) is None
    assert build_revision_feedback(evaluation()) is not None


def test_success_creates_one_revision_and_reevaluates_it() -> None:
    original = source()
    service, formats, agent, evaluator = build_service(original=original)
    revised = asyncio.run(service.revise_if_required(original=original, evaluation=evaluation()))
    assert revised is not None
    assert revised.status == GeneratedFormatStatus.SUCCESS
    assert revised.revision_of_format_id == "fmt_base"
    assert formats.find_by_id("fmt_base") is original
    assert len(formats.created) == 1
    assert formats.created[0].status == GeneratedFormatStatus.PROCESSING
    assert evaluator.calls == [revised.format_id]
    assert agent.calls == 1

    second = asyncio.run(service.revise_if_required(original=source(), evaluation=evaluation()))
    assert second is None
    assert agent.calls == 1


def test_approved_skips_agent_and_reservation() -> None:
    service, formats, agent, evaluator = build_service()
    assert asyncio.run(service.revise_if_required(
        original=source(), evaluation=evaluation("approved")
    )) is None
    assert formats.created == []
    assert agent.calls == 0
    assert evaluator.calls == []


def test_non_actionable_feedback_does_not_revise() -> None:
    service, formats, agent, _ = build_service()
    assert asyncio.run(service.revise_if_required(
        original=source(), evaluation=evaluation(actionable=False)
    )) is None
    assert formats.created == []
    assert agent.calls == 0


def test_failed_agent_result_is_persisted_without_evaluation() -> None:
    service, formats, agent, evaluator = build_service(
        agent=StubRevision(result(GeneratedFormatStatus.NO_RESULTS))
    )
    revised = asyncio.run(service.revise_if_required(original=source(), evaluation=evaluation()))
    assert revised is not None
    assert revised.status == GeneratedFormatStatus.NO_RESULTS
    assert formats.updated[-1].status == GeneratedFormatStatus.NO_RESULTS
    assert evaluator.calls == []
    assert agent.calls == 1


def test_transport_error_closes_reservation_and_does_not_retry() -> None:
    service, formats, agent, _ = build_service(
        agent=StubRevision(error=FormatRevisionIntegrationError("timeout"))
    )
    with pytest.raises(FormatAutoRevisionError):
        asyncio.run(service.revise_if_required(original=source(), evaluation=evaluation()))
    assert formats.updated[-1].status == GeneratedFormatStatus.FAILED
    assert agent.calls == 1
    assert asyncio.run(service.revise_if_required(
        original=source(), evaluation=evaluation()
    )) is None
    assert agent.calls == 1


def test_reevaluation_error_does_not_change_successful_revision() -> None:
    service, formats, _, evaluator = build_service(
        evaluator=StubEvaluator(error=RuntimeError("Data IA unavailable"))
    )
    with pytest.raises(FormatAutoReevaluationError):
        asyncio.run(service.revise_if_required(original=source(), evaluation=evaluation()))
    assert formats.updated[-1].status == GeneratedFormatStatus.SUCCESS
    assert len(evaluator.calls) == 1


def test_version_identity_is_validated() -> None:
    service, formats, agent, _ = build_service()
    with pytest.raises(ValueError, match="evaluación"):
        asyncio.run(service.revise_if_required(
            original=source(),
            evaluation=replace(evaluation(), format_id="other"),
        ))
    assert formats.created == []
    assert agent.calls == 0


def test_adaptation_invokes_auto_revision_after_evaluation() -> None:
    """La orquestación general incorpora revisión solo cuando está habilitada."""
    from app.application.adaptation_orchestration_service import AdaptationOrchestrationService

    class Evaluator:
        def __init__(self):
            self.calls: list[str] = []

        async def evaluate_format(self, format_id: str):
            self.calls.append(format_id)
            return evaluation()

    class AutoRevision:
        def __init__(self):
            self.calls: list[str] = []

        async def revise_if_required(self, *, original, evaluation):
            self.calls.append(original.format_id)
            return None

    evaluator = Evaluator()
    revisor = AutoRevision()
    orchestration = AdaptationOrchestrationService(
        document_service=None,
        rag_integration_service=None,
        format_generation_service=None,
        generated_package_storage_service=None,
        format_evaluation_service=evaluator,
        format_auto_revision_service=revisor,
    )
    asyncio.run(orchestration._evaluate_completed_formats([source()]))
    assert evaluator.calls == ["fmt_base"]
    assert revisor.calls == ["fmt_base"]


def test_adaptation_keeps_previous_behavior_when_auto_revision_disabled() -> None:
    """Sin activar la opción no se hacen llamadas adicionales a Agentes."""
    from app.application.adaptation_orchestration_service import AdaptationOrchestrationService

    class Evaluator:
        def __init__(self):
            self.calls = 0

        async def evaluate_format(self, format_id: str):
            self.calls += 1
            return evaluation()

    evaluator = Evaluator()
    orchestration = AdaptationOrchestrationService(
        document_service=None,
        rag_integration_service=None,
        format_generation_service=None,
        generated_package_storage_service=None,
        format_evaluation_service=evaluator,
    )
    asyncio.run(orchestration._evaluate_completed_formats([source()]))
    assert evaluator.calls == 1


def test_v1_evaluation_does_not_enable_revision() -> None:
    """La corrección automática depende del contrato V2, no del V1."""
    v1 = FormatEvaluation(
        evaluation_id="eval_v1",
        format_id="fmt_base",
        status=FormatEvaluationStatus.REQUIRES_REVIEW,
        scores=EvaluationScores(
            relevance=3, coherence=3, didactic_adaptation=2, content_support=3,
        ),
    )
    service, formats, agent, _ = build_service()
    assert asyncio.run(service.revise_if_required(
        original=source(), evaluation=v1
    )) is None
    assert agent.calls == 0
    assert formats.created == []
