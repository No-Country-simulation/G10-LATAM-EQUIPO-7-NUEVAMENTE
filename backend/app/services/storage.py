"""Compatibilidad temporal para el endpoint legacy de carga de archivos.

Este módulo será retirado cuando `/files/upload` sea sustituido por
`/documents`.
"""

from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.infrastructure.storage.local_storage import (
    FileTooLargeError as FileTooLargeError,
)
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.schemas.file import UploadedFile

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


async def _read_chunks(file: UploadFile) -> AsyncIterator[bytes]:
    """Lee un UploadFile por bloques para evitar cargarlo completo en memoria."""
    while chunk := await file.read(_CHUNK_SIZE):
        yield chunk


async def save_upload(file: UploadFile) -> UploadedFile:
    """Adapta el endpoint legacy al nuevo almacenamiento local."""
    original_filename = file.filename or "archivo"
    content_type = file.content_type

    storage = LocalFileStorage(
        base_directory=Path(settings.UPLOAD_DIR),
        max_size_bytes=settings.max_upload_size_bytes,
    )

    try:
        stored_file = await storage.save(
            original_filename=original_filename,
            chunks=_read_chunks(file),
        )
    finally:
        await file.close()

    return UploadedFile(
        filename=stored_file.filename,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=stored_file.size_bytes,
        path=str(stored_file.path),
    )