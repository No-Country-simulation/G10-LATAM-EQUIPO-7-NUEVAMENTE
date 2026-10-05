"""Pruebas para las utilidades SHA-256."""

import hashlib

from app.core.hashing import (
    calculate_file_sha256,
    calculate_sha256,
)


def test_calculate_sha256() -> None:
    content = b"NuevaMente"

    expected = hashlib.sha256(content).hexdigest()

    assert calculate_sha256(content) == expected


def test_calculate_file_sha256(tmp_path) -> None:
    content = b"Documento de prueba NuevaMente"
    file_path = tmp_path / "documento.txt"
    file_path.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()

    assert calculate_file_sha256(file_path) == expected