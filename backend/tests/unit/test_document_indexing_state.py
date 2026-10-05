"""Pruebas de transiciones de estado durante indexación."""

from pathlib import Path

import pytest

from app.application.document_service import (
    DocumentIndexingStateError,
    DocumentService,
)
from app.domain.enums import DocumentStatus
from tests.fakes import (
    FakeDocumentRepository,
    FakeObjectStorage,
)


def _create_stored_document(
    tmp_path: Path,
) -> tuple[
    DocumentService,
    FakeDocumentRepository,
    str,
]:
    """Construye un documento almacenado listo para indexación."""
    file_path = (
        tmp_path / "manual.txt"
    )

    file_path.write_bytes(
        b"contenido"
    )

    repository = FakeDocumentRepository()
    storage = FakeObjectStorage()

    service = DocumentService(
        repository
    )

    registration = (
        service.register_document(
            local_path=file_path,
            original_filename="manual.txt",
            content_type="text/plain",
            size_bytes=file_path.stat().st_size,
        )
    )

    stored_document = (
        service.store_document(
            document_id=(
                registration.document.document_id
            ),
            local_path=file_path,
            object_storage=storage,
        )
    )

    return (
        service,
        repository,
        stored_document.document_id,
    )


def test_start_indexing_transitions_stored_to_indexing(
    tmp_path: Path,
) -> None:
    """Un documento almacenado puede iniciar indexación."""
    service, repository, document_id = (
        _create_stored_document(
            tmp_path
        )
    )

    service.start_indexing(
        document_id
    )

    document = repository.find_by_id(
        document_id
    )

    assert document is not None
    assert (
        document.status
        == DocumentStatus.INDEXING
    )


def test_complete_indexing_transitions_to_indexed(
    tmp_path: Path,
) -> None:
    """Una indexación activa puede completarse."""
    service, repository, document_id = (
        _create_stored_document(
            tmp_path
        )
    )

    service.start_indexing(
        document_id
    )

    service.complete_indexing(
        document_id
    )

    document = repository.find_by_id(
        document_id
    )

    assert document is not None
    assert (
        document.status
        == DocumentStatus.INDEXED
    )


def test_failed_indexing_can_be_retried(
    tmp_path: Path,
) -> None:
    """Un documento con indexación fallida puede reintentarse."""
    service, repository, document_id = (
        _create_stored_document(
            tmp_path
        )
    )

    service.start_indexing(
        document_id
    )

    service.fail_indexing(
        document_id
    )

    failed_document = (
        repository.find_by_id(
            document_id
        )
    )

    assert failed_document is not None
    assert (
        failed_document.status
        == DocumentStatus.INDEXING_FAILED
    )

    service.start_indexing(
        document_id
    )

    retry_document = (
        repository.find_by_id(
            document_id
        )
    )

    assert retry_document is not None
    assert (
        retry_document.status
        == DocumentStatus.INDEXING
    )


def test_indexing_rejects_invalid_document_state(
    tmp_path: Path,
) -> None:
    """No inicia indexación antes del almacenamiento persistente."""
    file_path = (
        tmp_path / "manual.txt"
    )

    file_path.write_bytes(
        b"contenido"
    )

    repository = FakeDocumentRepository()

    service = DocumentService(
        repository
    )

    registration = (
        service.register_document(
            local_path=file_path,
            original_filename="manual.txt",
            content_type="text/plain",
            size_bytes=file_path.stat().st_size,
        )
    )

    with pytest.raises(
        DocumentIndexingStateError,
        match="no puede pasar a indexing",
    ):
        service.start_indexing(
            registration.document.document_id
        )