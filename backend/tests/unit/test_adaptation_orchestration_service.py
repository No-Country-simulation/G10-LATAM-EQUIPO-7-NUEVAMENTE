"""Pruebas unitarias de AdaptationOrchestrationService."""

import asyncio
import hashlib

import pytest

from app.application.adaptation_orchestration_service import (
    AdaptationDocumentStateError,
    AdaptationOrchestrationService,
)
from app.application.document_service import (
    DocumentNotFoundError,
    DocumentService,
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
from tests.fakes import FakeDocumentRepository


class SpyRAGIntegrationService:
    """Registra las solicitudes de indexación recibidas."""

    def __init__(self) -> None:
        self.document_ids: list[str] = []

    async def index_document(
        self,
        document_id: str,
    ) -> None:
        self.document_ids.append(
            document_id
        )


class SpyFormatGenerationService:
    """Registra preparación y finalización de generaciones."""

    def __init__(self) -> None:
        self.preparation_requests: list[
            dict[str, object]
        ] = []

        self.completion_requests: list[
            tuple[str, ...]
        ] = []

    def prepare_generation(
        self,
        *,
        document_id: str,
        formats: tuple[
            GeneratedFormatType,
            ...,
        ],
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[GeneratedFormat]:
        """Simula el registro previo de intentos processing."""
        self.preparation_requests.append(
            {
                "document_id": document_id,
                "formats": formats,
                "profile": profile,
                "niche": niche,
                "detail_level": detail_level,
                "learning_objective": learning_objective,
            }
        )

        generation_context = GenerationContext(
            profile=profile,
            niche=niche,
            detail_level=detail_level,
            learning_objective=learning_objective,
        )

        return [
            GeneratedFormat(
                format_id=(
                    f"fmt_{format_type.value}"
                ),
                document_id=document_id,
                format_type=format_type,
                status=(
                    GeneratedFormatStatus.PROCESSING
                ),
                generation_context=(
                    generation_context
                ),
            )
            for format_type in formats
        ]

    async def complete_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...
        ],
    ) -> list[GeneratedFormat]:
        """Registra el lote recibido para completar."""
        self.completion_requests.append(
            tuple(
                attempt.format_id
                for attempt in attempts
            )
        )

        return list(
            attempts
        )


def build_document(
    status: DocumentStatus,
) -> Document:
    """Construye un documento válido para pruebas."""
    content = b"contenido de prueba"

    return Document(
        document_id="doc_123",
        original_filename="manual.txt",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
        status=status,
        oci_object_name=(
            "documents/doc_123/original.txt"
        ),
    )


def build_service(
    status: DocumentStatus,
) -> tuple[
    AdaptationOrchestrationService,
    SpyRAGIntegrationService,
    SpyFormatGenerationService,
]:
    """Construye el orquestador con colaboradores controlados."""
    repository = FakeDocumentRepository()

    repository.create(
        build_document(
            status
        )
    )

    document_service = DocumentService(
        repository
    )

    rag_service = (
        SpyRAGIntegrationService()
    )

    generation_service = (
        SpyFormatGenerationService()
    )

    orchestration_service = (
        AdaptationOrchestrationService(
            document_service=document_service,
            rag_integration_service=rag_service,
            format_generation_service=(
                generation_service
            ),
        )
    )

    return (
        orchestration_service,
        rag_service,
        generation_service,
    )


def test_stored_document_is_indexed_without_generation() -> None:
    """Indexa un documento almacenado sin iniciar generación."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        DocumentStatus.STORED
    )

    asyncio.run(
        service.ensure_document_indexed(
            "doc_123"
        )
    )

    assert rag_service.document_ids == [
        "doc_123"
    ]

    assert (
        generation_service.preparation_requests
        == []
    )

    assert (
        generation_service.completion_requests
        == []
    )


def test_indexing_failed_document_retries_indexing() -> None:
    """Reintenta RAG después de una indexación fallida."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        DocumentStatus.INDEXING_FAILED
    )

    asyncio.run(
        service.ensure_document_indexed(
            "doc_123"
        )
    )

    assert rag_service.document_ids == [
        "doc_123"
    ]

    assert (
        generation_service.preparation_requests
        == []
    )

    assert (
        generation_service.completion_requests
        == []
    )


