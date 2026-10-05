"""Pruebas unitarias de RAGIntegrationService."""

import asyncio
from pathlib import Path

import pytest

from app.application.document_service import (
    DocumentNotFoundError,
    DocumentNotStoredError,
    DocumentService,
)
from app.application.rag_integration_service import (
    RAGIntegrationError,
    RAGIntegrationService,
)
from app.domain.enums import DocumentStatus
from tests.fakes import (
    FailingRAGPort,
    FakeDocumentRepository,
    FakeObjectStorage,
    FakeRAGPort,
)


def test_index_document_sends_retrieved_document_to_rag(
    tmp_path: Path,
) -> None:
    """Entrega a RAG el mismo documento almacenado por BackendAPI."""
    original_content = (
        b"contenido que debe recibir RAG"
    )

    file_path = (
        tmp_path / "manual.pdf"
    )

    file_path.write_bytes(
        original_content
    )

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()
    rag = FakeRAGPort()

    document_service = DocumentService(
        repository
    )

    registration = (
        document_service.register_document(
            local_path=file_path,
            original_filename="manual.pdf",
            content_type="application/pdf",
            size_bytes=file_path.stat().st_size,
        )
    )

    stored_document = (
        document_service.store_document(
            document_id=(
                registration.document.document_id
            ),
            local_path=file_path,
            object_storage=storage,
        )
    )

    integration_service = (
        RAGIntegrationService(
            document_service=document_service,
            object_storage=storage,
            rag=rag,
        )
    )

    asyncio.run(
        integration_service.index_document(
            stored_document.document_id
        )
    )

    assert len(
        rag.received_documents
    ) == 1

    received = rag.received_documents[0]

    assert (
        received.document_id
        == stored_document.document_id
    )

    assert (
        received.filename
        == "manual.pdf"
    )

    assert (
        received.content_type
        == "application/pdf"
    )

    assert (
        received.content
        == original_content
    )

    persisted_document = (
        repository.find_by_id(
            stored_document.document_id
        )
    )

    assert persisted_document is not None
    assert (
        persisted_document.status
        == DocumentStatus.INDEXED
    )


def test_index_document_preserves_backend_document_id(
    tmp_path: Path,
) -> None:
    """Conserva el identificador canónico generado por BackendAPI."""
    file_path = (
        tmp_path / "documento.txt"
    )

    file_path.write_bytes(
        b"contenido"
    )

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()
    rag = FakeRAGPort()

    document_service = DocumentService(
        repository
    )

    registration = (
        document_service.register_document(
            local_path=file_path,
            original_filename="documento.txt",
            content_type="text/plain",
            size_bytes=file_path.stat().st_size,
        )
    )

    stored_document = (
        document_service.store_document(
            document_id=(
                registration.document.document_id
            ),
            local_path=file_path,
            object_storage=storage,
        )
    )

    integration_service = (
        RAGIntegrationService(
            document_service=document_service,
            object_storage=storage,
            rag=rag,
        )
    )

    asyncio.run(
        integration_service.index_document(
            stored_document.document_id
        )
    )

    assert (
        rag.received_documents[0].document_id
        == stored_document.document_id
    )


def test_index_document_rejects_unknown_document() -> None:
    """No invoca RAG cuando el document_id no existe."""
    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()
    rag = FakeRAGPort()

    document_service = DocumentService(
        repository
    )

    integration_service = (
        RAGIntegrationService(
            document_service=document_service,
            object_storage=storage,
            rag=rag,
        )
    )

    with pytest.raises(
        DocumentNotFoundError,
    ):
        asyncio.run(
            integration_service.index_document(
                "doc_inexistente"
            )
        )

    assert (
        rag.received_documents
        == []
    )


def test_index_document_requires_stored_content(
    tmp_path: Path,
) -> None:
    """No invoca RAG si el documento todavía no está almacenado."""
    file_path = (
        tmp_path / "manual.txt"
    )

    file_path.write_bytes(
        b"contenido"
    )

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()
    rag = FakeRAGPort()

    document_service = DocumentService(
        repository
    )

    registration = (
        document_service.register_document(
            local_path=file_path,
            original_filename="manual.txt",
            content_type="text/plain",
            size_bytes=file_path.stat().st_size,
        )
    )

    integration_service = (
        RAGIntegrationService(
            document_service=document_service,
            object_storage=storage,
            rag=rag,
        )
    )

    with pytest.raises(
        DocumentNotStoredError,
    ):
        asyncio.run(
            integration_service.index_document(
                registration.document.document_id
            )
        )

    assert (
        rag.received_documents
        == []
    )


def test_index_document_marks_failure_when_rag_fails(
    tmp_path: Path,
) -> None:
    """Registra INDEXING_FAILED cuando RAG falla."""
    file_path = (
        tmp_path / "manual.txt"
    )

    file_path.write_bytes(
        b"contenido"
    )

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()

    document_service = DocumentService(
        repository
    )

    registration = (
        document_service.register_document(
            local_path=file_path,
            original_filename="manual.txt",
            content_type="text/plain",
            size_bytes=file_path.stat().st_size,
        )
    )

    stored_document = (
        document_service.store_document(
            document_id=(
                registration.document.document_id
            ),
            local_path=file_path,
            object_storage=storage,
        )
    )

    integration_service = (
        RAGIntegrationService(
            document_service=document_service,
            object_storage=storage,
            rag=FailingRAGPort(),
        )
    )

    with pytest.raises(
        RAGIntegrationError,
        match=(
            "No fue posible indexar "
            "el documento"
        ),
    ):
        asyncio.run(
            integration_service.index_document(
                stored_document.document_id
            )
        )

    persisted_document = (
        repository.find_by_id(
            stored_document.document_id
        )
    )

    assert persisted_document is not None
    assert (
        persisted_document.status
        == DocumentStatus.INDEXING_FAILED
    )