"""Pruebas del contrato canónico del paquete educativo OCI."""

from datetime import UTC, datetime

import pytest

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    QuizContent,
    QuizQuestion,
)
from app.domain.generated_educational_package import (
    GeneratedEducationalPackage,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.domain.learning_metadata import (
    LearningMetadata,
)


def build_context() -> GenerationContext:
    """Construye contexto válido para formatos de prueba."""
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
    )


def build_quiz() -> GeneratedFormat:
    """Construye un Quiz exitoso serializable."""
    timestamp = datetime.now(
        UTC
    )

    return GeneratedFormat(
        format_id="fmt_quiz_1",
        document_id="doc_123",
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=build_context(),
        content=QuizContent(
            title="Quiz",
            instructions="Seleccione una respuesta.",
            questions=(
                QuizQuestion(
                    question_id="q1",
                    question="¿Qué es BackendAPI?",
                    options=(
                        "Orquestador",
                        "Vector Store",
                    ),
                    correct_answer="Orquestador",
                    explanation=(
                        "BackendAPI coordina el flujo."
                    ),
                ),
            ),
        ),
        chunks_used=(
            ChunkEvidence(
                chunk_id="chunk_1",
                document_id="doc_123",
                rank=1,
                score=0.95,
                text="BackendAPI coordina el flujo.",
            ),
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_failed_flashcards() -> GeneratedFormat:
    """Construye Flashcards fallidas sin contenido."""
    timestamp = datetime.now(
        UTC
    )

    return GeneratedFormat(
        format_id="fmt_flashcards_1",
        document_id="doc_123",
        format_type=(
            GeneratedFormatType.FLASHCARDS
        ),
        status=GeneratedFormatStatus.FAILED,
        generation_context=build_context(),
        error_message="Fallo de generación.",
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_package_serializes_canonical_oci_contract() -> None:
    """Expone metadata y formatos sin evidencia ni contexto técnico."""
    package = GeneratedEducationalPackage(
        document_id="doc_123",
        learning_metadata=LearningMetadata(
            key_concepts=(
                "RAG",
                "BackendAPI",
            ),
            prerequisites=(
                "Python",
            ),
            estimated_time_minutes=18,
        ),
        formats=(
            build_quiz(),
            build_failed_flashcards(),
        ),
    )

    data = package.to_dict()

    assert data["document_id"] == "doc_123"

    assert data["learning_metadata"] == {
        "key_concepts": [
            "RAG",
            "BackendAPI",
        ],
        "prerequisites": [
            "Python",
        ],
        "estimated_time_minutes": 18,
    }

    formats = data["formats"]

    assert set(
        formats
    ) == {
        "quiz",
        "flashcards",
    }

    assert (
        formats["quiz"]["format_id"]
        == "fmt_quiz_1"
    )
    assert (
        formats["quiz"]["status"]
        == "success"
    )
    assert (
        formats["quiz"]["content"]["title"]
        == "Quiz"
    )
    assert (
        formats["quiz"]["error_message"]
        is None
    )

    assert (
        formats["flashcards"]["status"]
        == "failed"
    )
    assert (
        formats["flashcards"]["content"]
        is None
    )
    assert (
        formats["flashcards"]["error_message"]
        == "Fallo de generación."
    )

    assert (
        "chunks_used"
        not in formats["quiz"]
    )
    assert (
        "generation_context"
        not in formats["quiz"]
    )


def test_package_rejects_processing_format() -> None:
    """Un snapshot persistible nunca incluye trabajo todavía activo."""
    processing = GeneratedFormat(
        format_id="fmt_processing",
        document_id="doc_123",
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.PROCESSING,
        generation_context=build_context(),
    )

    with pytest.raises(
        ValueError,
        match="processing",
    ):
        GeneratedEducationalPackage(
            document_id="doc_123",
            learning_metadata=(
                LearningMetadata.empty()
            ),
            formats=(
                processing,
            ),
        )
