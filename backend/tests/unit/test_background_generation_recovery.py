"""Pruebas del cierre de contingencia para generación en background."""

import asyncio

from app.api.adaptation_execution import (
    execute_background_generation,
)
from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
    GenerationContext,
)


class InMemoryGeneratedFormatRepository:
    """Repositorio mínimo para probar recuperación de intentos."""

    def __init__(
        self,
        formats: tuple[
            GeneratedFormat,
            ...,
        ],
    ) -> None:
        self.formats = {
            generated_format.format_id: generated_format
            for generated_format in formats
        }

    def find_by_id(
        self,
        format_id: str,
    ) -> GeneratedFormat | None:
        return self.formats.get(
            format_id
        )

    def update(
        self,
        generated_format: GeneratedFormat,
    ) -> GeneratedFormat:
        self.formats[
            generated_format.format_id
        ] = generated_format
        return generated_format


class UnexpectedFailureOrchestrationService:
    """Simula una excepción inesperada durante el trabajo de background."""

    def __init__(
        self,
        generation_service: FormatGenerationService,
    ) -> None:
        self._generation_service = generation_service
        self.failure_requests: list[
            tuple[str, ...]
        ] = []

    async def complete_default_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
    ) -> list[GeneratedFormat]:
        raise RuntimeError(
            "Fallo inesperado simulado."
        )

    def fail_default_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
        error_message: str,
    ) -> list[GeneratedFormat]:
        self.failure_requests.append(
            tuple(
                attempt.format_id
                for attempt in attempts
            )
        )

        return (
            self._generation_service
            .fail_processing_attempts(
                attempts=attempts,
                error_message=error_message,
            )
        )


def build_processing_attempt(
    *,
    format_id: str,
    format_type: GeneratedFormatType,
) -> GeneratedFormat:
    """Construye un intento processing válido."""
    return GeneratedFormat(
        format_id=format_id,
        document_id="doc_123",
        format_type=format_type,
        status=GeneratedFormatStatus.PROCESSING,
        generation_context=GenerationContext(
            profile="beginner",
            niche="general",
            detail_level="standard",
        ),
    )


def build_generation_service(
    repository: InMemoryGeneratedFormatRepository,
) -> FormatGenerationService:
    """Construye el servicio usando solo la dependencia ejercitada."""
    return FormatGenerationService(
        document_repository=object(),
        generated_format_repository=repository,
        agents=object(),
    )


def test_fail_processing_attempts_preserves_terminal_attempts() -> None:
    """La compensación no sobrescribe un formato ya terminal."""
    quiz_attempt = build_processing_attempt(
        format_id="fmt_quiz",
        format_type=GeneratedFormatType.QUIZ,
    )
    flashcards_attempt = build_processing_attempt(
        format_id="fmt_flashcards",
        format_type=(
            GeneratedFormatType.FLASHCARDS
        ),
    )

    terminal_quiz = GeneratedFormat(
        format_id=quiz_attempt.format_id,
        document_id=quiz_attempt.document_id,
        format_type=quiz_attempt.format_type,
        status=GeneratedFormatStatus.FAILED,
        generation_context=(
            quiz_attempt.generation_context
        ),
        error_message="Fallo previo conservado.",
        created_at=quiz_attempt.created_at,
        updated_at=quiz_attempt.updated_at,
    )

    repository = (
        InMemoryGeneratedFormatRepository(
            (
                terminal_quiz,
                flashcards_attempt,
            )
        )
    )

    service = build_generation_service(
        repository
    )

    failed = service.fail_processing_attempts(
        attempts=(
            quiz_attempt,
            flashcards_attempt,
        ),
        error_message="Fallo inesperado de background.",
    )

    assert [
        attempt.format_id
        for attempt in failed
    ] == [
        "fmt_flashcards"
    ]

    stored_quiz = repository.find_by_id(
        "fmt_quiz"
    )
    stored_flashcards = repository.find_by_id(
        "fmt_flashcards"
    )

    assert stored_quiz is not None
    assert stored_flashcards is not None

    assert (
        stored_quiz.status
        == GeneratedFormatStatus.FAILED
    )
    assert (
        stored_quiz.error_message
        == "Fallo previo conservado."
    )

    assert (
        stored_flashcards.status
        == GeneratedFormatStatus.FAILED
    )
    assert (
        stored_flashcards.error_message
        == "Fallo inesperado de background."
    )


def test_unexpected_background_error_marks_processing_attempts_failed() -> None:
    """Un error inesperado no deja intentos activos en processing."""
    attempts = (
        build_processing_attempt(
            format_id="fmt_quiz",
            format_type=GeneratedFormatType.QUIZ,
        ),
        build_processing_attempt(
            format_id="fmt_flashcards",
            format_type=(
                GeneratedFormatType.FLASHCARDS
            ),
        ),
    )

    repository = (
        InMemoryGeneratedFormatRepository(
            attempts
        )
    )
    generation_service = (
        build_generation_service(
            repository
        )
    )
    orchestration_service = (
        UnexpectedFailureOrchestrationService(
            generation_service
        )
    )

    asyncio.run(
        execute_background_generation(
            orchestration_service=(
                orchestration_service
            ),
            attempts=attempts,
        )
    )

    assert (
        orchestration_service.failure_requests
        == [
            (
                "fmt_quiz",
                "fmt_flashcards",
            )
        ]
    )

    stored_formats = [
        repository.find_by_id(
            attempt.format_id
        )
        for attempt in attempts
    ]

    assert all(
        stored_format is not None
        for stored_format in stored_formats
    )
    assert all(
        stored_format.status
        == GeneratedFormatStatus.FAILED
        for stored_format in stored_formats
        if stored_format is not None
    )
