"""Pruebas unitarias del adaptador HTTP BackendAPI-Agentes."""

import asyncio
import json

import httpx
import pytest

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    FlashcardsContent,
    QuizContent,
)
from app.domain.generated_format import GenerationContext
from app.infrastructure.integrations.http_agents_adapter import (
    HTTPAgentsAdapter,
)
from app.ports.agents_port import (
    AgentGenerationInput,
    AgentsError,
)


def _build_request(
    *,
    learning_objective: str | None = (
        "Comprender conceptos clave."
    ),
) -> AgentGenerationInput:
    """Construye una solicitud representativa hacia Agentes."""
    return AgentGenerationInput(
        document_id="doc_123",
        formats=(
            GeneratedFormatType.QUIZ,
            GeneratedFormatType.FLASHCARDS,
        ),
        generation_context=GenerationContext(
            profile="beginner",
            niche="technology",
            detail_level="detailed",
            learning_objective=learning_objective,
        ),
    )


def _success_response() -> dict[str, object]:
    """Construye una respuesta canónica válida de Agentes."""
    evidence = [
        {
            "rank": 1,
            "chunk_id": "chunk_1",
            "document_id": "doc_123",
            "score": 0.93,
            "text": "Texto utilizado como evidencia.",
        }
    ]

    return {
        "document_id": "doc_123",
        "results": [
            {
                "format": "quiz",
                "status": "success",
                "content": {
                    "title": "Quiz de prueba",
                    "instructions": (
                        "Seleccione la respuesta correcta."
                    ),
                    "questions": [
                        {
                            "question_id": "q_1",
                            "question": (
                                "¿Qué componente orquesta "
                                "el producto?"
                            ),
                            "options": [
                                "BackendAPI",
                                "Frontend",
                            ],
                            "correct_answer": "BackendAPI",
                            "explanation": (
                                "BackendAPI coordina las "
                                "integraciones."
                            ),
                        }
                    ],
                },
                "sources_used": evidence,
                "error_message": None,
            },
            {
                "format": "flashcards",
                "status": "success",
                "content": {
                    "title": "Flashcards de prueba",
                    "instructions": (
                        "Revise cada tarjeta."
                    ),
                    "cards": [
                        {
                            "card_id": "card_1",
                            "front": "BackendAPI",
                            "back": (
                                "Orquestador del producto."
                            ),
                        }
                    ],
                },
                "sources_used": evidence,
                "error_message": None,
            },
        ],
    }


def test_http_agents_adapter_sends_canonical_request() -> None:
    """Envía a Agentes el contrato acordado de generación."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.url.path
            == "/api/v1/generate"
        )

        payload = json.loads(
            request.content
        )

        assert payload == {
            "document_id": "doc_123",
            "formats": [
                "quiz",
                "flashcards",
            ],
            "profile": "beginner",
            "niche": "technology",
            "detail_level": "detailed",
            "learning_objective": (
                "Comprender conceptos clave."
            ),
        }

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
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path="/api/v1/generate",
            )

            await adapter.generate_formats(
                _build_request()
            )

    asyncio.run(
        run_test()
    )


def test_http_agents_adapter_maps_successful_formats() -> None:
    """Mapea Quiz, Flashcards y evidencias al dominio Backend."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=200,
            json=_success_response(),
        )
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path="/api/v1/generate",
            )

            result = await adapter.generate_formats(
                _build_request()
            )

            assert (
                result.document_id
                == "doc_123"
            )

            assert len(
                result.results
            ) == 2

            quiz = result.results[0]

            assert (
                quiz.status
                == GeneratedFormatStatus.SUCCESS
            )
            assert isinstance(
                quiz.content,
                QuizContent,
            )
            assert (
                quiz.content.questions[0]
                .correct_answer
                == "BackendAPI"
            )
            assert (
                quiz.chunks_used[0].chunk_id
                == "chunk_1"
            )

            flashcards = result.results[1]

            assert isinstance(
                flashcards.content,
                FlashcardsContent,
            )
            assert (
                flashcards.content.cards[0]
                .card_id
                == "card_1"
            )

    asyncio.run(
        run_test()
    )


def test_http_agents_adapter_maps_no_results() -> None:
    """Conserva no_results y su mensaje de error."""

    response_payload = {
        "document_id": "doc_123",
        "results": [
            {
                "format": "quiz",
                "status": "no_results",
                "content": None,
                "sources_used": [],
                "error_message": (
                    "No se encontró contexto suficiente."
                ),
            }
        ],
    }

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=200,
            json=response_payload,
        )
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path="/api/v1/generate",
            )

            request = AgentGenerationInput(
                document_id="doc_123",
                formats=(
                    GeneratedFormatType.QUIZ,
                ),
                generation_context=GenerationContext(
                    profile="beginner",
                    niche="technology",
                    detail_level="standard",
                ),
            )

            result = await adapter.generate_formats(
                request
            )

            generated = result.results[0]

            assert (
                generated.status
                == GeneratedFormatStatus.NO_RESULTS
            )
            assert generated.content is None
            assert generated.chunks_used == ()
            assert generated.error_message == (
                "No se encontró contexto suficiente."
            )

    asyncio.run(
        run_test()
    )


def test_http_agents_adapter_omits_optional_objective() -> None:
    """No envía learning_objective cuando no fue informado."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        payload = json.loads(
            request.content
        )

        assert (
            "learning_objective"
            not in payload
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
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path="/api/v1/generate",
            )

            await adapter.generate_formats(
                _build_request(
                    learning_objective=None
                )
            )

    asyncio.run(
        run_test()
    )


def test_http_agents_adapter_rejects_invalid_content() -> None:
    """Rechaza contenido que incumple el contrato canónico."""

    payload = _success_response()

    payload["results"][0]["content"] = {
        "questions": [],
    }

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=200,
            json=payload,
        )
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path="/api/v1/generate",
            )

            with pytest.raises(
                AgentsError,
                match=(
                    "respuesta de generación inválida"
                ),
            ):
                await adapter.generate_formats(
                    _build_request()
                )

    asyncio.run(
        run_test()
    )


def test_http_agents_adapter_translates_http_error() -> None:
    """Traduce errores HTTP al contrato AgentsError."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=503,
            json={
                "detail": "Servicio no disponible",
            },
        )
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path="/api/v1/generate",
            )

            with pytest.raises(
                AgentsError,
                match="estado HTTP 503",
            ):
                await adapter.generate_formats(
                    _build_request()
                )

    asyncio.run(
        run_test()
    )


def test_http_agents_adapter_translates_timeout() -> None:
    """Traduce timeouts HTTP al contrato AgentsError."""

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
            base_url="http://agents.test",
        ) as client:
            adapter = HTTPAgentsAdapter(
                client=client,
                generate_path="/api/v1/generate",
            )

            with pytest.raises(
                AgentsError,
                match="superó el tiempo permitido",
            ):
                await adapter.generate_formats(
                    _build_request()
                )

    asyncio.run(
        run_test()
    )