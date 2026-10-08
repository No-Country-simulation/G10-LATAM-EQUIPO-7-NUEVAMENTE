"""Pruebas de integración del endpoint de documentos."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.fakes import (
    FailingObjectStorage,
    FakeAdaptationOrchestrationService,
    FakeObjectStorage,
)

_ADAPTATION_DATA = {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
    "learning_objective": (
        "Comprender los conceptos principales del documento."
    ),
}

_CURRENT_FORMATS = {
    "quiz",
    "flashcards",
    "tldr",
    "video_script",
}


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
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
    filename: str,
    content_type: str,
) -> None:
    """Almacena, indexa y genera los cuatro formatos por etapas."""
    file_content = b"contenido de prueba"

    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
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

    assert body["document_id"].startswith(
        "doc_"
    )
    assert body["filename"] == filename
    assert body["status"] == "indexed"
    assert body["duplicate"] is False
    assert "formats" not in body

    document_id = body["document_id"]

    assert (
        fake_adaptation_orchestration_service
        .indexing_requests
        == [
            document_id
        ]
    )

    assert (
        fake_adaptation_orchestration_service
        .preparation_requests
        == [
            {
                "document_id": document_id,
                "profile": "intermediate",
                "niche": "backend",
                "detail_level": "detailed",
                "learning_objective": (
                    "Comprender los conceptos "
                    "principales del documento."
                ),
            }
        ]
    )

    assert len(
        fake_adaptation_orchestration_service
        .completion_requests
    ) == 1

    completed_format_ids = (
        fake_adaptation_orchestration_service
        .completion_requests[0]
    )

    assert len(
        completed_format_ids
    ) == 4

    formats_response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert (
        formats_response.status_code
        == 200
    )

    formats_body = (
        formats_response.json()
    )

    assert (
        formats_body["status"]
        == "ready"
    )

    assert set(
        formats_body["formats"]
    ) == _CURRENT_FORMATS

    assert all(
        format_response["status"]
        == "success"
        for format_response
        in formats_body["formats"].values()
    )

    returned_format_ids = {
        format_response[
            "format_id"
        ]
        for format_response
        in formats_body["formats"].values()
    }

    assert (
        returned_format_ids
        == set(
            completed_format_ids
        )
    )

    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert stored_files == []

    assert len(
        object_storage.uploaded_objects
    ) == 1

    extension = Path(
        filename
    ).suffix.lower()

    expected_object_name = (
        f"documents/{document_id}/"
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
        data=_ADAPTATION_DATA,
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
        data=_ADAPTATION_DATA,
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
        data=_ADAPTATION_DATA,
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
        data=_ADAPTATION_DATA,
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
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Devuelve 502 cuando falla el almacenamiento permanente."""
    client.app.state.object_storage = (
        FailingObjectStorage()
    )

    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
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

    assert (
        fake_adaptation_orchestration_service
        .indexing_requests
        == []
    )

    assert (
        fake_adaptation_orchestration_service
        .preparation_requests
        == []
    )

    assert (
        fake_adaptation_orchestration_service
        .completion_requests
        == []
    )


