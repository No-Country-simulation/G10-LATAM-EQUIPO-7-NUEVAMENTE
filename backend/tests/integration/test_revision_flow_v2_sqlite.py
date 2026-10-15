"""Pruebas de integración del ciclo de revisión Sprint 4.

Se utiliza SQLite real en un archivo temporal y los adaptadores HTTP de
producción con ``httpx.MockTransport``. No hay llamadas de red, Gemini ni OCI.
Estas pruebas no sustituyen la validación end-to-end contra Agentes/Data/IA.
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from app.application.adaptation_orchestration_service import AdaptationOrchestrationService
from app.application.format_auto_revision_service import FormatAutoRevisionService
from app.application.format_evaluation_service import FormatEvaluationService
from app.application.format_revision_history_service import FormatRevisionHistoryService
from app.application.format_revision_service import FormatRevisionService
from app.application.generated_format_query_service import GeneratedFormatQueryService
from app.application.generated_package_storage_service import GeneratedPackageStorageService
from app.domain.document import Document
from app.domain.enums import DocumentStatus, GeneratedFormatStatus, GeneratedFormatType
from app.domain.generated_content import TLDRContent
from app.domain.generated_format import ChunkEvidence, GeneratedFormat, GenerationContext
from app.domain.learning_metadata import LearningMetadata
from app.infrastructure.integrations.http_agent_revision_adapter import HTTPAgentRevisionAdapter
from app.infrastructure.integrations.http_data_ia_adapter import HTTPDataIAAdapter
from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_format_evaluation_repository_adapter import (
    SQLiteFormatEvaluationRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)

DOCUMENT_ID = "doc_integration_v2"
ROOT_ID = "fmt_integration_root"


class CapturingObjectStorage:
    """Puerto mínimo: guarda el paquete en memoria, no llama a OCI."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.write_count = 0

    def upload_bytes(
        self, *, content: bytes, object_name: str, content_type: str | None = None
    ) -> None:
        assert content_type == "application/json"
        self.objects[object_name] = content
        self.write_count += 1


class CompletedGeneration:
    """No llama a Agentes/generación: completa un intento ya persistido."""

    async def complete_generation(
        self, *, attempts: tuple[GeneratedFormat, ...]
    ) -> list[GeneratedFormat]:
        return list(attempts)


class HttpScenario:
    """Simula los contratos HTTP públicos con respuestas configurables."""

    def __init__(
        self,
        *,
        first_verdict: str | None = "requires_revision",
        second_verdict: str | None = "approved",
        agent_result: str = "success",
        second_evaluation_error: bool = False,
    ) -> None:
        self.first_verdict = first_verdict
        self.second_verdict = second_verdict
        self.agent_result = agent_result
        self.second_evaluation_error = second_evaluation_error
        self.agent_requests: list[dict[str, object]] = []
        self.evaluation_requests: list[dict[str, object]] = []

    def agents_handler(self, request: httpx.Request) -> httpx.Response:
        """Registra el contrato V2 recibido y devuelve un resultado atómico."""
        assert request.url.path == "/api/v1/revise"
        body = json.loads(request.content)
        self.agent_requests.append(body)

        if self.agent_result == "timeout":
            raise httpx.ReadTimeout("Timeout simulado de Agentes", request=request)

        if self.agent_result == "failed":
            return httpx.Response(
                503,
                json={
                    "revision_id": body["revision_id"],
                    "original_format_id": body["original_format_id"],
                    "document_id": body["document_id"],
                    "format": body["format"],
                    "status": "failed",
                    "content": None,
                    "sources_used": [],
                    "execution_time_seconds": 0.4,
                    "error_message": "Gemini no disponible",
                    "error": {
                        "code": "PROVIDER_UNAVAILABLE",
                        "message": "Gemini no disponible",
                        "retryable": True,
                        "http_status": 503,
                        "upstream_status": 503,
                        "provider": "gemini",
                    },
                },
            )

        content = TLDRContent(
            title="Versión corregida",
            summary="Una explicación más clara y fundamentada.",
            key_points=("Concepto corregido",),
            conclusion="Conclusión corregida.",
        ).to_dict()
        if self.agent_result == "invalid_content":
            content = {}

        return httpx.Response(
            200,
            json={
                "revision_id": (
                    "revision_incorrecta"
                    if self.agent_result == "wrong_id"
                    else body["revision_id"]
                ),
                "original_format_id": body["original_format_id"],
                "document_id": body["document_id"],
                "format": body["format"],
                "status": "success",
                "content": content,
                "sources_used": body["chunks_used"],
                "execution_time_seconds": 0.9,
                "error_message": None,
                "error": None,
            },
        )

    def data_handler(self, request: httpx.Request) -> httpx.Response:
        """Primera evaluación de la raíz; segunda, de la corrección."""
        assert request.url.path == "/evaluate/v2"
        body = json.loads(request.content)
        self.evaluation_requests.append(body)
        is_revision = len(self.evaluation_requests) > 1

        if is_revision and self.second_evaluation_error:
            return httpx.Response(503, json={"detail": "Proveedor caído"})

        verdict = self.second_verdict if is_revision else self.first_verdict
        actionable = verdict in ("requires_revision", "rejected")
        scores = None if verdict is None else {
            "relevance": 4.0,
            "coherence": 3.5,
            "didactic_adaptation": 2.0 if actionable else 4.5,
            "content_support": 4.0,
        }
        return httpx.Response(
            200,
            json={
                "document_id": body["document_id"],
                "format": body["format"],
                "verdict": verdict,
                "heuristic_scores": scores,
                "semantic_evaluation": {
                    "status": "unavailable",
                    "scores": None,
                    "observations": [],
                    "recommendations": (
                        [{
                            "dimension": "didactic_adaptation",
                            "message": "Simplificar términos y aportar un ejemplo.",
                            "item_id": None,
                        }] if actionable else []
                    ),
                    "unsupported_information": [],
                    "error_code": "not_configured",
                    "error_message": None,
                    "model": None,
                    "prompt_version": None,
                    "latency_ms": None,
                },
                "evaluator_version": "2.0-integration",
                "rubric_version": "2.0-integration",
            },
        )


