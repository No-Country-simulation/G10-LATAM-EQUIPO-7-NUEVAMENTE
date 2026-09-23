"""Dobles de prueba compartidos por BackendAPI."""

from pathlib import Path


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
    """Simula un fallo del proveedor de objetos."""

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        raise RuntimeError(
            "Fallo simulado de Object Storage."
        )