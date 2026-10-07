"""Pruebas de integración del listado de documentos de biblioteca."""

from fastapi.testclient import TestClient

from tests.fakes import (
    FakeAdaptationOrchestrationService,
)

_ADAPTATION_DATA = {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
    "learning_objective": (
        "Comprender los conceptos principales."
    ),
}


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


def test_list_documents_returns_processed_documents(
    client: TestClient,
    api_prefix: str,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Retorna documentos indexados disponibles en biblioteca."""
    first_upload = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
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
        data=_ADAPTATION_DATA,
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

    first_document_id = (
        first_upload.json()["document_id"]
    )

    second_document_id = (
        second_upload.json()["document_id"]
    )

    assert (
        fake_adaptation_orchestration_service
        .indexing_requests
        == [
            first_document_id,
            second_document_id,
        ]
    )

    assert len(
        fake_adaptation_orchestration_service
        .preparation_requests
    ) == 2

    prepared_document_ids = {
        request["document_id"]
        for request
        in (
            fake_adaptation_orchestration_service
            .preparation_requests
        )
    }

    assert prepared_document_ids == {
        first_document_id,
        second_document_id,
    }

    assert len(
        fake_adaptation_orchestration_service
        .completion_requests
    ) == 2

    assert all(
        len(completed_format_ids)
        == 2
        for completed_format_ids
        in (
            fake_adaptation_orchestration_service
            .completion_requests
        )
    )

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
        first_document_id,
        second_document_id,
    }

    for document in body["documents"]:
        assert (
            document["status"]
            == "indexed"
        )

        assert (
            document["content_type"]
            == "text/plain"
        )

        assert document["size_bytes"] > 0

        assert "filename" in document
        assert "created_at" in document
        assert "updated_at" in document

        # GET /documents continúa exponiendo únicamente
        # metadata de biblioteca.
        assert "title" not in document
        assert "summary" not in document
        assert "estimated_time" not in document
        assert "formats_status" not in document
        assert "formats" not in document
