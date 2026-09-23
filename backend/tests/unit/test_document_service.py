"""Pruebas unitarias de DocumentService."""

from pathlib import Path

import pytest

from app.application.document_service import (
    DocumentNotFoundError,
    DocumentNotStoredError,
    DocumentRetrievalError,
    DocumentService,
)
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from tests.fakes import (
    FailingDownloadObjectStorage,
    FakeObjectStorage,
)


class FakeDocumentRepository:
    """Repositorio en memoria utilizado exclusivamente por las pruebas."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    def create(self, document: Document) -> Document:
        self.documents[document.document_id] = document
        return document

    def find_by_id(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def find_by_sha256(self, sha256: str) -> Document | None:
        return next(
            (
                document
                for document in self.documents.values()
                if document.sha256 == sha256
            ),
            None,
        )

    def update(self, document: Document) -> Document:
        self.documents[document.document_id] = document
        return document


def test_register_document(tmp_path: Path) -> None:
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()

    service = DocumentService(repository)

    result = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    assert result.created is True
    assert result.document.status == DocumentStatus.VALIDATED


def test_register_duplicate_reuses_document(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()

    service = DocumentService(repository)

    first = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    second = service.register_document(
        local_path=file_path,
        original_filename="copia.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    assert (
        first.document.document_id
        == second.document.document_id
    )
    assert second.created is False


def test_store_document(tmp_path: Path) -> None:
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()

    service = DocumentService(repository)

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    document = service.store_document(
        document_id=registration.document.document_id,
        local_path=file_path,
        object_storage=storage,
    )

    assert document.status == DocumentStatus.STORED
    assert document.oci_object_name is not None
    assert (
        document.oci_object_name
        in storage.uploaded_objects
    )


def test_retrieve_document_returns_original_content(
    tmp_path: Path,
) -> None:
    """Recupera exactamente el contenido almacenado."""
    original_content = (
        b"contenido original recuperado desde object storage"
    )

    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(original_content)

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()

    service = DocumentService(repository)

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    stored_document = service.store_document(
        document_id=registration.document.document_id,
        local_path=file_path,
        object_storage=storage,
    )

    retrieved_document = service.retrieve_document(
        document_id=stored_document.document_id,
        object_storage=storage,
    )

    assert (
        retrieved_document.document_id
        == stored_document.document_id
    )
    assert retrieved_document.filename == "manual.pdf"
    assert (
        retrieved_document.content_type
        == "application/pdf"
    )
    assert retrieved_document.content == original_content


def test_retrieve_unknown_document_raises_error() -> None:
    """Un document_id inexistente se controla explícitamente."""
    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()

    service = DocumentService(repository)

    with pytest.raises(
        DocumentNotFoundError,
        match="No existe el documento doc_inexistente.",
    ):
        service.retrieve_document(
            document_id="doc_inexistente",
            object_storage=storage,
        )


def test_retrieve_document_without_object_raises_error(
    tmp_path: Path,
) -> None:
    """Un documento registrado pero no almacenado no puede recuperarse."""
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()

    service = DocumentService(repository)

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    document_id = registration.document.document_id

    with pytest.raises(
        DocumentNotStoredError,
        match=(
            f"El documento {document_id} no tiene "
            "un objeto almacenado asociado."
        ),
    ):
        service.retrieve_document(
            document_id=document_id,
            object_storage=storage,
        )


def test_retrieve_document_handles_object_storage_error(
    tmp_path: Path,
) -> None:
    """Los fallos de Object Storage se traducen a error de aplicación."""
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = FakeDocumentRepository()
    working_storage = FakeObjectStorage()

    service = DocumentService(repository)

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    stored_document = service.store_document(
        document_id=registration.document.document_id,
        local_path=file_path,
        object_storage=working_storage,
    )

    failing_storage = FailingDownloadObjectStorage()

    with pytest.raises(
        DocumentRetrievalError,
        match=(
            "No fue posible recuperar el documento "
            f"{stored_document.document_id}."
        ),
    ):
        service.retrieve_document(
            document_id=stored_document.document_id,
            object_storage=failing_storage,
        )

    persisted_document = repository.find_by_id(
        stored_document.document_id
    )

    assert persisted_document is not None
    assert persisted_document.status == DocumentStatus.STORED