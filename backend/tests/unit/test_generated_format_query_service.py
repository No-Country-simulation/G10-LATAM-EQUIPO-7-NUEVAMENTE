"""Pruebas del caso de uso de consulta de formatos generados."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.application.generated_format_query_service import (
    GeneratedFormatQueryDocumentNotFoundError,
    GeneratedFormatQueryService,
)
from app.domain.document import Document
from app.domain.enums import (
    DocumentFormatsStatus,
    DocumentStatus,
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
from tests.fakes import FakeDocumentRepository

DOCUMENT_ID = "doc_123"


class FakeGeneratedFormatRepository:
    """Repositorio en memoria para consultas de formatos."""

    def __init__(self) -> None:
        self.generated_formats: list[
            GeneratedFormat
        ] = []

    def create(
        self,
        generated_format: GeneratedFormat,
    ) -> GeneratedFormat:
        """Persiste una generación en memoria."""
        self.generated_formats.append(
            generated_format
        )

        return generated_format

    def find_by_id(
        self,
        format_id: str,
    ) -> GeneratedFormat | None:
        """Busca una generación por identificador."""
        return next(
            (
                generated_format
                for generated_format
                in self.generated_formats
                if (
                    generated_format.format_id
                    == format_id
                )
            ),
            None,
        )

    def find_by_document_id(
        self,
        document_id: str,
    ) -> list[GeneratedFormat]:
        """Obtiene generaciones de un documento."""
        return [
            generated_format
            for generated_format
            in self.generated_formats
            if (
                generated_format.document_id
                == document_id
            )
        ]


def build_document(
    *,
    status: DocumentStatus = DocumentStatus.INDEXED,
) -> Document:
    """Construye un documento válido para las pruebas."""
    content = b"Documento de prueba"

    return Document(
        document_id=DOCUMENT_ID,
        original_filename="manual.pdf",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
        status=status,
    )


def build_context() -> GenerationContext:
    """Construye el contexto pedagógico de prueba."""
    return GenerationContext(
        profile="beginner",
        niche="technology",
        detail_level="detailed",
    )


def build_evidence() -> tuple[
    ChunkEvidence,
    ...
]:
    """Construye evidencia válida para generaciones exitosas."""
    return (
        ChunkEvidence(
            chunk_id=f"{DOCUMENT_ID}_1_0",
            document_id=DOCUMENT_ID,
            rank=1,
            score=0.95,
            text="Contenido utilizado como evidencia.",
        ),
    )


def build_quiz(
    *,
    format_id: str = "fmt_quiz_1",
    status: GeneratedFormatStatus = (
        GeneratedFormatStatus.SUCCESS
    ),
    created_at: datetime | None = None,
) -> GeneratedFormat:
    """Construye un resultado Quiz."""
    timestamp = (
        created_at
        or datetime.now(UTC)
    )

    successful = (
        status
        == GeneratedFormatStatus.SUCCESS
    )

    return GeneratedFormat(
        format_id=format_id,
        document_id=DOCUMENT_ID,
        format_type=GeneratedFormatType.QUIZ,
        status=status,
        generation_context=build_context(),
        content=(
            QuizContent(
                title="Quiz de prueba",
                instructions=(
                    "Seleccione la respuesta correcta."
                ),
                questions=(
                    QuizQuestion(
                        question_id="q1",
                        question="¿Qué es BackendAPI?",
                        options=(
                            "El orquestador del producto",
                            "El Vector Store",
                        ),
                        correct_answer=(
                            "El orquestador del producto"
                        ),
                        explanation=(
                            "BackendAPI coordina las "
                            "integraciones del producto."
                        ),
                    ),
                ),
            )
            if successful
            else None
        ),
        chunks_used=(
            build_evidence()
            if successful
            else ()
        ),
        error_message=(
            None
            if successful
            else "No fue posible generar el Quiz."
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_flashcards(
    *,
    format_id: str = "fmt_flashcards_1",
    status: GeneratedFormatStatus = (
        GeneratedFormatStatus.SUCCESS
    ),
    created_at: datetime | None = None,
) -> GeneratedFormat:
    """Construye un resultado Flashcards."""
    timestamp = (
        created_at
        or datetime.now(UTC)
    )

    successful = (
        status
        == GeneratedFormatStatus.SUCCESS
    )

    return GeneratedFormat(
        format_id=format_id,
        document_id=DOCUMENT_ID,
        format_type=(
            GeneratedFormatType.FLASHCARDS
        ),
        status=status,
        generation_context=build_context(),
        content=(
            FlashcardsContent(
                title="Flashcards de prueba",
                instructions="Revise las tarjetas.",
                cards=(
                    FlashcardItem(
                        card_id="card_1",
                        front="BackendAPI",
                        back=(
                            "Orquestador del producto."
                        ),
                    ),
                ),
            )
            if successful
            else None
        ),
        chunks_used=(
            build_evidence()
            if successful
            else ()
        ),
        error_message=(
            None
            if successful
            else "No fue posible generar Flashcards."
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_service(
    *,
    document: Document | None = None,
    generated_formats: tuple[
        GeneratedFormat,
        ...
    ] = (),
) -> GeneratedFormatQueryService:
    """Construye el servicio con repositorios en memoria."""
    document_repository = (
        FakeDocumentRepository()
    )

    if document is not None:
        document_repository.create(
            document
        )

    generated_format_repository = (
        FakeGeneratedFormatRepository()
    )

    for generated_format in generated_formats:
        generated_format_repository.create(
            generated_format
        )

    return GeneratedFormatQueryService(
        document_repository=(
            document_repository
        ),
        generated_format_repository=(
            generated_format_repository
        ),
    )


def test_query_rejects_unknown_document() -> None:
    """Reporta explícitamente un documento inexistente."""
    service = build_service()

    with pytest.raises(
        GeneratedFormatQueryDocumentNotFoundError,
        match="No existe el documento",
    ):
        service.get_document_formats(
            DOCUMENT_ID
        )


def test_query_returns_processing_without_formats() -> None:
    """Un documento sin resultados expone processing."""
    service = build_service(
        document=build_document()
    )

    result = service.get_document_formats(
        DOCUMENT_ID
    )

    assert (
        result.status
        == DocumentFormatsStatus.PROCESSING
    )
    assert result.formats == ()


def test_query_returns_error_for_failed_document_without_formats() -> None:
    """Un documento fallido sin formatos expone error."""
    service = build_service(
        document=build_document(
            status=(
                DocumentStatus.INDEXING_FAILED
            )
        )
    )

    result = service.get_document_formats(
        DOCUMENT_ID
    )

    assert (
        result.status
        == DocumentFormatsStatus.ERROR
    )
    assert result.formats == ()


def test_query_returns_ready_when_both_formats_succeed() -> None:
    """Quiz y Flashcards exitosos producen estado ready."""
    service = build_service(
        document=build_document(),
        generated_formats=(
            build_quiz(),
            build_flashcards(),
        ),
    )

    result = service.get_document_formats(
        DOCUMENT_ID
    )

    assert (
        result.status
        == DocumentFormatsStatus.READY
    )

    assert {
        generated_format.format_type
        for generated_format
        in result.formats
    } == {
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    }


def test_query_returns_partial_when_only_one_format_succeeds() -> None:
    """Un formato exitoso y otro fallido producen partial."""
    service = build_service(
        document=build_document(),
        generated_formats=(
            build_quiz(),
            build_flashcards(
                status=(
                    GeneratedFormatStatus.FAILED
                )
            ),
        ),
    )

    result = service.get_document_formats(
        DOCUMENT_ID
    )

    assert (
        result.status
        == DocumentFormatsStatus.PARTIAL
    )


def test_query_returns_error_when_no_format_succeeds() -> None:
    """Resultados sin éxitos producen estado global error."""
    service = build_service(
        document=build_document(),
        generated_formats=(
            build_quiz(
                status=(
                    GeneratedFormatStatus.FAILED
                )
            ),
            build_flashcards(
                status=(
                    GeneratedFormatStatus.NO_RESULTS
                )
            ),
        ),
    )

    result = service.get_document_formats(
        DOCUMENT_ID
    )

    assert (
        result.status
        == DocumentFormatsStatus.ERROR
    )


def test_query_preserves_latest_success_after_newer_failure() -> None:
    """Un reintento fallido no oculta una generación exitosa previa."""
    first_timestamp = datetime(
        2026,
        9,
        30,
        12,
        0,
        tzinfo=UTC,
    )

    successful_quiz = build_quiz(
        format_id="fmt_quiz_success",
        created_at=first_timestamp,
    )

    failed_retry = build_quiz(
        format_id="fmt_quiz_failed_retry",
        status=GeneratedFormatStatus.FAILED,
        created_at=(
            first_timestamp
            + timedelta(minutes=10)
        ),
    )

    service = build_service(
        document=build_document(),
        generated_formats=(
            successful_quiz,
            failed_retry,
            build_flashcards(),
        ),
    )

    result = service.get_document_formats(
        DOCUMENT_ID
    )

    selected_quiz = next(
        generated_format
        for generated_format
        in result.formats
        if (
            generated_format.format_type
            == GeneratedFormatType.QUIZ
        )
    )

    assert (
        selected_quiz.format_id
        == "fmt_quiz_success"
    )

    assert (
        result.status
        == DocumentFormatsStatus.READY
    )


def test_query_selects_latest_successful_generation() -> None:
    """Entre varios éxitos se expone el más reciente."""
    first_timestamp = datetime(
        2026,
        9,
        30,
        12,
        0,
        tzinfo=UTC,
    )

    first_quiz = build_quiz(
        format_id="fmt_quiz_old",
        created_at=first_timestamp,
    )

    latest_quiz = build_quiz(
        format_id="fmt_quiz_new",
        created_at=(
            first_timestamp
            + timedelta(minutes=5)
        ),
    )

    service = build_service(
        document=build_document(),
        generated_formats=(
            first_quiz,
            latest_quiz,
        ),
    )

    result = service.get_document_formats(
        DOCUMENT_ID
    )

    assert len(
        result.formats
    ) == 1

    assert (
        result.formats[0].format_id
        == "fmt_quiz_new"
    )

    assert (
        result.status
        == DocumentFormatsStatus.PARTIAL
    )