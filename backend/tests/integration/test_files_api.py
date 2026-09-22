"""Pruebas de integración del endpoint legacy de archivos."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture
def temporary_upload_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Redirige el almacenamiento legacy a un directorio temporal."""
    upload_directory = tmp_path / "uploads"

    monkeypatch.setattr(
        settings,
        "UPLOAD_DIR",
        str(upload_directory),
    )

    return upload_directory


def test_upload_file(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
) -> None:
    response = client.post(
        f"{api_prefix}/files/upload",
        files={
            "file": (
                "notas de prueba.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["original_filename"] == "notas de prueba.txt"
    assert body["size_bytes"] == len(b"contenido")
    assert " " not in body["filename"]

    stored_path = Path(body["path"])

    assert stored_path.exists()
    assert stored_path.parent == temporary_upload_directory


def test_upload_requires_file(
    client: TestClient,
    api_prefix: str,
) -> None:
    response = client.post(
        f"{api_prefix}/files/upload"
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "file"