"""Contrato para almacenamiento temporal de archivos."""

from collections.abc import AsyncIterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class FileTooLargeError(Exception):
    """El archivo supera el tamaño máximo permitido."""


@dataclass(frozen=True, slots=True)
class TemporaryStoredFile:
    """Archivo almacenado temporalmente durante una carga.

    Attributes:
        filename: Nombre seguro utilizado para el archivo temporal.
        path: Ruta física temporal.
        size_bytes: Tamaño total almacenado en bytes.
    """

    filename: str
    path: Path
    size_bytes: int


class TemporaryStoragePort(Protocol):
    """Define el almacenamiento temporal requerido por BackendAPI."""

    async def save(
        self,
        *,
        original_filename: str,
        chunks: AsyncIterable[bytes],
    ) -> TemporaryStoredFile:
        """Almacena temporalmente un flujo de bytes.

        Args:
            original_filename: Nombre original recibido desde el cliente.
            chunks: Flujo asíncrono del contenido del archivo.

        Returns:
            Información del archivo temporal creado.

        Raises:
            FileTooLargeError: Si el contenido supera el límite configurado.
        """
        ...