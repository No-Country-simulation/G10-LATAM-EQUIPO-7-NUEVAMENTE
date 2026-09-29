"""Pruebas de integración del listado de documentos de biblioteca."""

from fastapi.testclient import TestClient


def test_list_documents_returns_empty_library(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Una biblioteca sin documentos retorna una colección vacía."""
    response = client.get(
        f"{api_prefix}/documents"
    )

    assert response.status_code == 200
    assert response.json() == {
        "documents": [],
    }


def test_list_documents_returns_stored_documents(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Retorna documentos almacenados disponibles en biblioteca."""
    first_upload = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "arquitectura.txt",
                b"contenido de arquitectura",
                "text/plain",
            )
        },
    )

    second_upload = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "patrones.txt",
                b"contenido de patrones",
                "text/plain",
            )
        },
    )

    assert first_upload.status_code == 201
    assert second_upload.status_code == 201

    response = client.get(
        f"{api_prefix}/documents"
    )

    assert response.status_code == 200

    body = response.json()

    assert len(
        body["documents"]
    ) == 2

    returned_ids = {
        document["document_id"]
        for document
        in body["documents"]
    }

    assert returned_ids == {
        first_upload.json()["document_id"],
        second_upload.json()["document_id"],
    }

    for document in body["documents"]:
        assert document["status"] == "stored"
        assert document["content_type"] == "text/plain"
        assert document["size_bytes"] > 0
        assert "filename" in document
        assert "created_at" in document
        assert "updated_at" in document