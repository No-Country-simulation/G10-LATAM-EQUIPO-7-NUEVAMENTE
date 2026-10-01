"""Pruebas de integración BackendAPI → Agentes → persistencia SQLite."""

import asyncio
import hashlib
import json
from pathlib import Path

import httpx

from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.domain.document import Document
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    FlashcardsContent,
    QuizContent,
)
from app.infrastructure.integrations.http_agents_adapter import (
    HTTPAgentsAdapter,
)
from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)

DOCUMENT_ID = "doc_agents_integration"


def _build_document() -> Document:
    """Construye un documento indexado apto para generación."""
    content = (
        b"Documento de prueba para integracion "
        b"BackendAPI y Agentes."
    )

    return Document(
        document_id=DOCUMENT_ID,
        original_filename="arquitectura.txt",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
        status=DocumentStatus.INDEXED,
        oci_object_name=(
            f"documents/{DOCUMENT_ID}/original.txt"
        ),
    )


def _build_agents_response() -> dict[str, object]:
    """Construye una respuesta canónica de generación."""
    return {
        "document_id": DOCUMENT_ID,
        "results": [
            {
                "format": "quiz",
                "status": "success",
                "content": {
                    "title": (
                        "Quiz sobre arquitectura "
                        "de software"
                    ),
                    "instructions": (
                        "Seleccione la respuesta correcta."
                    ),
                    "questions": [
                        {
                            "question_id": "q_1",
                            "question": (
                                "¿Qué componente actúa como "
                                "orquestador del producto?"
                            ),
                            "options": [
                                "BackendAPI",
                                "Frontend",
                                "Vector Store",
                            ],
                            "correct_answer": (
                                "BackendAPI"
                            ),
                            "explanation": (
                                "BackendAPI coordina las "
                                "integraciones y la persistencia "
                                "de negocio."
                            ),
                        }
                    ],
                },
                "sources_used": [
                    {
                        "chunk_id": (
                            f"{DOCUMENT_ID}_chunk_1"
                        ),
                        "document_id": DOCUMENT_ID,
                        "rank": 1,
                        "score": 0.94,
                        "text": (
                            "BackendAPI actúa como "
                            "orquestador del producto."
                        ),
                    }
                ],
                "error_message": None,
            },
            {
                "format": "flashcards",
                "status": "success",
                "content": {
                    "title": (
                        "Flashcards sobre arquitectura"
                    ),
                    "instructions": (
                        "Revise cada concepto y su "
                        "explicación."
                    ),
                    "cards": [
                        {
                            "card_id": "card_1",
                            "front": "BackendAPI",
                            "back": (
                                "Componente responsable de "
                                "orquestar el flujo del producto."
                            ),
                        }
                    ],
                },
                "sources_used": [
                    {
                        "chunk_id": (
                            f"{DOCUMENT_ID}_chunk_1"
                        ),
                        "document_id": DOCUMENT_ID,
                        "rank": 1,
                        "score": 0.94,
                        "text": (
                            "BackendAPI actúa como "
                            "orquestador del producto."
                        ),
                    }
                ],
                "error_message": None,
            },
        ],
    }


def test_generation_through_http_agents_is_persisted_in_sqlite(
    tmp_path: Path,
) -> None:
    """Genera mediante HTTPAgentsAdapter y persiste el resultado real."""

    database = SQLiteDatabase(
        "sqlite:///"
        f"{(tmp_path / 'agents_integration.db').as_posix()}"
    )

    database.initialize()

    document_repository = (
        SQLiteDocumentRepositoryAdapter(
            database
        )
    )

    generated_format_repository = (
        SQLiteGeneratedFormatRepositoryAdapter(
            database
        )
    )

    document_repository.create(
        _build_document()
    )

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
            "document_id": DOCUMENT_ID,
            "formats": [
                "quiz",
                "flashcards",
            ],
            "profile": "beginner",
            "niche": "software",
            "detail_level": "detailed",
            "learning_objective": (
                "Comprender la arquitectura "
                "general del sistema."
            ),
        }

        return httpx.Response(
            status_code=200,
            json=_build_agents_response(),
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://agents.test",
        ) as client:
            agents_adapter = (
                HTTPAgentsAdapter(
                    client=client,
                    generate_path=(
                        "/api/v1/generate"
                    ),
                )
            )

            service = (
                FormatGenerationService(
                    document_repository=(
                        document_repository
                    ),
                    generated_format_repository=(
                        generated_format_repository
                    ),
                    agents=agents_adapter,
                )
            )

            generated_formats = (
                await service.generate_formats(
                    document_id=DOCUMENT_ID,
                    formats=(
                        GeneratedFormatType.QUIZ,
                        GeneratedFormatType.FLASHCARDS,
                    ),
                    profile="beginner",
                    niche="software",
                    detail_level="detailed",
                    learning_objective=(
                        "Comprender la arquitectura "
                        "general del sistema."
                    ),
                )
            )

            assert len(
                generated_formats
            ) == 2

    asyncio.run(
        run_test()
    )

    persisted_formats = (
        generated_format_repository
        .find_by_document_id(
            DOCUMENT_ID
        )
    )

    assert len(
        persisted_formats
    ) == 2

    persisted_by_type = {
        generated_format.format_type: (
            generated_format
        )
        for generated_format
        in persisted_formats
    }

    quiz = persisted_by_type[
        GeneratedFormatType.QUIZ
    ]

    assert (
        quiz.status
        == GeneratedFormatStatus.SUCCESS
    )

    assert isinstance(
        quiz.content,
        QuizContent,
    )

    assert (
        quiz.content.title
        == "Quiz sobre arquitectura de software"
    )

    assert (
        quiz.content.questions[0]
        .correct_answer
        == "BackendAPI"
    )

    assert (
        quiz.chunks_used[0].document_id
        == DOCUMENT_ID
    )

    assert (
        quiz.chunks_used[0].text
        == (
            "BackendAPI actúa como "
            "orquestador del producto."
        )
    )

    assert (
        quiz.generation_context.profile
        == "beginner"
    )

    assert (
        quiz.generation_context.niche
        == "software"
    )

    assert (
        quiz.generation_context.detail_level
        == "detailed"
    )

    assert (
        quiz.generation_context.learning_objective
        == (
            "Comprender la arquitectura "
            "general del sistema."
        )
    )

    flashcards = persisted_by_type[
        GeneratedFormatType.FLASHCARDS
    ]

    assert (
        flashcards.status
        == GeneratedFormatStatus.SUCCESS
    )

    assert isinstance(
        flashcards.content,
        FlashcardsContent,
    )

    assert (
        flashcards.content.cards[0].front
        == "BackendAPI"
    )

    assert (
        flashcards.content.cards[0].back
        == (
            "Componente responsable de "
            "orquestar el flujo del producto."
        )
    )

    assert (
        flashcards.chunks_used[0].chunk_id
        == f"{DOCUMENT_ID}_chunk_1"
    )