def test_duplicate_document_reuses_document_id(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Un duplicado reutiliza document_id sin volver a almacenarse."""
    file_content = b"mismo contenido"

    first_response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
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
        data=_ADAPTATION_DATA,
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

    assert first_body["status"] == "indexed"
    assert second_body["status"] == "indexed"

    assert first_body["duplicate"] is False
    assert second_body["duplicate"] is True

    assert "formats" not in first_body
    assert "formats" not in second_body

    document_id = (
        first_body["document_id"]
    )

    assert (
        fake_adaptation_orchestration_service
        .indexing_requests
        == [
            document_id,
            document_id,
        ]
    )

    assert len(
        fake_adaptation_orchestration_service
        .preparation_requests
    ) == 2

    assert all(
        request["document_id"]
        == document_id
        for request
        in (
            fake_adaptation_orchestration_service
            .preparation_requests
        )
    )

    assert len(
        fake_adaptation_orchestration_service
        .completion_requests
    ) == 2

    assert all(
        len(completed_format_ids)
        == 4
        for completed_format_ids
        in (
            fake_adaptation_orchestration_service
            .completion_requests
        )
    )

    formats_response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert (
        formats_response.status_code
        == 200
    )

    formats_body = (
        formats_response.json()
    )

    assert (
        formats_body["status"]
        == "ready"
    )

    assert set(
        formats_body["formats"]
    ) == _CURRENT_FORMATS

    stored_files = list(
        temporary_upload_directory.iterdir()
    )

    assert stored_files == []

    assert len(
        object_storage.uploaded_objects
    ) == 1

    expected_object_name = (
        f"documents/{document_id}/"
        "original.txt"
    )

    assert (
        object_storage.uploaded_objects[
            expected_object_name
        ]
        == file_content
    )


def test_upload_requires_document_and_pedagogical_context(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Requiere archivo y parámetros pedagógicos obligatorios."""
    response = client.post(
        f"{api_prefix}/documents"
    )

    assert response.status_code == 422

    error_fields = {
        error["field"]
        for error in response.json()["errors"]
    }

    assert {
        "file",
        "profile",
        "niche",
        "detail_level",
    }.issubset(
        error_fields
    )


def test_upload_requires_pedagogical_context(
    client: TestClient,
    api_prefix: str,
) -> None:
    """No procesa un archivo sin el contexto pedagógico requerido."""
    response = client.post(
        f"{api_prefix}/documents",
        files={
            "file": (
                "manual.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422

    error_fields = {
        error["field"]
        for error in response.json()["errors"]
    }

    assert {
        "profile",
        "niche",
        "detail_level",
    }.issubset(
        error_fields
    )


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("profile", "expert"),
        ("niche", "unknown"),
        ("detail_level", "   "),
    ],
)
def test_upload_rejects_invalid_pedagogical_context(
    client: TestClient,
    api_prefix: str,
    field: str,
    invalid_value: str,
) -> None:
    """Valida el contexto pedagógico antes de ejecutar el flujo."""
    data = {
        **_ADAPTATION_DATA,
        field: invalid_value,
    }

    response = client.post(
        f"{api_prefix}/documents",
        data=data,
        files={
            "file": (
                "manual.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422


def test_get_registered_document(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Consulta la metadata pública de un documento indexado."""
    file_content = b"contenido persistido"

    create_response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={
            "file": (
                "manual.txt",
                file_content,
                "text/plain",
            )
        },
    )

    assert create_response.status_code == 201

    document_id = (
        create_response.json()["document_id"]
    )

    assert (
        fake_adaptation_orchestration_service
        .indexing_requests
        == [
            document_id
        ]
    )

    assert len(
        fake_adaptation_orchestration_service
        .preparation_requests
    ) == 1

    assert len(
        fake_adaptation_orchestration_service
        .completion_requests
    ) == 1

    response = client.get(
        f"{api_prefix}/documents/{document_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["document_id"] == document_id
    assert body["filename"] == "manual.txt"
    assert body["status"] == "indexed"
    assert body["content_type"] == "text/plain"
    assert (
        body["size_bytes"]
        == len(file_content)
    )

    assert "created_at" in body
    assert "updated_at" in body

    assert body["title"] is None
    assert body["summary"] is None
    assert body["learning_metadata"] is None
    assert "estimated_time" not in body

    assert "formats_status" not in body
    assert "formats" not in body

    expected_object_name = (
        f"documents/{document_id}/original.txt"
    )

    assert (
        object_storage.uploaded_objects[
            expected_object_name
        ]
        == file_content
    )

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


def test_adaptations_endpoint_is_not_public(
    client: TestClient,
    api_prefix: str,
) -> None:
    """La adaptación continúa siendo un caso de uso interno."""
    response = client.post(
        f"{api_prefix}/adaptations",
        json={
            "document_id": "doc_123",
            "profile": "intermediate",
            "niche": "backend",
            "detail_level": "detailed",
        },
    )

    assert response.status_code == 404
