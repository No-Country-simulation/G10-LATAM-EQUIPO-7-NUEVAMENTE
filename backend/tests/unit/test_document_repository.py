"""Pruebas del repositorio SQLite de documentos."""

import hashlib

from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_document_repository import (
    SQLiteDocumentRepository,
)


def build_document() -> Document:
    content = b"Documento persistido"

    return Document(
        document_id="doc_123",
        original_filename="manual.pdf",
        sha256=hashlib.sha256(content).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
    )


def test_repository_creates_and_finds_document(tmp_path) -> None:
    database_path = tmp_path / "test.db"

    database = SQLiteDatabase(
        f"sqlite:///{database_path.as_posix()}"
    )
    database.initialize()

    repository = SQLiteDocumentRepository(database)
    document = build_document()

    repository.create(document)

    stored = repository.find_by_id(document.document_id)

    assert stored is not None
    assert stored.document_id == document.document_id
    assert stored.sha256 == document.sha256


def test_repository_finds_document_by_sha256(tmp_path) -> None:
    database = SQLiteDatabase(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    database.initialize()

    repository = SQLiteDocumentRepository(database)
    document = build_document()

    repository.create(document)

    stored = repository.find_by_sha256(document.sha256)

    assert stored is not None
    assert stored.document_id == document.document_id


def test_repository_updates_document(tmp_path) -> None:
    database = SQLiteDatabase(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    database.initialize()

    repository = SQLiteDocumentRepository(database)
    document = build_document()

    repository.create(document)

    document.update_status(DocumentStatus.STORED)
    document.assign_oci_object(
        "documents/doc_123/original.pdf"
    )

    repository.update(document)

    stored = repository.find_by_id(document.document_id)

    assert stored is not None
    assert stored.status == DocumentStatus.STORED
    assert (
        stored.oci_object_name
        == "documents/doc_123/original.pdf"
    )