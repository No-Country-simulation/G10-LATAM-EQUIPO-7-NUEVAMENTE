"""Almacenamiento persistente de objetos en el sistema de archivos local."""

import shutil
from pathlib import Path

from app.ports.object_storage import ObjectStorageError


class LocalObjectStorage:
    """Implementa ObjectStoragePort utilizando el sistema de archivos local.

    Permite desarrollo local y ejecuciones sin conexión activa a OCI Object Storage.
    """

    def __init__(self, base_directory: Path = Path("storage/objects")) -> None:
        self._base_directory = base_directory

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        """Copia el archivo temporal al directorio persistente local."""
        try:
            target_path = self._base_directory / object_name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local_path, target_path)
        except Exception as exc:
            raise ObjectStorageError(
                f"No fue posible guardar el archivo localmente en {object_name}."
            ) from exc

    def download_file(self, object_name: str) -> bytes:
        """Lee el archivo almacenado localmente."""
        target_path = self._base_directory / object_name
        if not target_path.exists():
            raise ObjectStorageError(f"Objeto {object_name} no encontrado localmente.")
        return target_path.read_bytes()

    def delete_object(self, object_name: str) -> None:
        """Elimina el archivo almacenado localmente."""
        target_path = self._base_directory / object_name
        target_path.unlink(missing_ok=True)
