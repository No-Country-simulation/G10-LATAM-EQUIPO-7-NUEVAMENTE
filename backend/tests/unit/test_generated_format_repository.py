"""Pruebas del repositorio SQLite de formatos generados."""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.domain.document import Document
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
from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatAlreadyExistsError,
    GeneratedFormatDocumentNotFoundError,
)

DOCUMENT_ID = "doc_123"


def build_repositories(
    tmp_path: Path,
) -> tuple[
    SQLiteDocumentRepositoryAdapter,
    SQLiteGeneratedFormatRepositoryAdapter,
]:
    """Crea repositorios SQLite sobre una BD aislada."""
    database = SQLiteDatabase(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    database.initialize()

    return (
        SQLiteDocumentRepositoryAdapter(
            database
        ),
        SQLiteGeneratedFormatRepositoryAdapter(
            database
        ),
    )


def build_document(
    document_id: str = DOCUMENT_ID,
) -> Document:
    """Construye un documento válido para satisfacer la FK."""
    content = (
        f"Documento {document_id}"
        .encode()
    )

    return Document(
        document_id=document_id,
        original_filename="manual.pdf",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
    )


def build_context() -> GenerationContext:
    """Construye un contexto pedagógico completo."""
    return GenerationContext(
        profile="beginner",
        niche="technology",
        detail_level="detailed",
        learning_objective=(
            "Comprender los conceptos principales."
        ),
    )


def build_evidence(
    document_id: str = DOCUMENT_ID,
) -> tuple[ChunkEvidence, ...]:
    """Construye evidencia completa utilizada por la generación."""
    return (
        ChunkEvidence(
            chunk_id=f"{document_id}_1_0",
            document_id=document_id,
            rank=1,
            score=0.94,
            text=(
                "Los microservicios son componentes "
                "desplegables de forma independiente."
            ),
        ),
        ChunkEvidence(
            chunk_id=f"{document_id}_1_1",
            document_id=document_id,
            rank=2,
            score=0.88,
            text=(
                "Cada servicio puede evolucionar "
                "de manera independiente."
            ),
        ),
    )


def build_quiz(
    *,
    format_id: str = "fmt_quiz_1",
    document_id: str = DOCUMENT_ID,
    created_at: datetime | None = None,
) -> GeneratedFormat:
    """Construye una generación Quiz exitosa."""
    timestamp = (
        created_at
        or datetime.now(UTC)
    )

    return GeneratedFormat(
        format_id=format_id,
        document_id=document_id,
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=build_context(),
        content=QuizContent(
            title="Quiz de microservicios",
            instructions=(
                "Seleccione la respuesta correcta."
            ),
            questions=(
                QuizQuestion(
                    question_id="q1",
                    question=(
                        "¿Qué caracteriza a un microservicio?"
                    ),
                    options=(
                        "Despliegue independiente",
                        "Base de datos compartida obligatoria",
                    ),
                    correct_answer=(
                        "Despliegue independiente"
                    ),
                    explanation=(
                        "Puede desplegarse y evolucionar "
                        "de forma independiente."
                    ),
                ),
            ),
        ),
        chunks_used=build_evidence(
            document_id
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_flashcards(
    *,
    format_id: str = "fmt_flashcards_1",
    document_id: str = DOCUMENT_ID,
) -> GeneratedFormat:
    """Construye una generación Flashcards exitosa."""
    return GeneratedFormat(
        format_id=format_id,
        document_id=document_id,
        format_type=(
            GeneratedFormatType.FLASHCARDS
        ),
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=build_context(),
        content=FlashcardsContent(
            title="Flashcards de microservicios",
            instructions="Revise cada tarjeta.",
            cards=(
                FlashcardItem(
                    card_id="card_1",
                    front="Microservicio",
                    back=(
                        "Servicio pequeño y desplegable "
                        "de forma independiente."
                    ),
                ),
            ),
        ),
        chunks_used=build_evidence(
            document_id
        ),
    )


def build_failed_format(
    *,
    format_id: str = "fmt_failed_1",
    document_id: str = DOCUMENT_ID,
) -> GeneratedFormat:
    """Construye una generación fallida persistible."""
    return GeneratedFormat(
        format_id=format_id,
        document_id=document_id,
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.FAILED,
        generation_context=build_context(),
        content=None,
        chunks_used=(),
        error_message=(
            "Agentes no pudo generar el Quiz."
        ),
    )


def test_repository_persists_and_restores_quiz(
    tmp_path: Path,
) -> None:
    """Comprueba round-trip completo de un Quiz."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    quiz = build_quiz()

    repository.create(
        quiz
    )

    stored = repository.find_by_id(
        quiz.format_id
    )

    assert stored is not None
    assert stored.format_id == quiz.format_id
    assert stored.document_id == DOCUMENT_ID
    assert (
        stored.format_type
        == GeneratedFormatType.QUIZ
    )
    assert (
        stored.status
        == GeneratedFormatStatus.SUCCESS
    )

    assert isinstance(
        stored.content,
        QuizContent,
    )

    assert (
        stored.content.title
        == "Quiz de microservicios"
    )

    assert (
        stored.content.questions[0]
        .correct_answer
        == "Despliegue independiente"
    )

    assert len(
        stored.chunks_used
    ) == 2

    assert (
        stored.chunks_used[0].chunk_id
        == f"{DOCUMENT_ID}_1_0"
    )

    assert (
        stored.chunks_used[0].text
        == (
            "Los microservicios son componentes "
            "desplegables de forma independiente."
        )
    )

    assert (
        stored.generation_context.profile
        == "beginner"
    )
    assert (
        stored.generation_context.niche
        == "technology"
    )
    assert (
        stored.generation_context.detail_level
        == "detailed"
    )
    assert (
        stored.generation_context.learning_objective
        == "Comprender los conceptos principales."
    )

def build_processing_format(
    *,
    format_id: str = "fmt_processing_1",
    document_id: str = DOCUMENT_ID,
    created_at: datetime | None = None,
) -> GeneratedFormat:
    """Construye un intento de generación en procesamiento."""
    timestamp = (
        created_at
        or datetime.now(UTC)
    )

    return GeneratedFormat(
        format_id=format_id,
        document_id=document_id,
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.PROCESSING,
        generation_context=build_context(),
        content=None,
        chunks_used=(),
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
    )

def test_repository_finds_quiz_and_flashcards_by_document(
    tmp_path: Path,
) -> None:
    """Recupera todos los formatos asociados a un documento."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    quiz = build_quiz()
    flashcards = build_flashcards()

    repository.create(
        quiz
    )
    repository.create(
        flashcards
    )

    stored_formats = (
        repository.find_by_document_id(
            DOCUMENT_ID
        )
    )

    assert len(
        stored_formats
    ) == 2

    assert {
        generated_format.format_type
        for generated_format
        in stored_formats
    } == {
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    }

    stored_flashcards = next(
        generated_format
        for generated_format
        in stored_formats
        if (
            generated_format.format_type
            == GeneratedFormatType.FLASHCARDS
        )
    )

    assert isinstance(
        stored_flashcards.content,
        FlashcardsContent,
    )

    assert (
        stored_flashcards
        .content
        .cards[0]
        .front
        == "Microservicio"
    )


def test_repository_preserves_multiple_generations(
    tmp_path: Path,
) -> None:
    """Conserva historial 1:N incluso para el mismo tipo de formato."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    first_created_at = datetime(
        2026,
        9,
        30,
        12,
        0,
        tzinfo=UTC,
    )

    first_quiz = build_quiz(
        format_id="fmt_quiz_1",
        created_at=first_created_at,
    )

    second_quiz = build_quiz(
        format_id="fmt_quiz_2",
        created_at=(
            first_created_at
            + timedelta(minutes=5)
        ),
    )

    repository.create(
        first_quiz
    )
    repository.create(
        second_quiz
    )

    stored_formats = (
        repository.find_by_document_id(
            DOCUMENT_ID
        )
    )

    assert len(
        stored_formats
    ) == 2

    assert [
        generated_format.format_id
        for generated_format
        in stored_formats
    ] == [
        "fmt_quiz_1",
        "fmt_quiz_2",
    ]

    assert all(
        generated_format.format_type
        == GeneratedFormatType.QUIZ
        for generated_format
        in stored_formats
    )


def test_repository_persists_failed_generation(
    tmp_path: Path,
) -> None:
    """Conserva una generación fallida para soporte de flujo parcial."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    failed_format = build_failed_format()

    repository.create(
        failed_format
    )

    stored = repository.find_by_id(
        failed_format.format_id
    )

    assert stored is not None

    assert (
        stored.status
        == GeneratedFormatStatus.FAILED
    )
    assert stored.content is None
    assert stored.chunks_used == ()
    assert (
        stored.error_message
        == "Agentes no pudo generar el Quiz."
    )


def test_repository_returns_empty_list_for_document_without_formats(
    tmp_path: Path,
) -> None:
    """Una consulta sin generaciones retorna una colección vacía."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    stored_formats = (
        repository.find_by_document_id(
            DOCUMENT_ID
        )
    )

    assert stored_formats == []


def test_repository_rejects_duplicate_format_id(
    tmp_path: Path,
) -> None:
    """Reporta explícitamente un format_id previamente persistido."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    quiz = build_quiz()

    repository.create(
        quiz
    )

    with pytest.raises(
        GeneratedFormatAlreadyExistsError,
        match="Ya existe el formato generado",
    ):
        repository.create(
            quiz
        )


def test_repository_rejects_unknown_document(
    tmp_path: Path,
) -> None:
    """Reporta explícitamente una referencia a document_id inexistente."""
    _, repository = (
        build_repositories(
            tmp_path
        )
    )

    quiz = build_quiz(
        document_id="doc_inexistente"
    )

    with pytest.raises(
        GeneratedFormatDocumentNotFoundError,
        match="no existe",
    ):
        repository.create(
            quiz
        )

def test_repository_persists_processing_generation(
    tmp_path: Path,
) -> None:
    """Persiste y reconstruye un intento processing."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    processing = build_processing_format()

    repository.create(
        processing
    )

    stored = repository.find_by_id(
        processing.format_id
    )

    assert stored is not None

    assert (
        stored.format_id
        == processing.format_id
    )
    assert (
        stored.status
        == GeneratedFormatStatus.PROCESSING
    )
    assert stored.content is None
    assert stored.chunks_used == ()
    assert stored.error_message is None


def test_repository_updates_processing_generation_to_success(
    tmp_path: Path,
) -> None:
    """Actualiza el mismo intento sin crear una segunda generación."""
    document_repository, repository = (
        build_repositories(
            tmp_path
        )
    )

    document_repository.create(
        build_document()
    )

    processing = build_processing_format(
        format_id="fmt_quiz_processing"
    )

    repository.create(
        processing
    )

    successful_quiz = build_quiz(
        format_id=processing.format_id,
        created_at=processing.created_at,
    )

    completed = GeneratedFormat(
        format_id=processing.format_id,
        document_id=processing.document_id,
        format_type=processing.format_type,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=(
            processing.generation_context
        ),
        content=successful_quiz.content,
        chunks_used=successful_quiz.chunks_used,
        error_message=None,
        created_at=processing.created_at,
        updated_at=(
            processing.updated_at
            + timedelta(seconds=1)
        ),
    )

    repository.update(
        completed
    )

    stored = repository.find_by_id(
        processing.format_id
    )

    assert stored is not None

    assert (
        stored.format_id
        == processing.format_id
    )
    assert (
        stored.status
        == GeneratedFormatStatus.SUCCESS
    )
    assert isinstance(
        stored.content,
        QuizContent,
    )

    history = (
        repository.find_by_document_id(
            DOCUMENT_ID
        )
    )

    assert len(history) == 1
    assert (
        history[0].format_id
        == processing.format_id
    )
