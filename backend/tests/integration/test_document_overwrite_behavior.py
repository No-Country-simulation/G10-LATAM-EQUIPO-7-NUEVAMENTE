"""Pruebas de integración de deduplicación y no sobrescritura documental."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.fakes import FakeAdaptationOrchestrationService, FakeObjectStorage

_ADAPTATION_DATA = {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
    "learning_objective": (
        "Comprender los conceptos principales del documento."
    ),
}


def _upload_text_document(
    *,
    client: TestClient,
    api_prefix: str,
    filename: str,
    content: bytes,
):
    """Carga un TXT con el contexto pedagógico común de las pruebas."""
    return client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={"file": (filename, content, "text/plain")},
    )


def test_same_filename_with_different_content_creates_independent_documents(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """Mismo nombre con distinto SHA crea documentos y objetos independientes."""
    filename = "manual.txt"
    first_content = b"version original del documento"
    second_content = b"version actualizada con contenido diferente"

    first_response = _upload_text_document(
        client=client,
        api_prefix=api_prefix,
        filename=filename,
        content=first_content,
    )
    second_response = _upload_text_document(
        client=client,
        api_prefix=api_prefix,
        filename=filename,
        content=second_content,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_body = first_response.json()
    second_body = second_response.json()

    first_document_id = first_body["document_id"]
    second_document_id = second_body["document_id"]

    assert first_document_id != second_document_id
    assert first_body["filename"] == filename
    assert second_body["filename"] == filename
    assert first_body["duplicate"] is False
    assert second_body["duplicate"] is False
    assert first_body["status"] == "indexed"
    assert second_body["status"] == "indexed"

    first_object_name = (
        f"documents/{first_document_id}/original.txt"
    )
    second_object_name = (
        f"documents/{second_document_id}/original.txt"
    )

    assert first_object_name != second_object_name
    assert len(object_storage.uploaded_objects) == 2
    assert (
        object_storage.uploaded_objects[first_object_name]
        == first_content
    )
    assert (
        object_storage.uploaded_objects[second_object_name]
        == second_content
    )

    first_detail_response = client.get(
        f"{api_prefix}/documents/{first_document_id}"
    )
    second_detail_response = client.get(
        f"{api_prefix}/documents/{second_document_id}"
    )

    assert first_detail_response.status_code == 200
    assert second_detail_response.status_code == 200

    first_detail = first_detail_response.json()
    second_detail = second_detail_response.json()

    assert first_detail["document_id"] == first_document_id
    assert second_detail["document_id"] == second_document_id
    assert first_detail["filename"] == filename
    assert second_detail["filename"] == filename
    assert first_detail["size_bytes"] == len(first_content)
    assert second_detail["size_bytes"] == len(second_content)

    assert (
        fake_adaptation_orchestration_service.indexing_requests
        == [first_document_id, second_document_id]
    )
    assert [
        request["document_id"]
        for request
        in fake_adaptation_orchestration_service.preparation_requests
    ] == [first_document_id, second_document_id]
    assert len(
        fake_adaptation_orchestration_service.completion_requests
    ) == 2
    assert list(temporary_upload_directory.iterdir()) == []


def test_same_filename_and_same_content_reuses_existing_document(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """Mismo nombre y mismo SHA reutiliza el documento sin sobrescribir OCI."""
    filename = "manual.txt"
    content = b"contenido estable del documento"

    first_response = _upload_text_document(
        client=client,
        api_prefix=api_prefix,
        filename=filename,
        content=content,
    )
    second_response = _upload_text_document(
        client=client,
        api_prefix=api_prefix,
        filename=filename,
        content=content,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200

    first_body = first_response.json()
    second_body = second_response.json()

    document_id = first_body["document_id"]

    assert second_body["document_id"] == document_id
    assert first_body["duplicate"] is False
    assert second_body["duplicate"] is True
    assert first_body["filename"] == filename
    assert second_body["filename"] == filename
    assert first_body["status"] == "indexed"
    assert second_body["status"] == "indexed"

    expected_object_name = (
        f"documents/{document_id}/original.txt"
    )

    assert len(object_storage.uploaded_objects) == 1
    assert (
        object_storage.uploaded_objects[expected_object_name]
        == content
    )

    detail_response = client.get(
        f"{api_prefix}/documents/{document_id}"
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["document_id"] == document_id
    assert detail["filename"] == filename
    assert detail["size_bytes"] == len(content)

    assert (
        fake_adaptation_orchestration_service.indexing_requests
        == [document_id, document_id]
    )
    assert [
        request["document_id"]
        for request
        in fake_adaptation_orchestration_service.preparation_requests
    ] == [document_id, document_id]
    assert len(
        fake_adaptation_orchestration_service.completion_requests
    ) == 2
    assert list(temporary_upload_directory.iterdir()) == []
