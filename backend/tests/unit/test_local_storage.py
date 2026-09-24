"""Pruebas de almacenamiento local temporal."""

import asyncio
from collections.abc import AsyncIterator

from app.infrastructure.storage.local_storage import (
    LocalFileStorage,
    sanitize_filename,
)


def test_sanitize_filename() -> None:
    assert sanitize_filename("notas de prueba.txt") == "notas_de_prueba.txt"


def test_local_storage_saves_file(tmp_path) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b"Nueva"
        yield b"Mente"

    storage = LocalFileStorage(
        base_directory=tmp_path,
        max_size_bytes=1024,
    )

    stored_file = asyncio.run(
        storage.save(
            original_filename="documento.txt",
            chunks=chunks(),
        )
    )

    assert stored_file.size_bytes == len(b"NuevaMente")
    assert stored_file.path.read_bytes() == b"NuevaMente"