@dataclass(slots=True)
class FlowResult:
    """Datos observables después de ejecutar el flujo integrado."""

    scenario: HttpScenario
    versions: list[GeneratedFormat]
    original_evaluations: list
    revision_evaluations: list
    history: object
    public_formats: object
    oci_package: dict[str, object]
    oci_writes: int
    duplicate_result: GeneratedFormat | None


def create_original() -> GeneratedFormat:
    """Genera contenido inicial con evidencia documental consistente."""
    return GeneratedFormat(
        format_id=ROOT_ID,
        document_id=DOCUMENT_ID,
        format_type=GeneratedFormatType.TLDR,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=GenerationContext(
            profile="profesional",
            niche="arquitectura de software",
            detail_level="avanzado",
            learning_objective="Comprender el desacoplamiento",
        ),
        content=TLDRContent(
            title="Versión original",
            summary="Resumen inicial con términos complejos.",
            key_points=("Desacoplamiento",),
            conclusion="Conclusión original.",
        ),
        chunks_used=(ChunkEvidence(
            chunk_id="chunk_doc_1",
            document_id=DOCUMENT_ID,
            rank=1,
            score=0.94,
            text="El desacoplamiento separa responsabilidades del software.",
        ),),
    )


def create_document() -> Document:
    """Documento válido con metadatos, apto para construir snapshot OCI."""
    raw = b"manual de arquitectura de software"
    return Document(
        document_id=DOCUMENT_ID,
        original_filename="manual.txt",
        sha256=hashlib.sha256(raw).hexdigest(),
        content_type="text/plain",
        size_bytes=len(raw),
        status=DocumentStatus.INDEXED,
        learning_metadata=LearningMetadata(
            key_concepts=("desacoplamiento",),
            prerequisites=("arquitectura",),
            estimated_time_minutes=12,
        ),
    )


