"""Pruebas unitarias de DocumentService."""

from copy import deepcopy
from pathlib import Path

import pytest

from app.application.document_service import (
    DocumentNotFoundError,
    DocumentNotStoredError,
    DocumentRetrievalError,
    DocumentService,
    DocumentStorageConsistencyError,
    DocumentStorageError,
)
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.ports.document_repository import (
    DocumentRepositoryError,
)
from tests.fakes import (
    FailingDeleteObjectStorage,
    FailingDownloadObjectStorage,
    FakeObjectStorage,
)


class FakeDocumentRepository:
    """Repositorio en memoria utilizado exclusivamente por las pruebas."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    def create(self, document: Document) -> Document:
        self.documents[document.document_id] = deepcopy(
            document
        )
        return document

    def find_by_id(
        self,
        document_id: str,
    ) -> Document | None:
        document = self.documents.get(
            document_id
        )

        if document is None:
            return None

        return deepcopy(document)

    def find_by_sha256(
        self,
        sha256: str,
    ) -> Document | None:
        document = next(
            (
                document
                for document in self.documents.values()
                if document.sha256 == sha256
            ),
            None,
        )

        if document is None:
            return None

        return deepcopy(document)

    def update(self, document: Document) -> Document:
        self.documents[document.document_id] = deepcopy(
            document
        )
        return document


class FailingStoredUpdateRepository(
    FakeDocumentRepository
):
    """Falla una vez al intentar persistir el estado STORED."""

    def __init__(self) -> None:
        super().__init__()
        self._stored_update_failed = False

    def update(self, document: Document) -> Document:
        if (
            document.status == DocumentStatus.STORED
            and not self._stored_update_failed
        ):
            self._stored_update_failed = True

            raise DocumentRepositoryError(
                "Fallo simulado al persistir STORED."
            )

        return super().update(document)


class FailingStoredAndRecoveryUpdateRepository(
    FakeDocumentRepository
):
    """Falla al persistir STORED y STORAGE_FAILED."""

    def update(self, document: Document) -> Document:
        if document.status in {
            DocumentStatus.STORED,
            DocumentStatus.STORAGE_FAILED,
        }:
            raise DocumentRepositoryError(
                "Fallo simulado de persistencia."
            )

        return super().update(document)


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


def test_store_document_compensates_when_final_persistence_fails(
    tmp_path: Path,
) -> None:
    """Elimina de Object Storage un objeto cuya metadata no pudo persistirse."""
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = FailingStoredUpdateRepository()
    storage = FakeObjectStorage()

    service = DocumentService(repository)

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    document_id = registration.document.document_id

    object_name = (
        f"documents/{document_id}/original.pdf"
    )

    with pytest.raises(
        DocumentStorageError,
        match="No fue posible confirmar el almacenamiento",
    ):
        service.store_document(
            document_id=document_id,
            local_path=file_path,
            object_storage=storage,
        )

    assert object_name not in storage.uploaded_objects

    persisted_document = repository.find_by_id(
        document_id
    )

    assert persisted_document is not None
    assert (
        persisted_document.status
        == DocumentStatus.STORAGE_FAILED
    )
    assert persisted_document.oci_object_name is None


def test_store_document_reports_consistency_error_when_delete_fails(
    tmp_path: Path,
) -> None:
    """Expone una inconsistencia si no puede eliminarse el objeto cargado."""
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = FailingStoredUpdateRepository()
    storage = FailingDeleteObjectStorage()

    service = DocumentService(repository)

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    document_id = registration.document.document_id

    object_name = (
        f"documents/{document_id}/original.pdf"
    )

    with pytest.raises(
        DocumentStorageConsistencyError,
        match="quedó en un estado inconsistente",
    ):
        service.store_document(
            document_id=document_id,
            local_path=file_path,
            object_storage=storage,
        )

    assert object_name in storage.uploaded_objects

    persisted_document = repository.find_by_id(
        document_id
    )

    assert persisted_document is not None
    assert (
        persisted_document.status
        == DocumentStatus.STORING
    )
    assert persisted_document.oci_object_name is None


def test_store_document_reports_consistency_error_when_failure_status_cannot_persist(
    tmp_path: Path,
) -> None:
    """Detecta si la compensación OCI funciona pero la BD sigue fallando."""
    file_path = tmp_path / "manual.pdf"
    file_path.write_bytes(b"contenido")

    repository = (
        FailingStoredAndRecoveryUpdateRepository()
    )
    storage = FakeObjectStorage()

    service = DocumentService(repository)

    registration = service.register_document(
        local_path=file_path,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=file_path.stat().st_size,
    )

    document_id = registration.document.document_id

    object_name = (
        f"documents/{document_id}/original.pdf"
    )

    with pytest.raises(
        DocumentStorageConsistencyError,
        match="no fue posible registrar STORAGE_FAILED",
    ):
        service.store_document(
            document_id=document_id,
            local_path=file_path,
            object_storage=storage,
        )

    assert object_name not in storage.uploaded_objects

    persisted_document = repository.find_by_id(
        document_id
    )

    assert persisted_document is not None
    assert (
        persisted_document.status
        == DocumentStatus.STORING
    )
    assert persisted_document.oci_object_name is None


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
    assert (
        persisted_document.status
        == DocumentStatus.STORED
    )