"""Dobles de prueba compartidos por BackendAPI."""

from pathlib import Path

from app.ports.object_storage import ObjectStorageError


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