def execute_flow(tmp_path: Path, scenario: HttpScenario) -> FlowResult:
    """Ejecuta orquestación de aplicación con BD real y HTTP sin red.

    Crea un archivo SQLite separado por test, una única generación inicial y
    el snapshot mediante el mismo servicio de producción que usa Object Storage.
    """
    database = SQLiteDatabase(f"sqlite:///{(tmp_path / 'revision_v2.db').as_posix()}")
    database.initialize()
    documents = SQLiteDocumentRepositoryAdapter(database)
    formats = SQLiteGeneratedFormatRepositoryAdapter(database)
    evaluations = SQLiteFormatEvaluationRepositoryAdapter(database)
    documents.create(create_document())
    root = formats.create(create_original())
    storage = CapturingObjectStorage()
    package_service = GeneratedPackageStorageService(
        document_repository=documents,
        generated_format_repository=formats,
        object_storage=storage,
    )

    async def run() -> GeneratedFormat | None:
        """Conserva vivos los clientes HTTP durante ambos turnos de evaluación."""
        async with (
            httpx.AsyncClient(
                base_url="http://agentes.test",
                transport=httpx.MockTransport(scenario.agents_handler),
            ) as agent_client,
            httpx.AsyncClient(
                base_url="http://data-ia.test",
                transport=httpx.MockTransport(scenario.data_handler),
            ) as data_client,
        ):
            evaluator = FormatEvaluationService(
                generated_format_repository=formats,
                evaluation_repository=evaluations,
                data_ia=HTTPDataIAAdapter(client=data_client, evaluate_path="/evaluate/v2"),
            )
            revisor = FormatRevisionService(
                generated_format_repository=formats,
                agent_revision=HTTPAgentRevisionAdapter(client=agent_client),
            )
            auto_revision = FormatAutoRevisionService(
                generated_format_repository=formats,
                format_revision_service=revisor,
                format_evaluation_service=evaluator,
            )
            orchestration = AdaptationOrchestrationService(
                document_service=None,
                rag_integration_service=None,
                format_generation_service=CompletedGeneration(),
                generated_package_storage_service=package_service,
                format_evaluation_service=evaluator,
                format_auto_revision_service=auto_revision,
            )
            completed = await orchestration.complete_default_generation(attempts=(root,))
            assert [item.format_id for item in completed] == [ROOT_ID]

            # Invocar una segunda vez el MISMO ciclo no debe llamar a Agentes.
            original_evals = evaluations.find_by_format_id(ROOT_ID)
            assert len(original_evals) == 1
            return await auto_revision.revise_if_required(
                original=root,
                evaluation=original_evals[0],
            )

    duplicate_result = asyncio.run(run())
    stored_versions = formats.find_by_document_id(DOCUMENT_ID)
    revisions = [v for v in stored_versions if v.revision_of_format_id == ROOT_ID]
    history = FormatRevisionHistoryService(
        document_repository=documents,
        generated_format_repository=formats,
        evaluation_repository=evaluations,
    ).get_history(DOCUMENT_ID, GeneratedFormatType.TLDR)
    public_formats = GeneratedFormatQueryService(
        document_repository=documents,
        generated_format_repository=formats,
    ).get_document_formats(DOCUMENT_ID)
    object_name = f"documents/{DOCUMENT_ID}/generated/content.json"
    return FlowResult(
        scenario=scenario,
        versions=stored_versions,
        original_evaluations=evaluations.find_by_format_id(ROOT_ID),
        revision_evaluations=(
            evaluations.find_by_format_id(revisions[0].format_id) if revisions else []
        ),
        history=history,
        public_formats=public_formats,
        oci_package=json.loads(storage.objects[object_name]),
        oci_writes=storage.write_count,
        duplicate_result=duplicate_result,
    )


def get_revision(result: FlowResult) -> GeneratedFormat:
    """Recupera la única revisión creada por el orquestador."""
    revisions = [v for v in result.versions if v.revision_of_format_id == ROOT_ID]
    assert len(revisions) == 1
    return revisions[0]


@pytest.mark.parametrize("initial_verdict", ["requires_revision", "rejected"])
def test_full_cycle_persists_revises_reevaluates_and_publishes(
    tmp_path: Path, initial_verdict: str
) -> None:
    """Prueba juntos adaptadores HTTP, servicios, SQLite, historial y snapshot."""
    result = execute_flow(tmp_path, HttpScenario(first_verdict=initial_verdict))
    revision = get_revision(result)

    assert revision.status == GeneratedFormatStatus.SUCCESS
    assert revision.content is not None
    assert revision.content.title == "Versión corregida"
    assert result.versions[0].format_id == ROOT_ID
    assert result.versions[0].content.title == "Versión original"
    assert result.original_evaluations[0].verdict == initial_verdict
    assert result.revision_evaluations[0].verdict == "approved"
    assert result.history.cycles[0].original.generated_format.format_id == ROOT_ID
    assert result.history.cycles[0].revision.generated_format.format_id == revision.format_id
    assert result.history.cycles[0].latest_evaluation.format_id == revision.format_id
    assert result.oci_package["formats"]["tldr"]["format_id"] == revision.format_id
    assert result.oci_writes == 1
    assert result.duplicate_result is None

    requests = result.scenario.agent_requests
    assert len(requests) == 1
    assert requests[0]["revision_id"] == revision.format_id
    assert requests[0]["original_format_id"] == ROOT_ID
    assert requests[0]["chunks_used"] == [c.to_dict() for c in create_original().chunks_used]
    assert requests[0]["evaluator_response"]["verdict"] == initial_verdict
    assert len(result.scenario.evaluation_requests) == 2
    assert result.scenario.evaluation_requests[1]["generated_content"]["title"] == (
        "Versión corregida"
    )
    assert result.public_formats.formats[0].format_id == revision.format_id


