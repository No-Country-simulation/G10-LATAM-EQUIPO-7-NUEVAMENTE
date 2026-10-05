"""Utilidades para generar identificadores SHA-256."""

import hashlib
from pathlib import Path

_DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def calculate_sha256(content: bytes) -> str:
    """Calcula el SHA-256 de un contenido en memoria.

    Args:
        content: Contenido binario sobre el cual calcular el hash.

    Returns:
        Representación hexadecimal SHA-256 de 64 caracteres.
    """
    return hashlib.sha256(content).hexdigest()


def calculate_file_sha256(
    file_path: Path,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> str:
    """Calcula el SHA-256 de un archivo sin cargarlo completamente en memoria.

    Args:
        file_path: Ruta del archivo.
        chunk_size: Cantidad de bytes leídos en cada iteración.

    Returns:
        Representación hexadecimal SHA-256 del archivo.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        OSError: Si ocurre un error durante la lectura.
    """
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()