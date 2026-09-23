"""Dobles de prueba compartidos por BackendAPI."""

from copy import deepcopy
from pathlib import Path

from app.domain.document import Document
from app.ports.object_storage import ObjectStorageError
from app.ports.rag import (
    RagDocumentInput,
    RagError,
)


class FakeDocumentRepository:
    """Repositorio de documentos en memoria para pruebas."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    def create(
        self,
        document: Document,
    ) -> Document:
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

    def update(
        self,
        document: Document,
    ) -> Document:
        self.documents[document.document_id] = deepcopy(
            document
        )

        return document


class FakeObjectStorage:
    """Almacenamiento en memoria para pruebas."""

    def __init__(self) -> None:
        self.uploaded_objects: dict[str, bytes] = {}

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        self.uploaded_objects[object_name] = (
            local_path.read_bytes()
        )

    def download_file(
        self,
        object_name: str,
    ) -> bytes:
        return self.uploaded_objects[object_name]

    def delete_object(
        self,
        object_name: str,
    ) -> None:
        self.uploaded_objects.pop(
            object_name,
            None,
        )


class FailingObjectStorage(FakeObjectStorage):
    """Simula un fallo durante la escritura en Object Storage."""

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        raise ObjectStorageError(
            "Fallo simulado de Object Storage."
        )


class FailingDownloadObjectStorage(FakeObjectStorage):
    """Simula un fallo durante la lectura desde Object Storage."""

    def download_file(
        self,
        object_name: str,
    ) -> bytes:
        raise ObjectStorageError(
            f"Fallo simulado al recuperar {object_name}."
        )


class FailingDeleteObjectStorage(FakeObjectStorage):
    """Simula un fallo durante una compensación de Object Storage."""

    def delete_object(
        self,
        object_name: str,
    ) -> None:
        raise ObjectStorageError(
            f"Fallo simulado al eliminar {object_name}."
        )


class FakeRagPort:
    """RAG falso que registra los documentos recibidos."""

    def __init__(self) -> None:
        self.received_documents: list[
            RagDocumentInput
        ] = []

    async def index_document(
        self,
        document: RagDocumentInput,
    ) -> None:
        self.received_documents.append(
            document
        )


class FailingRagPort:
    """RAG falso que simula un fallo al recibir documentos."""

    async def index_document(
        self,
        document: RagDocumentInput,
    ) -> None:
        raise RagError(
            "Fallo simulado del módulo RAG."
        )