@pytest.mark.parametrize("verdict", ["approved", None])
def test_approved_or_unavailable_verdict_never_calls_revisor(
    tmp_path: Path, verdict: str | None
) -> None:
    """La ausencia de decisión negativa no reserva revisiones ni llama al LLM."""
    result = execute_flow(tmp_path, HttpScenario(first_verdict=verdict))
    assert len(result.versions) == 1
    assert result.original_evaluations[0].verdict == verdict
    assert result.scenario.agent_requests == []
    assert len(result.scenario.evaluation_requests) == 1
    assert result.oci_package["formats"]["tldr"]["format_id"] == ROOT_ID
    assert result.duplicate_result is None


def test_negative_second_verdict_does_not_chain_new_revision(tmp_path: Path) -> None:
    """Una corrección rechazada queda registrada sin provocar otra corrección."""
    result = execute_flow(tmp_path, HttpScenario(second_verdict="rejected"))
    revision = get_revision(result)
    assert revision.status == GeneratedFormatStatus.SUCCESS
    assert result.revision_evaluations[0].verdict == "rejected"
    assert result.history.cycles[0].latest_evaluation.format_id == revision.format_id
    assert len(result.scenario.agent_requests) == 1
    assert result.duplicate_result is None


def test_agent_terminal_failure_preserves_original_and_history(tmp_path: Path) -> None:
    """Un 503 con error estructurado es resultado failed, no una sustitución."""
    result = execute_flow(tmp_path, HttpScenario(agent_result="failed"))
    revision = get_revision(result)
    assert revision.status == GeneratedFormatStatus.FAILED
    assert revision.content is None
    assert result.revision_evaluations == []
    assert result.history.cycles[0].latest_evaluation is None
    assert result.versions[0].status == GeneratedFormatStatus.SUCCESS
    assert result.oci_package["formats"]["tldr"]["format_id"] == ROOT_ID
    assert len(result.scenario.agent_requests) == 1
    assert len(result.scenario.evaluation_requests) == 1
    assert result.duplicate_result is None


@pytest.mark.parametrize("mode", ["wrong_id", "invalid_content", "timeout"])
def test_invalid_agent_response_or_timeout_closes_reserved_revision(
    tmp_path: Path, mode: str
) -> None:
    """Un error de contrato/transporte deja FAILED y no duplica la llamada."""
    result = execute_flow(tmp_path, HttpScenario(agent_result=mode))
    revision = get_revision(result)
    assert revision.status == GeneratedFormatStatus.FAILED
    assert revision.error_message is not None
    assert result.revision_evaluations == []
    assert result.oci_package["formats"]["tldr"]["format_id"] == ROOT_ID
    assert len(result.scenario.agent_requests) == 1
    assert result.duplicate_result is None


def test_data_ia_outage_after_revision_preserves_content_and_history(tmp_path: Path) -> None:
    """Fallo en reevaluación conserva SUCCESS sin fabricar evaluación aprobada."""
    result = execute_flow(tmp_path, HttpScenario(second_evaluation_error=True))
    revision = get_revision(result)
    assert revision.status == GeneratedFormatStatus.SUCCESS
    assert result.revision_evaluations == []
    assert result.history.cycles[0].latest_evaluation is None
    assert result.original_evaluations[0].verdict == "requires_revision"
    assert len(result.scenario.agent_requests) == 1
    assert len(result.scenario.evaluation_requests) == 2
    assert result.duplicate_result is None
    # Política actual: OCI conserva el último éxito técnico; no supone aprobación.
    assert result.oci_package["formats"]["tldr"]["format_id"] == revision.format_id
