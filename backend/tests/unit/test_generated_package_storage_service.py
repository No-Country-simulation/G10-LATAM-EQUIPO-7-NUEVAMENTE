"""Pruebas del servicio de persistencia del paquete educativo."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.application.generated_package_storage_service import (
    GeneratedPackageDataError,
    GeneratedPackageStorageError,
    GeneratedPackageStorageService,
)
from app.domain.document import Document
from app.domain.enums import (
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
from app.domain.learning_metadata import (
    LearningMetadata,
)
from app.ports.object_storage_port import (
    ObjectStorageError,
)

DOCUMENT_ID = "doc_package_123"


class FakeDocumentRepository:
    """Repositorio mínimo de documentos para el servicio."""

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
    """Repositorio mínimo de historial de formatos."""

    def __init__(
        self,
        history: list[
            GeneratedFormat
        ],
    ) -> None:
        self.history = history

    def find_by_document_id(
        self,
        document_id: str,
    ) -> list[
        GeneratedFormat
    ]:
        return [
            generated_format
            for generated_format
            in self.history
            if (
                generated_format.document_id
                == document_id
            )
        ]


class CapturingObjectStorage:
    """Captura la escritura binaria que realizaría OCI."""

    def __init__(self) -> None:
        self.objects: dict[
            str,
            tuple[
                bytes,
                str | None,
            ],
        ] = {}

    def upload_bytes(
        self,
        *,
        content: bytes,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        self.objects[
            object_name
        ] = (
            content,
            content_type,
        )


class FailingObjectStorage(
    CapturingObjectStorage
):
    """Simula un fallo del proveedor al escribir el JSON."""

    def upload_bytes(
        self,
        *,
        content: bytes,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        raise ObjectStorageError(
            "Fallo simulado."
        )


def build_document(
    *,
    learning_metadata: (
        LearningMetadata | None
    ) = None,
) -> Document:
    """Construye un documento indexado con metadata pedagógica."""
    content = b"contenido"

    return Document(
        document_id=DOCUMENT_ID,
        original_filename="manual.txt",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
        status=DocumentStatus.INDEXED,
        learning_metadata=(
            learning_metadata
            if learning_metadata is not None
            else LearningMetadata(
                key_concepts=(
                    "BackendAPI",
                    "RAG",
                ),
                prerequisites=(
                    "APIs REST",
                ),
                estimated_time_minutes=15,
            )
        ),
    )


def build_context() -> GenerationContext:
    """Construye el contexto compartido del historial."""
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
    )


def build_evidence() -> tuple[
    ChunkEvidence,
    ...
]:
    """Construye evidencia válida para un resultado exitoso."""
    return (
        ChunkEvidence(
            chunk_id="chunk_1",
            document_id=DOCUMENT_ID,
            rank=1,
            score=0.95,
            text="Contenido utilizado.",
        ),
    )


def build_quiz(
    *,
    format_id: str,
    status: GeneratedFormatStatus,
    created_at: datetime,
) -> GeneratedFormat:
    """Construye un intento de Quiz."""
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
                title=format_id,
                instructions="Seleccione una opción.",
                questions=(
                    QuizQuestion(
                        question_id="q1",
                        question="¿Qué es RAG?",
                        options=(
                            "Retrieval",
                            "Storage",
                        ),
                        correct_answer="Retrieval",
                        explanation="Usa recuperación.",
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
            if status
            in {
                GeneratedFormatStatus.SUCCESS,
                GeneratedFormatStatus.PROCESSING,
            }
            else "Fallo de Quiz."
        ),
        created_at=created_at,
        updated_at=created_at,
    )


def build_flashcards(
    *,
    format_id: str,
    status: GeneratedFormatStatus,
    created_at: datetime,
) -> GeneratedFormat:
    """Construye un intento de Flashcards."""
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
                title=format_id,
                instructions="Revise las tarjetas.",
                cards=(
                    FlashcardItem(
                        card_id="c1",
                        front="RAG",
                        back="Retrieval Augmented Generation",
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
            if status
            in {
                GeneratedFormatStatus.SUCCESS,
                GeneratedFormatStatus.PROCESSING,
            }
            else "Fallo de Flashcards."
        ),
        created_at=created_at,
        updated_at=created_at,
    )


def build_service(
    *,
    history: list[
        GeneratedFormat
    ],
    document: Document | None = None,
    object_storage=None,
) -> tuple[
    GeneratedPackageStorageService,
    CapturingObjectStorage,
]:
    """Construye el servicio con colaboradores controlados."""
    storage = (
        object_storage
        if object_storage is not None
        else CapturingObjectStorage()
    )

    service = GeneratedPackageStorageService(
        document_repository=(
            FakeDocumentRepository(
                document
                if document is not None
                else build_document()
            )
        ),
        generated_format_repository=(
            FakeGeneratedFormatRepository(
                history
            )
        ),
        object_storage=storage,
    )

    return service, storage


def test_persists_complete_package_in_canonical_path() -> None:
    """Guarda metadata, Quiz y Flashcards en un único JSON UTF-8."""
    timestamp = datetime(
        2026,
        10,
        7,
        16,
        0,
        tzinfo=UTC,
    )

    service, storage = build_service(
        history=[
            build_quiz(
                format_id="fmt_quiz_v1",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=timestamp,
            ),
            build_flashcards(
                format_id="fmt_flashcards_v1",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=timestamp,
            ),
        ]
    )

    object_name = (
        service.persist_current_package(
            DOCUMENT_ID
        )
    )

    assert object_name == (
        f"documents/{DOCUMENT_ID}/"
        "generated/content.json"
    )

    content, content_type = (
        storage.objects[
            object_name
        ]
    )

    assert (
        content_type
        == "application/json"
    )

    data = json.loads(
        content.decode(
            "utf-8"
        )
    )

    assert (
        data["document_id"]
        == DOCUMENT_ID
    )
    assert (
        data["learning_metadata"]
        ["estimated_time_minutes"]
        == 15
    )
    assert (
        data["formats"]["quiz"]["format_id"]
        == "fmt_quiz_v1"
    )
    assert (
        data["formats"]["flashcards"]["format_id"]
        == "fmt_flashcards_v1"
    )


def test_regenerating_one_format_preserves_other_current_success() -> None:
    """Actualiza Quiz sin perder las Flashcards vigentes."""
    base = datetime(
        2026,
        10,
        7,
        16,
        0,
        tzinfo=UTC,
    )

    service, storage = build_service(
        history=[
            build_quiz(
                format_id="fmt_quiz_v1",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=base,
            ),
            build_flashcards(
                format_id="fmt_flashcards_v1",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=base,
            ),
            build_quiz(
                format_id="fmt_quiz_v2",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=(
                    base
                    + timedelta(minutes=10)
                ),
            ),
        ]
    )

    object_name = (
        service.persist_current_package(
            DOCUMENT_ID
        )
    )

    data = json.loads(
        storage.objects[
            object_name
        ][0].decode(
            "utf-8"
        )
    )

    assert (
        data["formats"]["quiz"]["format_id"]
        == "fmt_quiz_v2"
    )
    assert (
        data["formats"]["flashcards"]["format_id"]
        == "fmt_flashcards_v1"
    )


def test_failed_regeneration_preserves_previous_success() -> None:
    """Un reintento fallido no reemplaza contenido válido en OCI."""
    base = datetime(
        2026,
        10,
        7,
        16,
        0,
        tzinfo=UTC,
    )

    service, storage = build_service(
        history=[
            build_quiz(
                format_id="fmt_quiz_success",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=base,
            ),
            build_quiz(
                format_id="fmt_quiz_failed_retry",
                status=GeneratedFormatStatus.FAILED,
                created_at=(
                    base
                    + timedelta(minutes=10)
                ),
            ),
        ]
    )

    object_name = (
        service.persist_current_package(
            DOCUMENT_ID
        )
    )

    data = json.loads(
        storage.objects[
            object_name
        ][0].decode(
            "utf-8"
        )
    )

    assert (
        data["formats"]["quiz"]["format_id"]
        == "fmt_quiz_success"
    )
    assert (
        data["formats"]["quiz"]["status"]
        == "success"
    )


def test_processing_attempt_does_not_replace_stable_package() -> None:
    """Un intento activo no elimina el último resultado terminal."""
    base = datetime(
        2026,
        10,
        7,
        16,
        0,
        tzinfo=UTC,
    )

    service, storage = build_service(
        history=[
            build_flashcards(
                format_id="fmt_flashcards_v1",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=base,
            ),
            build_flashcards(
                format_id="fmt_flashcards_processing",
                status=GeneratedFormatStatus.PROCESSING,
                created_at=(
                    base
                    + timedelta(minutes=5)
                ),
            ),
        ]
    )

    object_name = (
        service.persist_current_package(
            DOCUMENT_ID
        )
    )

    data = json.loads(
        storage.objects[
            object_name
        ][0].decode(
            "utf-8"
        )
    )

    assert (
        data["formats"]["flashcards"]["format_id"]
        == "fmt_flashcards_v1"
    )


def test_rejects_document_without_learning_metadata() -> None:
    """No crea un paquete incompleto sin metadata pedagógica."""
    document = build_document()
    document.learning_metadata = None

    service, _ = build_service(
        document=document,
        history=[
            build_quiz(
                format_id="fmt_quiz_v1",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=datetime.now(
                    UTC
                ),
            ),
        ],
    )

    with pytest.raises(
        GeneratedPackageDataError,
        match="metadatos pedagógicos",
    ):
        service.persist_current_package(
            DOCUMENT_ID
        )


def test_wraps_object_storage_failure() -> None:
    """Expone un error propio cuando falla la escritura del JSON."""
    service, _ = build_service(
        history=[
            build_quiz(
                format_id="fmt_quiz_v1",
                status=GeneratedFormatStatus.SUCCESS,
                created_at=datetime.now(
                    UTC
                ),
            ),
        ],
        object_storage=(
            FailingObjectStorage()
        ),
    )

    with pytest.raises(
        GeneratedPackageStorageError,
        match="Object Storage",
    ):
        service.persist_current_package(
            DOCUMENT_ID
        )
