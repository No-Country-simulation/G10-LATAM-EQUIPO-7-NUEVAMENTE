"""Pruebas de integración del endpoint de carga de documentos."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("manual.pdf", "application/pdf"),
        ("notas.md", "text/markdown"),
        ("contenido.txt", "text/plain"),
    ],
)
def test_upload_supported_document(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    filename: str,
    content_type: str,
) -> None:
    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                filename,
                b"contenido de prueba",
                content_type,
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["original_filename"] == filename
    assert body["content_type"] == content_type
    assert body["size_bytes"] == len(b"contenido de prueba")
    assert body["filename"]

    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == b"contenido de prueba"


def test_upload_rejects_unsupported_document(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
) -> None:
    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "imagen.jpg",
                b"contenido",
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 415
    assert not temporary_upload_directory.exists()


def test_upload_requires_document(
    client: TestClient,
    api_prefix: str,
) -> None:
    response = client.post(
        f"{api_prefix}/documents"
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "file"