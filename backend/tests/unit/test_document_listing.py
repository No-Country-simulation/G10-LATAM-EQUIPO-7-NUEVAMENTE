"""Pruebas unitarias de consulta de documentos para biblioteca."""

import hashlib
from datetime import UTC, datetime, timedelta

from app.application.document_service import (
    DocumentService,
)
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from tests.fakes import FakeDocumentRepository


def _build_document(
    *,
    document_id: str,
    status: DocumentStatus,
    oci_object_name: str | None,
    created_at: datetime,
) -> Document:
    """Construye un documento controlado para las pruebas."""
    content = document_id.encode()

    return Document(
        document_id=document_id,
        original_filename=f"{document_id}.pdf",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
        status=status,
        oci_object_name=oci_object_name,
        created_at=created_at,
        updated_at=created_at,
    )


def test_list_active_documents_returns_only_persisted_documents() -> None:
    """Excluye documentos que todavía no tienen archivo persistido."""
    repository = FakeDocumentRepository()

    now = datetime.now(UTC)

    repository.create(
        _build_document(
            document_id="doc_stored",
            status=DocumentStatus.STORED,
            oci_object_name=(
                "documents/doc_stored/original.pdf"
            ),
            created_at=now,
        )
    )

    repository.create(
        _build_document(
            document_id="doc_failed",
            status=DocumentStatus.STORAGE_FAILED,
            oci_object_name=None,
            created_at=(
                now + timedelta(seconds=1)
            ),
        )
    )

    service = DocumentService(
        repository
    )

    documents = (
        service.list_active_documents()
    )

    assert [
        document.document_id
        for document in documents
    ] == [
        "doc_stored",
    ]


def test_list_active_documents_keeps_indexing_failed_document() -> None:
    """Un fallo de indexación no elimina el documento de biblioteca."""
    repository = FakeDocumentRepository()

    now = datetime.now(UTC)

    repository.create(
        _build_document(
            document_id="doc_retryable",
            status=DocumentStatus.INDEXING_FAILED,
            oci_object_name=(
                "documents/doc_retryable/original.pdf"
            ),
            created_at=now,
        )
    )

    service = DocumentService(
        repository
    )

    documents = (
        service.list_active_documents()
    )

    assert len(documents) == 1
    assert (
        documents[0].status
        == DocumentStatus.INDEXING_FAILED
    )


def test_list_active_documents_returns_newest_first() -> None:
    """Mantiene el orden establecido por el repositorio."""
    repository = FakeDocumentRepository()

    now = datetime.now(UTC)

    repository.create(
        _build_document(
            document_id="doc_old",
            status=DocumentStatus.STORED,
            oci_object_name=(
                "documents/doc_old/original.pdf"
            ),
            created_at=now,
        )
    )

    repository.create(
        _build_document(
            document_id="doc_new",
            status=DocumentStatus.INDEXED,
            oci_object_name=(
                "documents/doc_new/original.pdf"
            ),
            created_at=(
                now + timedelta(seconds=1)
            ),
        )
    )

    service = DocumentService(
        repository
    )

    documents = (
        service.list_active_documents()
    )

    assert [
        document.document_id
        for document in documents
    ] == [
        "doc_new",
        "doc_old",
    ]