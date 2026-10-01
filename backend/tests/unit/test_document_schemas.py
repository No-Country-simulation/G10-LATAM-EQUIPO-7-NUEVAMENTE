"""Pruebas de los contratos HTTP de documentos."""

from datetime import UTC, datetime

from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.schemas.document import (
    DocumentCreatedResponse,
    DocumentResponse,
)
from app.schemas.generated_format import (
    FlashcardItemResponse,
    FlashcardsContentResponse,
    GeneratedFormatResponse,
    QuizContentResponse,
    QuizQuestionResponse,
)


def test_document_created_response() -> None:
    """Expone documento procesado junto con sus formatos generados."""
    response = DocumentCreatedResponse(
        document_id="doc_123",
        filename="manual.pdf",
        status=DocumentStatus.INDEXED,
        duplicate=False,
        formats={
            GeneratedFormatType.QUIZ: (
                GeneratedFormatResponse(
                    format_id="fmt_quiz",
                    status=(
                        GeneratedFormatStatus.SUCCESS
                    ),
                    content=QuizContentResponse(
                        title="Quiz",
                        instructions=(
                            "Seleccione una respuesta."
                        ),
                        questions=[
                            QuizQuestionResponse(
                                question_id="q1",
                                question=(
                                    "¿Cuál es la respuesta?"
                                ),
                                options=[
                                    "Correcta",
                                    "Incorrecta",
                                ],
                                correct_answer="Correcta",
                                explanation=(
                                    "La respuesta está "
                                    "soportada por el documento."
                                ),
                            )
                        ],
                    ),
                )
            ),
            GeneratedFormatType.FLASHCARDS: (
                GeneratedFormatResponse(
                    format_id="fmt_flashcards",
                    status=(
                        GeneratedFormatStatus.SUCCESS
                    ),
                    content=(
                        FlashcardsContentResponse(
                            title="Flashcards",
                            instructions=(
                                "Revise cada tarjeta."
                            ),
                            cards=[
                                FlashcardItemResponse(
                                    card_id="card_1",
                                    front="Concepto",
                                    back="Definición",
                                )
                            ],
                        )
                    ),
                )
            ),
        },
    )

    assert (
        response.document_id
        == "doc_123"
    )
    assert (
        response.status
        == DocumentStatus.INDEXED
    )
    assert response.duplicate is False

    assert set(
        response.formats
    ) == {
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    }

    assert (
        response.formats[
            GeneratedFormatType.QUIZ
        ].status
        == GeneratedFormatStatus.SUCCESS
    )

    assert (
        response.formats[
            GeneratedFormatType.FLASHCARDS
        ].status
        == GeneratedFormatStatus.SUCCESS
    )


def test_document_response() -> None:
    """Expone metadata base y campos enriquecidos opcionales."""
    now = datetime.now(
        UTC
    )

    response = DocumentResponse(
        document_id="doc_123",
        filename="manual.pdf",
        status=DocumentStatus.INDEXED,
        content_type="application/pdf",
        size_bytes=100,
        created_at=now,
        updated_at=now,
    )

    assert response.size_bytes == 100
    assert response.title is None
    assert response.summary is None
    assert response.estimated_time is None