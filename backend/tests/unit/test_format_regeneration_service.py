"""Pruebas unitarias de FormatRegenerationService."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.application.format_regeneration_service import (
    FormatRegenerationContextConflictError,
    FormatRegenerationContextNotFoundError,
    FormatRegenerationDocumentNotFoundError,
    FormatRegenerationDocumentStateError,
    FormatRegenerationInProgressError,
    FormatRegenerationService,
)
from app.domain.document import Document
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
    GenerationContext,
)


class FakeDocumentRepository:
    """Repositorio mínimo de documentos para regeneración."""

    def __init__(
        self,
        document: Document | None,
    ) -> None:
        self.document = document

    def find_by_id(
        self,
        document_id: str,
    ) -> Document | None:
        if (
            self.document is not None
            and self.document.document_id
            == document_id
        ):
            return self.document

        return None


class FakeGeneratedFormatRepository:
    """Repositorio en memoria con historial completo."""

    def __init__(
        self,
        formats: list[
            GeneratedFormat
        ] | None = None,
    ) -> None:
        self.formats = list(
            formats or []
        )

    def create(
        self,
        generated_format: GeneratedFormat,
    ) -> GeneratedFormat:
        self.formats.append(
            generated_format
        )
        return generated_format

    def update(
        self,
        generated_format: GeneratedFormat,
    ) -> GeneratedFormat:
        for index, stored_format in enumerate(
            self.formats
        ):
            if (
                stored_format.format_id
                == generated_format.format_id
            ):
                self.formats[index] = (
                    generated_format
                )
                return generated_format

        raise RuntimeError(
            "Formato inexistente."
        )

    def find_by_id(
        self,
        format_id: str,
    ) -> GeneratedFormat | None:
        return next(
            (
                generated_format
                for generated_format
                in self.formats
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
    ) -> list[
        GeneratedFormat
    ]:
        return [
            generated_format
            for generated_format
            in self.formats
            if (
                generated_format.document_id
                == document_id
            )
        ]


class UnusedAgents:
    """Agentes no debe ejecutarse durante prepare_regeneration."""

    async def generate_formats(
        self,
        request,
    ):
        raise AssertionError(
            "prepare_regeneration no debe invocar Agentes."
        )


def build_document(
    status: DocumentStatus = (
        DocumentStatus.INDEXED
    ),
) -> Document:
    """Construye un documento válido para las pruebas."""
    content = b"contenido"

    return Document(
        document_id="doc_123",
        original_filename="manual.txt",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
        status=status,
    )


def build_context(
    *,
    profile: str = "intermediate",
    niche: str = "backend",
    detail_level: str = "detailed",
    learning_objective: str | None = (
        "Comprender el documento."
    ),
) -> GenerationContext:
    """Construye un contexto pedagógico persistible."""
    return GenerationContext(
        profile=profile,
        niche=niche,
        detail_level=detail_level,
        learning_objective=learning_objective,
    )


def build_terminal_attempt(
    *,
    format_id: str,
    format_type: GeneratedFormatType,
    status: GeneratedFormatStatus,
    context: GenerationContext,
    created_at: datetime | None = None,
) -> GeneratedFormat:
    """Construye un intento terminal sin contenido para pruebas."""
    timestamp = (
        created_at
        or datetime.now(UTC)
    )

    return GeneratedFormat(
        format_id=format_id,
        document_id="doc_123",
        format_type=format_type,
        status=status,
        generation_context=context,
        content=None,
        chunks_used=(),
        error_message=(
            "Resultado previo."
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_processing_attempt(
    *,
    format_id: str,
    format_type: GeneratedFormatType,
    context: GenerationContext,
) -> GeneratedFormat:
    """Construye un intento activo."""
    return GeneratedFormat(
        format_id=format_id,
        document_id="doc_123",
        format_type=format_type,
        status=GeneratedFormatStatus.PROCESSING,
        generation_context=context,
    )


def build_service(
    *,
    document: Document | None,
    history: list[
        GeneratedFormat
    ] | None = None,
) -> tuple[
    FormatRegenerationService,
    FakeGeneratedFormatRepository,
]:
    """Construye el servicio con persistencia controlada."""
    document_repository = (
        FakeDocumentRepository(
            document
        )
    )

    generated_format_repository = (
        FakeGeneratedFormatRepository(
            history
        )
    )

    format_generation_service = (
        FormatGenerationService(
            document_repository=(
                document_repository
            ),
            generated_format_repository=(
                generated_format_repository
            ),
            agents=UnusedAgents(),
        )
    )

    service = FormatRegenerationService(
        document_repository=(
            document_repository
        ),
        generated_format_repository=(
            generated_format_repository
        ),
        format_generation_service=(
            format_generation_service
        ),
    )

    return (
        service,
        generated_format_repository,
    )


def test_regeneration_creates_new_processing_attempt_with_previous_context() -> None:
    """Crea un nuevo format_id reutilizando el contexto anterior."""
    context = build_context()

    previous = build_terminal_attempt(
        format_id="fmt_quiz_old",
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.FAILED,
        context=context,
    )

    service, repository = build_service(
        document=build_document(),
        history=[
            previous
        ],
    )

    attempts = (
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
        )
    )

    assert len(attempts) == 1

    regenerated = attempts[0]

    assert (
        regenerated.format_id
        != previous.format_id
    )
    assert (
        regenerated.status
        == GeneratedFormatStatus.PROCESSING
    )
    assert (
        regenerated.generation_context
        == context
    )

    assert len(
        repository.formats
    ) == 2

    assert (
        repository.formats[0]
        == previous
    )


def test_regeneration_accepts_multiple_formats_with_same_context() -> None:
    """Regenera Quiz y Flashcards dentro de un mismo nuevo lote."""
    context = build_context()

    service, _ = build_service(
        document=build_document(),
        history=[
            build_terminal_attempt(
                format_id="fmt_quiz_old",
                format_type=(
                    GeneratedFormatType.QUIZ
                ),
                status=(
                    GeneratedFormatStatus.FAILED
                ),
                context=context,
            ),
            build_terminal_attempt(
                format_id=(
                    "fmt_flashcards_old"
                ),
                format_type=(
                    GeneratedFormatType.FLASHCARDS
                ),
                status=(
                    GeneratedFormatStatus.NO_RESULTS
                ),
                context=context,
            ),
        ],
    )

    attempts = (
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
                GeneratedFormatType.FLASHCARDS,
            ),
        )
    )

    assert {
        attempt.format_type
        for attempt in attempts
    } == {
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    }

    assert all(
        attempt.status
        == GeneratedFormatStatus.PROCESSING
        for attempt in attempts
    )

    assert all(
        attempt.generation_context
        == context
        for attempt in attempts
    )


def test_regeneration_rejects_unknown_document() -> None:
    """Devuelve un error de aplicación si el documento no existe."""
    service, _ = build_service(
        document=None,
    )

    with pytest.raises(
        FormatRegenerationDocumentNotFoundError,
        match="doc_123",
    ):
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
        )


def test_regeneration_requires_indexed_document() -> None:
    """No inicia intentos para un documento no indexado."""
    context = build_context()

    service, repository = build_service(
        document=build_document(
            DocumentStatus.STORED
        ),
        history=[
            build_terminal_attempt(
                format_id="fmt_quiz_old",
                format_type=(
                    GeneratedFormatType.QUIZ
                ),
                status=(
                    GeneratedFormatStatus.FAILED
                ),
                context=context,
            )
        ],
    )

    with pytest.raises(
        FormatRegenerationDocumentStateError,
        match="indexed",
    ):
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
        )

    assert len(
        repository.formats
    ) == 1


def test_regeneration_rejects_requested_format_still_processing() -> None:
    """No crea un segundo intento mientras el actual siga processing."""
    context = build_context()

    processing = build_processing_attempt(
        format_id="fmt_quiz_processing",
        format_type=GeneratedFormatType.QUIZ,
        context=context,
    )

    service, repository = build_service(
        document=build_document(),
        history=[
            processing
        ],
    )

    with pytest.raises(
        FormatRegenerationInProgressError,
        match="quiz",
    ):
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
        )

    assert repository.formats == [
        processing
    ]


def test_regeneration_requires_previous_format_context() -> None:
    """No inventa parámetros pedagógicos si el formato no tiene historial."""
    service, repository = build_service(
        document=build_document(),
    )

    with pytest.raises(
        FormatRegenerationContextNotFoundError,
        match="quiz",
    ):
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
        )

    assert repository.formats == []


def test_regeneration_rejects_conflicting_previous_contexts() -> None:
    """Evita mezclar parámetros de dos generaciones incompatibles."""
    quiz_context = build_context()

    flashcards_context = build_context(
        profile="advanced",
    )

    service, repository = build_service(
        document=build_document(),
        history=[
            build_terminal_attempt(
                format_id="fmt_quiz_old",
                format_type=(
                    GeneratedFormatType.QUIZ
                ),
                status=(
                    GeneratedFormatStatus.FAILED
                ),
                context=quiz_context,
            ),
            build_terminal_attempt(
                format_id=(
                    "fmt_flashcards_old"
                ),
                format_type=(
                    GeneratedFormatType.FLASHCARDS
                ),
                status=(
                    GeneratedFormatStatus.FAILED
                ),
                context=flashcards_context,
            ),
        ],
    )

    with pytest.raises(
        FormatRegenerationContextConflictError,
        match="contexto pedagógico",
    ):
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
                GeneratedFormatType.FLASHCARDS,
            ),
        )

    assert len(
        repository.formats
    ) == 2


def test_regeneration_uses_latest_previous_attempt_context() -> None:
    """Toma el contexto del intento más reciente del formato."""
    first_context = build_context(
        profile="beginner",
    )

    latest_context = build_context(
        profile="advanced",
    )

    first_timestamp = datetime(
        2026,
        10,
        7,
        10,
        0,
        tzinfo=UTC,
    )

    service, _ = build_service(
        document=build_document(),
        history=[
            build_terminal_attempt(
                format_id="fmt_quiz_first",
                format_type=(
                    GeneratedFormatType.QUIZ
                ),
                status=(
                    GeneratedFormatStatus.FAILED
                ),
                context=first_context,
                created_at=first_timestamp,
            ),
            build_terminal_attempt(
                format_id="fmt_quiz_latest",
                format_type=(
                    GeneratedFormatType.QUIZ
                ),
                status=(
                    GeneratedFormatStatus.FAILED
                ),
                context=latest_context,
                created_at=(
                    first_timestamp
                    + timedelta(minutes=5)
                ),
            ),
        ],
    )

    attempts = (
        service.prepare_regeneration(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
        )
    )

    assert (
        attempts[0].generation_context
        == latest_context
    )
