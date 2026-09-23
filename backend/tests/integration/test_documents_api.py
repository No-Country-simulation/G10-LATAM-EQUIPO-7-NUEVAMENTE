"""Pruebas de integración del endpoint de documentos."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.fakes import FailingObjectStorage, FakeObjectStorage


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
    object_storage: FakeObjectStorage,
    filename: str,
    content_type: str,
) -> None:
    """Carga un documento válido y lo almacena de forma persistente."""
    file_content = b"contenido de prueba"

    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                filename,
                file_content,
                content_type,
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["document_id"].startswith("doc_")
    assert body["filename"] == filename
    assert body["status"] == "stored"
    assert body["duplicate"] is False

    # El archivo temporal debe eliminarse después del almacenamiento.
    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert stored_files == []

    # El archivo debe haberse enviado al Object Storage falso.
    assert len(object_storage.uploaded_objects) == 1

    extension = Path(filename).suffix.lower()

    expected_object_name = (
        f"documents/{body['document_id']}/"
        f"original{extension}"
    )

    assert (
        object_storage.uploaded_objects[
            expected_object_name
        ]
        == file_content
    )


def test_upload_rejects_unsupported_extension(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
) -> None:
    """Rechaza extensiones no permitidas antes de almacenar el archivo."""
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
    """Rechaza un MIME type incompatible con la extensión."""
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
    """Rechaza archivos vacíos y elimina cualquier temporal creado."""
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
    """Rechaza documentos que superan el tamaño máximo configurado."""
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


def test_upload_returns_502_when_object_storage_fails(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Devuelve 502 cuando falla el almacenamiento permanente."""
    client.app.state.object_storage = (
        FailingObjectStorage()
    )

    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "manual.txt",
                b"contenido para fallo",
                "text/plain",
            )
        },
    )

    assert response.status_code == 502

    assert (
        response.json()["detail"]
        == (
            "El documento fue registrado, pero no pudo "
            "almacenarse en OCI Object Storage."
        )
    )


def test_duplicate_document_reuses_document_id(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
) -> None:
    """Un duplicado reutiliza document_id y no se almacena dos veces."""
    file_content = b"mismo contenido"

    first_response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "original.txt",
                file_content,
                "text/plain",
            )
        },
    )

    second_response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "copia.txt",
                file_content,
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

    assert first_body["status"] == "stored"
    assert second_body["status"] == "stored"

    assert first_body["duplicate"] is False
    assert second_body["duplicate"] is True

    # Ninguna copia temporal debe permanecer después de los requests.
    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert stored_files == []

    # El mismo contenido solo debe existir una vez en Object Storage.
    assert len(object_storage.uploaded_objects) == 1

    expected_object_name = (
        f"documents/{first_body['document_id']}/"
        "original.txt"
    )

    assert (
        object_storage.uploaded_objects[
            expected_object_name
        ]
        == file_content
    )


def test_upload_requires_document(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Requiere que la petición incluya el campo file."""
    response = client.post(
        f"{api_prefix}/documents"
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "file"


def test_get_registered_document(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
) -> None:
    """Consulta la metadata de un documento almacenado."""
    file_content = b"contenido persistido"

    create_response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "manual.txt",
                file_content,
                "text/plain",
            )
        },
    )

    assert create_response.status_code == 201

    document_id = create_response.json()["document_id"]

    response = client.get(
        f"{api_prefix}/documents/{document_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["document_id"] == document_id
    assert body["filename"] == "manual.txt"
    assert body["status"] == "stored"
    assert body["content_type"] == "text/plain"
    assert body["size_bytes"] == len(file_content)
    assert "created_at" in body
    assert "updated_at" in body

    # El documento debe existir en el almacenamiento persistente falso.
    expected_object_name = (
        f"documents/{document_id}/original.txt"
    )

    assert (
        object_storage.uploaded_objects[
            expected_object_name
        ]
        == file_content
    )

    # El temporal ya no debe existir.
    assert list(
        temporary_upload_directory.iterdir()
    ) == []


def test_get_unknown_document_returns_404(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Devuelve 404 al consultar un document_id inexistente."""
    response = client.get(
        f"{api_prefix}/documents/doc_inexistente"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "No existe el documento doc_inexistente."
    )