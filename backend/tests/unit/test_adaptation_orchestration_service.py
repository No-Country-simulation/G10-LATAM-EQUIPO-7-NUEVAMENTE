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
    GeneratedFormatType,
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
    """Registra la solicitud de generación recibida."""

    def __init__(self) -> None:
        self.requests: list[
            dict[str, object]
        ] = []

    async def generate_formats(
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
    ) -> list:
        self.requests.append(
            {
                "document_id": document_id,
                "formats": formats,
                "profile": profile,
                "niche": niche,
                "detail_level": detail_level,
                "learning_objective": learning_objective,
            }
        )

        return []


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


def test_stored_document_is_indexed_before_generation() -> None:
    """Indexa un documento almacenado antes de generar formatos."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        DocumentStatus.STORED
    )

    asyncio.run(
        service.adapt_document(
            document_id="doc_123",
            profile="intermediate",
            niche="general",
            detail_level="detailed",
            learning_objective=(
                "Comprender los conceptos principales."
            ),
        )
    )

    assert rag_service.document_ids == [
        "doc_123"
    ]

    assert len(
        generation_service.requests
    ) == 1

    request = (
        generation_service.requests[0]
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

    assert request[
        "learning_objective"
    ] == (
        "Comprender los conceptos principales."
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
        service.adapt_document(
            document_id="doc_123",
            profile="beginner",
            niche="backend",
            detail_level="basic",
        )
    )

    assert rag_service.document_ids == [
        "doc_123"
    ]

    assert len(
        generation_service.requests
    ) == 1


def test_indexed_document_skips_indexing() -> None:
    """No reindexa un documento que ya está disponible en RAG."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        DocumentStatus.INDEXED
    )

    asyncio.run(
        service.adapt_document(
            document_id="doc_123",
            profile="advanced",
            niche="business",
            detail_level="detailed",
        )
    )

    assert rag_service.document_ids == []

    assert len(
        generation_service.requests
    ) == 1


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
def test_document_in_invalid_state_is_rejected(
    status: DocumentStatus,
) -> None:
    """No inicia adaptación desde estados no disponibles."""
    (
        service,
        rag_service,
        generation_service,
    ) = build_service(
        status
    )

    with pytest.raises(
        AdaptationDocumentStateError,
        match="no puede iniciar la adaptación",
    ):
        asyncio.run(
            service.adapt_document(
                document_id="doc_123",
                profile="intermediate",
                niche="general",
                detail_level="detailed",
            )
        )

    assert rag_service.document_ids == []
    assert generation_service.requests == []


def test_unknown_document_is_rejected() -> None:
    """Propaga el error cuando el documento no existe."""
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
            service.adapt_document(
                document_id="doc_inexistente",
                profile="intermediate",
                niche="general",
                detail_level="detailed",
            )
        )