def test_indexed_document_skips_indexing() -> None:
    """No reindexa un documento ya disponible en RAG."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        DocumentStatus.INDEXED
    )

    asyncio.run(
        service.ensure_document_indexed(
            "doc_123"
        )
    )

    assert rag_service.document_ids == []

    assert (
        generation_service.preparation_requests
        == []
    )

    assert (
        generation_service.completion_requests
        == []
    )


@pytest.mark.parametrize(
    "status",
    [
        DocumentStatus.RECEIVED,
        DocumentStatus.VALIDATED,
        DocumentStatus.STORING,
        DocumentStatus.INDEXING,
        DocumentStatus.VALIDATION_FAILED,
        DocumentStatus.STORAGE_FAILED,
    ],
)
def test_document_in_invalid_state_cannot_be_indexed(
    status: DocumentStatus,
) -> None:
    """Rechaza estados incompatibles con la indexación."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        status
    )

    with pytest.raises(
        AdaptationDocumentStateError,
        match=(
            "no puede iniciar la indexación "
            "para adaptación"
        ),
    ):
        asyncio.run(
            service.ensure_document_indexed(
                "doc_123"
            )
        )

    assert rag_service.document_ids == []

    assert (
        generation_service.preparation_requests
        == []
    )

    assert (
        generation_service.completion_requests
        == []
    )


def test_unknown_document_is_rejected_during_indexing() -> None:
    """Propaga el error si el documento a indexar no existe."""
    repository = FakeDocumentRepository()

    service = AdaptationOrchestrationService(
        document_service=DocumentService(
            repository
        ),
        rag_integration_service=(
            SpyRAGIntegrationService()
        ),
        format_generation_service=(
            SpyFormatGenerationService()
        ),
    )

    with pytest.raises(
        DocumentNotFoundError,
        match="doc_inexistente",
    ):
        asyncio.run(
            service.ensure_document_indexed(
                "doc_inexistente"
            )
        )


def test_default_formats_are_prepared_separately() -> None:
    """Registra Quiz y Flashcards sin ejecutar indexación ni Agentes."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        DocumentStatus.INDEXED
    )

    attempts = (
        service.prepare_default_formats(
            document_id="doc_123",
            profile="intermediate",
            niche="general",
            detail_level="detailed",
            learning_objective=(
                "Comprender los conceptos principales."
            ),
        )
    )

    assert rag_service.document_ids == []

    assert len(
        generation_service.preparation_requests
    ) == 1

    assert (
        generation_service.completion_requests
        == []
    )

    request = (
        generation_service
        .preparation_requests[0]
    )

    assert (
        request["document_id"]
        == "doc_123"
    )

    assert request["formats"] == (
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    )

    assert (
        request["profile"]
        == "intermediate"
    )

    assert (
        request["niche"]
        == "general"
    )

    assert (
        request["detail_level"]
        == "detailed"
    )

    assert (
        request["learning_objective"]
        == (
            "Comprender los conceptos principales."
        )
    )

    assert len(attempts) == 2

    assert all(
        attempt.status
        == GeneratedFormatStatus.PROCESSING
        for attempt in attempts
    )


def test_default_generation_completes_prepared_attempts() -> None:
    """Completa exactamente los intentos preparados previamente."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        DocumentStatus.INDEXED
    )

    attempts = (
        service.prepare_default_formats(
            document_id="doc_123",
            profile="beginner",
            niche="backend",
            detail_level="basic",
        )
    )

    asyncio.run(
        service.complete_default_generation(
            attempts=tuple(
                attempts
            )
        )
    )

    assert rag_service.document_ids == []

    assert len(
        generation_service.preparation_requests
    ) == 1

    assert (
        generation_service
        .preparation_requests[0]
        ["learning_objective"]
        is None
    )

    assert (
        generation_service.completion_requests
        == [
            (
                "fmt_quiz",
                "fmt_flashcards",
            )
        ]
    )
