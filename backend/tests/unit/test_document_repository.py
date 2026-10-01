"""Pruebas del repositorio SQLite de documentos."""

import hashlib
from pathlib import Path

from app.application.document_service import (
    DocumentService,
)
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from tests.fakes import FakeObjectStorage


def build_document() -> Document:
    """Construye un documento válido para las pruebas del repositorio."""
    content = b"Documento persistido"

    return Document(
        document_id="doc_123",
        original_filename="manual.pdf",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
    )


def build_repository(
    tmp_path: Path,
) -> SQLiteDocumentRepositoryAdapter:
    """Crea un repositorio SQLite aislado para una prueba."""
    database = SQLiteDatabase(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    database.initialize()

    return SQLiteDocumentRepositoryAdapter(
        database
    )


def test_repository_creates_and_finds_document(
    tmp_path: Path,
) -> None:
    """Persiste y recupera un documento mediante su document_id."""
    repository = build_repository(
        tmp_path
    )
    document = build_document()

    repository.create(
        document
    )

    stored = repository.find_by_id(
        document.document_id
    )

    assert stored is not None
    assert (
        stored.document_id
        == document.document_id
    )
    assert stored.sha256 == document.sha256


def test_repository_finds_document_by_sha256(
    tmp_path: Path,
) -> None:
    """Recupera un documento mediante su firma SHA-256."""
    repository = build_repository(
        tmp_path
    )
    document = build_document()

    repository.create(
        document
    )

    stored = repository.find_by_sha256(
        document.sha256
    )

    assert stored is not None
    assert (
        stored.document_id
        == document.document_id
    )


def test_repository_updates_document(
    tmp_path: Path,
) -> None:
    """Persiste estado y ruta OCI asociados al documento."""
    repository = build_repository(
        tmp_path
    )
    document = build_document()

    repository.create(
        document
    )

    document.update_status(
        DocumentStatus.STORED
    )
    document.assign_oci_object(
        "documents/doc_123/original.pdf"
    )

    repository.update(
        document
    )

    stored = repository.find_by_id(
        document.document_id
    )

    assert stored is not None
    assert (
        stored.status
        == DocumentStatus.STORED
    )
    assert (
        stored.oci_object_name
        == "documents/doc_123/original.pdf"
    )


def test_store_document_persists_id_and_oci_path(
    tmp_path: Path,
) -> None:
    """Persiste en SQLite el ID y la ruta OCI generados por el flujo real."""
    file_path = tmp_path / "manual.pdf"
    file_content = b"contenido persistido en object storage"

    file_path.write_bytes(
        file_content
    )

    repository = build_repository(
        tmp_path
    )
    object_storage = FakeObjectStorage()

    service = DocumentService(
        repository
    )

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    document_id = (
        registration.document.document_id
    )

    stored_document = service.store_document(
        document_id=document_id,
        local_path=file_path,
        object_storage=object_storage,
    )

    expected_object_name = (
        f"documents/{document_id}/original.pdf"
    )

    # Se consulta nuevamente desde SQLite para comprobar
    # que el ID y la ruta no existan solo en memoria.
    persisted_document = (
        repository.find_by_id(
            document_id
        )
    )

    assert persisted_document is not None

    assert (
        persisted_document.document_id
        == document_id
    )
    assert (
        persisted_document.oci_object_name
        == expected_object_name
    )
    assert (
        persisted_document.status
        == DocumentStatus.STORED
    )

    assert (
        stored_document.oci_object_name
        == expected_object_name
    )

    assert (
        object_storage.uploaded_objects[
            expected_object_name
        ]
        == file_content
    )