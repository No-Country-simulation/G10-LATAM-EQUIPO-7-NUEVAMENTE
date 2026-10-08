"""Pruebas de la evaluación Data/IA dentro de la orquestación."""

import asyncio

from app.application.adaptation_orchestration_service import (
    AdaptationOrchestrationService,
)
from app.application.format_evaluation_service import (
    FormatEvaluationIntegrationError,
)
from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    FlashcardItem,
    FlashcardsContent,
    QuizContent,
    QuizQuestion,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)


class SuccessfulGenerationService:
    """Convierte los intentos recibidos en generaciones exitosas."""

    async def complete_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
    ) -> list[GeneratedFormat]:
        context = (
            attempts[0].generation_context
        )

        completed: list[
            GeneratedFormat
        ] = []

        for attempt in attempts:
            if (
                attempt.format_type
                == GeneratedFormatType.QUIZ
            ):
                content = QuizContent(
                    title="Quiz",
                    instructions="Seleccione.",
                    questions=(
                        QuizQuestion(
                            question_id="q1",
                            question="¿Qué orquesta?",
                            options=(
                                "Backend",
                                "Frontend",
                            ),
                            correct_answer="Backend",
                            explanation=(
                                "Backend coordina."
                            ),
                        ),
                    ),
                )
            else:
                content = FlashcardsContent(
                    title="Tarjetas",
                    instructions="Revise.",
                    cards=(
                        FlashcardItem(
                            card_id="c1",
                            front="Backend",
                            back="Orquestador.",
                        ),
                    ),
                )

            completed.append(
                GeneratedFormat(
                    format_id=attempt.format_id,
                    document_id=(
                        attempt.document_id
                    ),
                    format_type=(
                        attempt.format_type
                    ),
                    status=(
                        GeneratedFormatStatus.SUCCESS
                    ),
                    generation_context=context,
                    content=content,
                    chunks_used=(
                        ChunkEvidence(
                            chunk_id=(
                                f"chunk_"
                                f"{attempt.format_type.value}"
                            ),
                            document_id=(
                                attempt.document_id
                            ),
                            rank=1,
                            score=0.95,
                            text="Evidencia.",
                        ),
                    ),
                    created_at=(
                        attempt.created_at
                    ),
                    updated_at=(
                        attempt.updated_at
                    ),
                )
            )

        return completed

    def fail_processing_attempts(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
        error_message: str,
    ) -> list[GeneratedFormat]:
        return []


class SpyEvaluationService:
    """Registra los format_id evaluados."""

    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail
        self.format_ids: list[str] = []

    async def evaluate_format(
        self,
        format_id: str,
    ):
        self.format_ids.append(
            format_id
        )

        if self.fail:
            raise (
                FormatEvaluationIntegrationError(
                    "Fallo simulado de Data/IA."
                )
            )

        return object()


class SpyPackageStorage:
    """Registra la actualización del snapshot OCI."""

    def __init__(self) -> None:
        self.document_ids: list[str] = []

    def persist_current_package(
        self,
        document_id: str,
    ) -> str:
        self.document_ids.append(
            document_id
        )
        return (
            f"documents/{document_id}/"
            "generated/content.json"
        )


class UnusedService:
    """Colaborador no utilizado por estas pruebas."""


def _build_attempts() -> tuple[
    GeneratedFormat,
    ...,
]:
    """Construye intentos processing de Quiz y Flashcards."""
    context = GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
    )

    return (
        GeneratedFormat(
            format_id="fmt_quiz",
            document_id="doc_123",
            format_type=GeneratedFormatType.QUIZ,
            status=(
                GeneratedFormatStatus.PROCESSING
            ),
            generation_context=context,
        ),
        GeneratedFormat(
            format_id="fmt_flashcards",
            document_id="doc_123",
            format_type=(
                GeneratedFormatType.FLASHCARDS
            ),
            status=(
                GeneratedFormatStatus.PROCESSING
            ),
            generation_context=context,
        ),
    )


def _build_service(
    *,
    evaluation_service: SpyEvaluationService,
    package_storage: SpyPackageStorage,
) -> AdaptationOrchestrationService:
    """Construye el orquestador para probar efectos post-generación."""
    return AdaptationOrchestrationService(
        document_service=UnusedService(),
        rag_integration_service=UnusedService(),
        format_generation_service=(
            SuccessfulGenerationService()
        ),
        generated_package_storage_service=(
            package_storage
        ),
        format_evaluation_service=(
            evaluation_service
        ),
    )


def test_successful_formats_are_evaluated_after_generation() -> None:
    """Data/IA recibe únicamente formatos ya generados exitosamente."""
    evaluation_service = (
        SpyEvaluationService()
    )
    package_storage = (
        SpyPackageStorage()
    )

    service = _build_service(
        evaluation_service=(
            evaluation_service
        ),
        package_storage=(
            package_storage
        ),
    )

    completed = asyncio.run(
        service.complete_default_generation(
            attempts=_build_attempts()
        )
    )

    assert all(
        item.status
        == GeneratedFormatStatus.SUCCESS
        for item in completed
    )

    assert evaluation_service.format_ids == [
        "fmt_quiz",
        "fmt_flashcards",
    ]

    assert (
        package_storage.document_ids
        == [
            "doc_123"
        ]
    )


def test_data_ia_failure_does_not_fail_generated_content() -> None:
    """Un fallo de evaluación no invalida una generación exitosa."""
    evaluation_service = (
        SpyEvaluationService(
            fail=True
        )
    )
    package_storage = (
        SpyPackageStorage()
    )

    service = _build_service(
        evaluation_service=(
            evaluation_service
        ),
        package_storage=(
            package_storage
        ),
    )

    completed = asyncio.run(
        service.complete_default_generation(
            attempts=_build_attempts()
        )
    )

    assert all(
        item.status
        == GeneratedFormatStatus.SUCCESS
        for item in completed
    )

    assert evaluation_service.format_ids == [
        "fmt_quiz",
        "fmt_flashcards",
    ]

    assert (
        package_storage.document_ids
        == [
            "doc_123"
        ]
    )
