"""Pruebas de integración del endpoint de documentos."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("manual.pdf", "application/pdf"),
        ("notas de clase.md", "text/markdown"),
        ("contenido.txt", "text/plain"),
    ],
)
def test_upload_valid_document(
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

    assert body["document_id"].startswith("doc_")
    assert body["filename"] == filename
    assert body["status"] == "validated"
    assert body["duplicate"] is False

    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert len(stored_files) == 1
    assert " " not in stored_files[0].name


def test_upload_rejects_unsupported_extension(
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


def test_upload_rejects_invalid_mime_type(
    client: TestClient,
    api_prefix: str,
) -> None:
    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "manual.pdf",
                b"contenido",
                "text/plain",
            )
        },
    )

    assert response.status_code == 415


def test_upload_rejects_empty_document(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
) -> None:
    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "vacio.txt",
                b"",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400

    if temporary_upload_directory.exists():
        assert list(
            temporary_upload_directory.iterdir()
        ) == []


def test_upload_rejects_document_over_size_limit(
    client: TestClient,
    api_prefix: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "MAX_UPLOAD_SIZE_MB",
        0,
    )

    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "contenido.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    assert response.status_code == 413


def test_duplicate_document_reuses_document_id(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
) -> None:
    first_response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "original.txt",
                b"mismo contenido",
                "text/plain",
            )
        },
    )

    second_response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "copia.txt",
                b"mismo contenido",
                "text/plain",
            )
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200

    first_body = first_response.json()
    second_body = second_response.json()

    assert (
        first_body["document_id"]
        == second_body["document_id"]
    )
    assert first_body["duplicate"] is False
    assert second_body["duplicate"] is True

    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert len(stored_files) == 1


def test_upload_requires_document(
    client: TestClient,
    api_prefix: str,
) -> None:
    response = client.post(
        f"{api_prefix}/documents"
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "file"