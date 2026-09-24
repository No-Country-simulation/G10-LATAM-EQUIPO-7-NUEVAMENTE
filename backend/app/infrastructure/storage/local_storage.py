"""Almacenamiento temporal de archivos en el sistema de archivos local."""

import re
import uuid
from collections.abc import AsyncIterable
from pathlib import Path

from app.ports.temporary_storage import (
    FileTooLargeError,
    TemporaryStoredFile,
)

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    """Genera un nombre seguro eliminando rutas y caracteres especiales."""
    basename = Path(filename or "archivo").name
    safe_name = _UNSAFE_CHARS.sub("_", basename).strip("._-")

    return safe_name or "archivo"


class LocalFileStorage:
    """Gestiona archivos temporales en el sistema de archivos local."""

    def __init__(
        self,
        base_directory: Path,
        max_size_bytes: int,
    ) -> None:
        if max_size_bytes < 0:
            raise ValueError("max_size_bytes no puede ser negativo.")

        self._base_directory = base_directory
        self._max_size_bytes = max_size_bytes

    async def save(
        self,
        *,
        original_filename: str,
        chunks: AsyncIterable[bytes],
    ) -> TemporaryStoredFile:
        """Guarda temporalmente un flujo de bytes.

        El contenido se escribe por bloques para evitar cargar el documento
        completo en memoria. Si ocurre un error durante la escritura, el
        archivo temporal incompleto se elimina.

        Args:
            original_filename: Nombre original recibido.
            chunks: Flujo asíncrono de bytes.

        Returns:
            Información del archivo temporal creado.

        Raises:
            FileTooLargeError: Si el archivo supera el límite configurado.
        """
        self._base_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_filename = sanitize_filename(original_filename)
        stored_filename = (
            f"{uuid.uuid4().hex}_{safe_filename}"
        )

        destination = (
            self._base_directory / stored_filename
        )

        size_bytes = 0
        completed = False

        try:
            with destination.open("wb") as buffer:
                async for chunk in chunks:
                    if not chunk:
                        continue

                    size_bytes += len(chunk)

                    if size_bytes > self._max_size_bytes:
                        raise FileTooLargeError(
                            original_filename
                        )

                    buffer.write(chunk)

            completed = True
        finally:
            if not completed:
                destination.unlink(
                    missing_ok=True
                )

        return TemporaryStoredFile(
            filename=stored_filename,
            path=destination,
            size_bytes=size_bytes,
        )