"""Puerto para almacenamiento persistente de objetos."""

from pathlib import Path
from typing import Protocol


class ObjectStorageError(Exception):
    """Error general al acceder al almacenamiento de objetos."""


class ObjectStorageConfigurationError(ObjectStorageError):
    """La configuración del proveedor de objetos es inválida."""


class ObjectStoragePort(Protocol):
    """Define las operaciones de almacenamiento requeridas por BackendAPI."""

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        """Almacena un archivo en el proveedor configurado.

        Args:
            local_path: Ruta temporal del archivo que será almacenado.
            object_name: Identificador lógico del objeto.
            content_type: MIME type del contenido, cuando esté disponible.

        Raises:
            ObjectStorageError: Si el proveedor no permite almacenar
                el objeto.
        """
        ...

    def upload_bytes(
        self,
        *,
        content: bytes,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        """Almacena contenido binario sin crear un archivo temporal.

        Args:
            content: Bytes que deben persistirse.
            object_name: Identificador lógico del objeto.
            content_type: MIME type del contenido, cuando esté disponible.

        Raises:
            ObjectStorageError: Si el proveedor no permite almacenar
                el objeto.
        """
        ...

    def download_file(
        self,
        object_name: str,
    ) -> bytes:
        """Recupera el contenido completo de un objeto.

        Args:
            object_name: Identificador del objeto almacenado.

        Returns:
            Contenido binario del objeto.

        Raises:
            ObjectStorageError: Si el proveedor no permite recuperar
                el objeto.
        """
        ...

    def delete_object(
        self,
        object_name: str,
    ) -> None:
        """Elimina un objeto almacenado.

        Args:
            object_name: Identificador del objeto.

        Raises:
            ObjectStorageError: Si el proveedor no permite eliminar
                el objeto.
        """
        ...
