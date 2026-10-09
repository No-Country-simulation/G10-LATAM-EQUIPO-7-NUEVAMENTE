"""Pruebas unitarias del adaptador HTTP BackendAPI-Data/IA."""

import asyncio
import json

import httpx
import pytest

from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    QuizContent,
    QuizQuestion,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GenerationContext,
)
from app.infrastructure.integrations.http_data_ia_adapter import (
    HTTPDataIAAdapter,
)
from app.ports.data_ia_port import (
    DataIAError,
    DataIAEvaluationInput,
)


def _build_request(
    *,
    learning_objective: str | None = (
        "Comprender arquitectura."
    ),
) -> DataIAEvaluationInput:
    """Construye una solicitud válida hacia Data/IA."""
    return DataIAEvaluationInput(
        document_id="doc_123",
        format_type=GeneratedFormatType.QUIZ,
        generated_content=QuizContent(
            title="Quiz",
            instructions="Seleccione una opción.",
            questions=(
                QuizQuestion(
                    question_id="q1",
                    question="¿Qué componente orquesta?",
                    options=(
                        "BackendAPI",
                        "Frontend",
                    ),
                    correct_answer="BackendAPI",
                    explanation=(
                        "BackendAPI coordina servicios."
                    ),
                ),
            ),
        ),
        chunks_used=(
            ChunkEvidence(
                chunk_id="chunk_1",
                document_id="doc_123",
                rank=1,
                score=0.94,
                text=(
                    "BackendAPI actúa como orquestador."
                ),
            ),
        ),
        generation_context=GenerationContext(
            profile="intermediate",
            niche="backend",
            detail_level="detailed",
            learning_objective=(
                learning_objective
            ),
        ),
    )


def _success_response() -> dict[str, object]:
    """Construye una respuesta válida de Data/IA."""
    return {
        "evaluator_version": "1.0.0",
        "rubric_version": "1.0.0",
        "document_id": "doc_123",
        "format": "quiz",
        "status": "aprobado",
        "scores": {
            "relevancia": 5,
            "coherencia": 4,
            "adaptacion_didactica": 4,
            "informacion_respaldada": 5,
        },
        "informacion_no_respaldada": False,
        "observaciones": [
            "El contenido cumple la rúbrica."
        ],
    }


def test_http_data_ia_adapter_sends_canonical_request() -> None:
    """Envía el contenido ya generado y sus evidencias a Data/IA."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == "/evaluate"

        payload = json.loads(
            request.content
        )

        assert payload["document_id"] == (
            "doc_123"
        )
        assert payload["format"] == "quiz"

        assert payload[
            "generated_content"
        ]["title"] == "Quiz"

        assert payload[
            "generation_context"
        ] == {
            "profile": "intermediate",
            "niche": "backend",
            "detail_level": "detailed",
            "learning_objective": (
                "Comprender arquitectura."
            ),
        }

        assert payload["chunks_used"] == [
            {
                "chunk_id": "chunk_1",
                "document_id": "doc_123",
                "rank": 1,
                "score": 0.94,
                "text": (
                    "BackendAPI actúa como orquestador."
                ),
            }
        ]

        return httpx.Response(
            status_code=200,
            json=_success_response(),
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate",
            )

            await adapter.evaluate(
                _build_request()
            )

    asyncio.run(
        run_test()
    )


def test_http_data_ia_adapter_maps_response_to_domain() -> None:
    """Convierte scores y versionado al dominio de BackendAPI."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=200,
            json=_success_response(),
        )
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate",
            )

            result = await adapter.evaluate(
                _build_request()
            )

            assert result.document_id == "doc_123"
            assert (
                result.format_type
                == GeneratedFormatType.QUIZ
            )
            assert (
                result.status
                == FormatEvaluationStatus.APPROVED
            )
            assert result.scores.relevance == 5
            assert result.scores.coherence == 4
            assert (
                result.scores.didactic_adaptation
                == 4
            )
            assert (
                result.scores.content_support
                == 5
            )
            assert (
                result.unsupported_information
                is False
            )
            assert result.observations == (
                "El contenido cumple la rúbrica.",
            )
            assert (
                result.evaluator_version
                == "1.0.0"
            )
            assert result.rubric_version == (
                "1.0.0"
            )

    asyncio.run(
        run_test()
    )


def test_http_data_ia_adapter_omits_optional_objective() -> None:
    """No envía learning_objective cuando no existe."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        payload = json.loads(
            request.content
        )

        assert (
            "learning_objective"
            not in payload[
                "generation_context"
            ]
        )

        return httpx.Response(
            status_code=200,
            json=_success_response(),
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate",
            )

            await adapter.evaluate(
                _build_request(
                    learning_objective=None
                )
            )

    asyncio.run(
        run_test()
    )


def test_http_data_ia_adapter_rejects_invalid_response() -> None:
    """Rechaza scores fuera del contrato acordado."""

    payload = _success_response()
    payload["scores"]["relevancia"] = 7

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=200,
            json=payload,
        )
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate",
            )

            with pytest.raises(
                DataIAError,
                match=(
                    "respuesta de evaluación inválida"
                ),
            ):
                await adapter.evaluate(
                    _build_request()
                )

    asyncio.run(
        run_test()
    )


def test_http_data_ia_adapter_translates_http_error() -> None:
    """Traduce errores HTTP al contrato DataIAError."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=503,
            json={
                "detail": "Servicio no disponible"
            },
        )
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate",
            )

            with pytest.raises(
                DataIAError,
                match="estado HTTP 503",
            ):
                await adapter.evaluate(
                    _build_request()
                )

    asyncio.run(
        run_test()
    )


def test_http_data_ia_adapter_translates_timeout() -> None:
    """Traduce timeouts HTTP al contrato DataIAError."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://data-ia.test",
        ) as client:
            adapter = HTTPDataIAAdapter(
                client=client,
                evaluate_path="/evaluate",
            )

            with pytest.raises(
                DataIAError,
                match="superó el tiempo permitido",
            ):
                await adapter.evaluate(
                    _build_request()
                )

    asyncio.run(
        run_test()
    )
