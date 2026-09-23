"""Pruebas unitarias de DocumentService."""

from pathlib import Path

from app.application.document_service import DocumentService
from app.domain.document import Document
from app.domain.enums import DocumentStatus


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


class FakeObjectStorage:
    """Almacenamiento falso para pruebas del caso de uso."""

    def __init__(self) -> None:
        self.uploaded_objects: dict[str, bytes] = {}

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        self.uploaded_objects[object_name] = local_path.read_bytes()

    def download_file(self, object_name: str) -> bytes:
        return self.uploaded_objects[object_name]

    def delete_object(self, object_name: str) -> None:
        self.uploaded_objects.pop(object_name, None)


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


def test_register_duplicate_reuses_document(tmp_path: Path) -> None:
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

    assert first.document.document_id == second.document.document_id
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
    assert document.oci_object_name in storage.uploaded_objects