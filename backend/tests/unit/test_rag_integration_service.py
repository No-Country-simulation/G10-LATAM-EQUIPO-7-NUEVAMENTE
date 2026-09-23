"""Pruebas unitarias de RagIntegrationService."""

import asyncio
from pathlib import Path

import pytest

from app.application.document_service import (
    DocumentNotFoundError,
    DocumentNotStoredError,
    DocumentService,
)
from app.application.rag_integration_service import (
    RagIntegrationError,
    RagIntegrationService,
)
from tests.fakes import (
    FailingRagPort,
    FakeDocumentRepository,
    FakeObjectStorage,
    FakeRagPort,
)


def test_index_document_sends_retrieved_document_to_rag(
    tmp_path: Path,
) -> None:
    """Entrega a RAG el mismo documento almacenado por BackendAPI."""
    original_content = b"contenido que debe recibir RAG"

    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(original_content)

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()
    rag = FakeRagPort()

    document_service = DocumentService(
        repository
    )

    registration = document_service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    stored_document = document_service.store_document(
        document_id=registration.document.document_id,
        local_path=file_path,
        object_storage=storage,
    )

    integration_service = RagIntegrationService(
        document_service=document_service,
        object_storage=storage,
        rag=rag,
    )

    asyncio.run(
        integration_service.index_document(
            stored_document.document_id
        )
    )

    assert len(rag.received_documents) == 1

    received = rag.received_documents[0]

    assert (
        received.document_id
        == stored_document.document_id
    )
    assert received.filename == "manual.pdf"
    assert received.content_type == "application/pdf"
    assert received.content == original_content


def test_index_document_preserves_backend_document_id(
    tmp_path: Path,
) -> None:
    """El document_id enviado a RAG es el identificador canónico de Backend."""
    file_path = tmp_path / "documento.txt"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()
    rag = FakeRagPort()

    document_service = DocumentService(
        repository
    )

    registration = document_service.register_document(
        local_path=file_path,
        original_filename="documento.txt",
        content_type="text/plain",
        size_bytes=file_path.stat().st_size,
    )

    stored_document = document_service.store_document(
        document_id=registration.document.document_id,
        local_path=file_path,
        object_storage=storage,
    )

    integration_service = RagIntegrationService(
        document_service=document_service,
        object_storage=storage,
        rag=rag,
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
    rag = FakeRagPort()

    document_service = DocumentService(
        repository
    )

    integration_service = RagIntegrationService(
        document_service=document_service,
        object_storage=storage,
        rag=rag,
    )

    with pytest.raises(
        DocumentNotFoundError,
    ):
        asyncio.run(
            integration_service.index_document(
                "doc_inexistente"
            )
        )

    assert rag.received_documents == []


def test_index_document_requires_stored_content(
    tmp_path: Path,
) -> None:
    """No invoca RAG si el documento todavía no está en Object Storage."""
    file_path = tmp_path / "manual.txt"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()
    rag = FakeRagPort()

    document_service = DocumentService(
        repository
    )

    registration = document_service.register_document(
        local_path=file_path,
        original_filename="manual.txt",
        content_type="text/plain",
        size_bytes=file_path.stat().st_size,
    )

    integration_service = RagIntegrationService(
        document_service=document_service,
        object_storage=storage,
        rag=rag,
    )

    with pytest.raises(
        DocumentNotStoredError,
    ):
        asyncio.run(
            integration_service.index_document(
                registration.document.document_id
            )
        )

    assert rag.received_documents == []


def test_index_document_translates_rag_error(
    tmp_path: Path,
) -> None:
    """Traduce fallos de RAG a un error propio de aplicación."""
    file_path = tmp_path / "manual.txt"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()

    document_service = DocumentService(
        repository
    )

    registration = document_service.register_document(
        local_path=file_path,
        original_filename="manual.txt",
        content_type="text/plain",
        size_bytes=file_path.stat().st_size,
    )

    stored_document = document_service.store_document(
        document_id=registration.document.document_id,
        local_path=file_path,
        object_storage=storage,
    )

    integration_service = RagIntegrationService(
        document_service=document_service,
        object_storage=storage,
        rag=FailingRagPort(),
    )

    with pytest.raises(
        RagIntegrationError,
        match="No fue posible entregar el documento",
    ):
        asyncio.run(
            integration_service.index_document(
                stored_document.document_id
            )
        )