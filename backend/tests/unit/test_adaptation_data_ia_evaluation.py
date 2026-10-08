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
    TLDRContent,
    VideoScriptContent,
    VideoScriptScene,
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
            content = self._build_content(
                attempt.format_type
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

    @staticmethod
    def _build_content(
        format_type: GeneratedFormatType,
    ):
        """Construye contenido válido para cada formato."""
        if (
            format_type
            == GeneratedFormatType.QUIZ
        ):
            return QuizContent(
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

        if (
            format_type
            == GeneratedFormatType.FLASHCARDS
        ):
            return FlashcardsContent(
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

        if (
            format_type
            == GeneratedFormatType.TLDR
        ):
            return TLDRContent(
                title="Resumen",
                summary=(
                    "Backend coordina las integraciones."
                ),
                key_points=(
                    "Orquestación",
                    "Persistencia",
                ),
                conclusion=(
                    "Backend centraliza el flujo."
                ),
            )

        return VideoScriptContent(
            title="Guion",
            estimated_duration_minutes=1,
            scenes=(
                VideoScriptScene(
                    scene_id="scene_1",
                    title="Introducción",
                    visual_description=(
                        "Diagrama de arquitectura."
                    ),
                    narration=(
                        "Backend coordina las integraciones."
                    ),
                    duration_seconds=30,
                ),
            ),
        )

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
    """Construye intentos processing de los cuatro formatos."""
    context = GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
    )

    return tuple(
        GeneratedFormat(
            format_id=(
                f"fmt_{format_type.value}"
            ),
            document_id="doc_123",
            format_type=format_type,
            status=(
                GeneratedFormatStatus.PROCESSING
            ),
            generation_context=context,
        )
        for format_type in (
            GeneratedFormatType.QUIZ,
            GeneratedFormatType.FLASHCARDS,
            GeneratedFormatType.TLDR,
            GeneratedFormatType.VIDEO_SCRIPT,
        )
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
    """Data/IA recibe los cuatro formatos cuando terminan en success."""
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
        "fmt_tldr",
        "fmt_video_script",
    ]

    assert (
        package_storage.document_ids
        == [
            "doc_123"
        ]
    )


def test_data_ia_failure_does_not_fail_generated_content() -> None:
    """Un fallo de evaluación no invalida ninguna generación exitosa."""
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
        "fmt_tldr",
        "fmt_video_script",
    ]

    assert (
        package_storage.document_ids
        == [
            "doc_123"
        ]
    )
