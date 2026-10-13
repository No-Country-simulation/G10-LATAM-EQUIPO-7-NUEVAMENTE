"""Pruebas unitarias de FormatEvaluationService."""

import asyncio

import pytest

from app.application.format_evaluation_service import (
    EvaluationResponseMismatchError,
    FormatEvaluationIntegrationError,
    FormatEvaluationService,
    GeneratedFormatNotEvaluationReadyError,
)
from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.format_evaluation import (
    EvaluationScores,
    FormatEvaluation,
)
from app.domain.generated_content import (
    QuizContent,
    QuizQuestion,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.ports.data_ia_port import (
    DataIAError,
    DataIAEvaluationInput,
    DataIAEvaluationResult,
)


class FakeGeneratedFormatRepository:
    """Repositorio mínimo para formatos generados."""

    def __init__(
        self,
        generated_format: (
            GeneratedFormat | None
        ),
    ) -> None:
        self.generated_format = (
            generated_format
        )

    def find_by_id(
        self,
        format_id: str,
    ) -> GeneratedFormat | None:
        if (
            self.generated_format is not None
            and self.generated_format.format_id
            == format_id
        ):
            return self.generated_format

        return None


class CapturingEvaluationRepository:
    """Captura evaluaciones persistidas."""

    def __init__(self) -> None:
        self.evaluations: list[
            FormatEvaluation
        ] = []

    def create(
        self,
        evaluation: FormatEvaluation,
    ) -> FormatEvaluation:
        self.evaluations.append(
            evaluation
        )
        return evaluation


class FakeDataIA:
    """Devuelve una evaluación válida y captura el request."""

    def __init__(
        self,
        *,
        document_id: str = "doc_123",
        format_type: GeneratedFormatType = (
            GeneratedFormatType.QUIZ
        ),
    ) -> None:
        self.document_id = document_id
        self.format_type = format_type
        self.last_request: (
            DataIAEvaluationInput | None
        ) = None

    async def evaluate(
        self,
        request: DataIAEvaluationInput,
    ) -> DataIAEvaluationResult:
        self.last_request = request

        return DataIAEvaluationResult(
            document_id=self.document_id,
            format_type=self.format_type,
            status=(
                FormatEvaluationStatus.APPROVED
            ),
            scores=EvaluationScores(
                relevance=5,
                coherence=4,
                didactic_adaptation=4,
                content_support=5,
            ),
            unsupported_information=False,
            observations=(
                "Contenido aprobado.",
            ),
            evaluator_version="1.0.0",
            rubric_version="1.0.0",
        )


class FailingDataIA:
    """Simula indisponibilidad de Data/IA."""

    async def evaluate(
        self,
        request: DataIAEvaluationInput,
    ) -> DataIAEvaluationResult:
        raise DataIAError(
            "Fallo simulado."
        )


def _build_generated_format(
    *,
    status: GeneratedFormatStatus = (
        GeneratedFormatStatus.SUCCESS
    ),
) -> GeneratedFormat:
    """Construye un Quiz persistido."""
    successful = (
        status
        == GeneratedFormatStatus.SUCCESS
    )

    return GeneratedFormat(
        format_id="fmt_quiz_123",
        document_id="doc_123",
        format_type=GeneratedFormatType.QUIZ,
        status=status,
        generation_context=GenerationContext(
            profile="intermediate",
            niche="backend",
            detail_level="detailed",
            learning_objective=(
                "Comprender arquitectura."
            ),
        ),
        content=(
            QuizContent(
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
            if successful
            else None
        ),
        chunks_used=(
            (
                ChunkEvidence(
                    chunk_id="chunk_1",
                    document_id="doc_123",
                    rank=1,
                    score=0.95,
                    text="Backend coordina.",
                ),
            )
            if successful
            else ()
        ),
        error_message=(
            None
            if successful
            else "Fallo previo."
        ),
    )


def test_evaluate_format_sends_generated_content_and_persists_result() -> None:
    """Evalúa contenido ya generado y persiste el resultado."""
    generated = _build_generated_format()
    generated_repository = (
        FakeGeneratedFormatRepository(
            generated
        )
    )
    evaluation_repository = (
        CapturingEvaluationRepository()
    )
    data_ia = FakeDataIA()

    service = FormatEvaluationService(
        generated_format_repository=(
            generated_repository
        ),
        evaluation_repository=(
            evaluation_repository
        ),
        data_ia=data_ia,
    )

    evaluation = asyncio.run(
        service.evaluate_format(
            generated.format_id
        )
    )

    assert data_ia.last_request is not None
    assert (
        data_ia.last_request.document_id
        == "doc_123"
    )
    assert (
        data_ia.last_request.generated_content
        is generated.content
    )
    assert (
        data_ia.last_request.chunks_used
        == generated.chunks_used
    )

    assert (
        evaluation.format_id
        == generated.format_id
    )
    assert (
        evaluation.status
        == FormatEvaluationStatus.APPROVED
    )
    assert evaluation.evaluator_version == (
        "1.0.0"
    )
    assert (
        evaluation_repository.evaluations
        == [
            evaluation
        ]
    )


def test_evaluate_format_rejects_non_success_generation() -> None:
    """No llama Data/IA si la generación no está lista."""
    generated = _build_generated_format(
        status=GeneratedFormatStatus.FAILED
    )

    service = FormatEvaluationService(
        generated_format_repository=(
            FakeGeneratedFormatRepository(
                generated
            )
        ),
        evaluation_repository=(
            CapturingEvaluationRepository()
        ),
        data_ia=FakeDataIA(),
    )

    with pytest.raises(
        GeneratedFormatNotEvaluationReadyError,
    ):
        asyncio.run(
            service.evaluate_format(
                generated.format_id
            )
        )


def test_evaluate_format_translates_data_ia_failure() -> None:
    """Traduce DataIAError sin modificar la generación."""
    generated = _build_generated_format()

    service = FormatEvaluationService(
        generated_format_repository=(
            FakeGeneratedFormatRepository(
                generated
            )
        ),
        evaluation_repository=(
            CapturingEvaluationRepository()
        ),
        data_ia=FailingDataIA(),
    )

    with pytest.raises(
        FormatEvaluationIntegrationError,
        match="Data/IA no pudo evaluar",
    ):
        asyncio.run(
            service.evaluate_format(
                generated.format_id
            )
        )

    assert (
        generated.status
        == GeneratedFormatStatus.SUCCESS
    )


def test_evaluate_format_rejects_response_for_other_document() -> None:
    """No persiste una evaluación asociada a otro documento."""
    generated = _build_generated_format()
    evaluation_repository = (
        CapturingEvaluationRepository()
    )

    service = FormatEvaluationService(
        generated_format_repository=(
            FakeGeneratedFormatRepository(
                generated
            )
        ),
        evaluation_repository=(
            evaluation_repository
        ),
        data_ia=FakeDataIA(
            document_id="doc_otro"
        ),
    )

    with pytest.raises(
        EvaluationResponseMismatchError,
        match="document_id diferente",
    ):
        asyncio.run(
            service.evaluate_format(
                generated.format_id
            )
        )

    assert (
        evaluation_repository.evaluations
        == []
    )
