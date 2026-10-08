"""Pruebas de integración HTTP para TLDR y Video Script."""

import asyncio
import json

import httpx
import pytest

from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    TLDRContent,
    VideoScriptContent,
    VideoScriptScene,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GenerationContext,
)
from app.infrastructure.integrations.http_agents_adapter import (
    HTTPAgentsAdapter,
)
from app.infrastructure.integrations.http_data_ia_adapter import (
    HTTPDataIAAdapter,
)
from app.ports.agents_port import (
    AgentGenerationInput,
)
from app.ports.data_ia_port import (
    DataIAEvaluationInput,
)


def _context() -> GenerationContext:
    """Construye contexto pedagógico compartido."""
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
        learning_objective=(
            "Comprender la arquitectura."
        ),
    )


def _evidence_payload() -> list[
    dict[str, object]
]:
    """Construye evidencia en el contrato HTTP de Agentes."""
    return [
        {
            "rank": 1,
            "chunk_id": "chunk_1",
            "document_id": "doc_123",
            "score": 0.95,
            "text": (
                "BackendAPI coordina integraciones."
            ),
        }
    ]


def _evidence() -> tuple[
    ChunkEvidence,
    ...,
]:
    """Construye evidencia canónica de BackendAPI."""
    return (
        ChunkEvidence(
            chunk_id="chunk_1",
            document_id="doc_123",
            rank=1,
            score=0.95,
            text=(
                "BackendAPI coordina integraciones."
            ),
        ),
    )


def _tldr() -> TLDRContent:
    """Construye contenido TLDR."""
    return TLDRContent(
        title="Resumen",
        summary="Backend coordina servicios.",
        key_points=(
            "Orquestación",
        ),
        conclusion=(
            "La arquitectura queda desacoplada."
        ),
    )


def _video_script() -> VideoScriptContent:
    """Construye contenido Video Script."""
    return VideoScriptContent(
        title="Guion",
        estimated_duration_minutes=1,
        scenes=(
            VideoScriptScene(
                scene_id="scene_1",
                title="Introducción",
                visual_description=(
                    "Diagrama de servicios."
                ),
                narration=(
                    "Backend coordina servicios."
                ),
                duration_seconds=30,
            ),
        ),
    )


def test_http_agents_adapter_maps_tldr_and_video_script() -> None:
    """Agentes puede entregar los dos nuevos contratos al Backend."""
    received_request: dict[
        str,
        object,
    ] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        received_request.update(
            json.loads(
                request.content
            )
        )

        return httpx.Response(
            200,
            json={
                "document_id": "doc_123",
                "learning_metadata": {
                    "key_concepts": [
                        "Arquitectura"
                    ],
                    "prerequisites": [],
                    "estimated_time_minutes": 10,
                },
                "results": [
                    {
                        "format": "tldr",
                        "status": "success",
                        "content": (
                            _tldr().to_dict()
                        ),
                        "sources_used": (
                            _evidence_payload()
                        ),
                        "error_message": None,
                    },
                    {
                        "format": "video_script",
                        "status": "success",
                        "content": (
                            _video_script()
                            .to_dict()
                        ),
                        "sources_used": (
                            _evidence_payload()
                        ),
                        "error_message": None,
                    },
                ],
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(
            handler
        )

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path=(
                    "/api/v1/generate"
                ),
            )

            result = await adapter.generate_formats(
                AgentGenerationInput(
                    document_id="doc_123",
                    formats=(
                        GeneratedFormatType.TLDR,
                        GeneratedFormatType.VIDEO_SCRIPT,
                    ),
                    generation_context=_context(),
                )
            )

        assert received_request[
            "formats"
        ] == [
            "tldr",
            "video_script",
        ]

        assert isinstance(
            result.results[0].content,
            TLDRContent,
        )

        assert isinstance(
            result.results[1].content,
            VideoScriptContent,
        )

    asyncio.run(
        run_test()
    )


@pytest.mark.parametrize(
    ("format_type", "content"),
    [
        (
            GeneratedFormatType.TLDR,
            _tldr(),
        ),
        (
            GeneratedFormatType.VIDEO_SCRIPT,
            _video_script(),
        ),
    ],
)
def test_http_data_ia_adapter_evaluates_additional_formats(
    format_type: GeneratedFormatType,
    content,
) -> None:
    """Data/IA recibe exactamente el contenido canónico de cada formato."""
    received_payload: dict[
        str,
        object,
    ] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        received_payload.update(
            json.loads(
                request.content
            )
        )

        return httpx.Response(
            200,
            json={
                "document_id": "doc_123",
                "format": format_type.value,
                "status": "aprobado",
                "scores": {
                    "relevancia": 5,
                    "coherencia": 5,
                    "adaptacion_didactica": 5,
                    "informacion_respaldada": 4,
                },
                "informacion_no_respaldada": False,
                "observaciones": [],
                "evaluator_version": "1.0.0",
                "rubric_version": "1.0.0",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(
            handler
        )

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate",
            )

            result = await adapter.evaluate(
                DataIAEvaluationInput(
                    document_id="doc_123",
                    format_type=format_type,
                    generated_content=content,
                    chunks_used=_evidence(),
                    generation_context=_context(),
                )
            )

        assert (
            received_payload["format"]
            == format_type.value
        )
        assert (
            received_payload[
                "generated_content"
            ]
            == content.to_dict()
        )
        assert (
            result.format_type
            == format_type
        )
        assert (
            result.status
            == FormatEvaluationStatus.APPROVED
        )

    asyncio.run(
        run_test()
    )
