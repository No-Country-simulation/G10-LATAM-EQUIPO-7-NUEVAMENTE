"""Pruebas de integración de inactivación lógica y reactivación de documentos."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.error_codes import ErrorCode
from app.domain.enums import DocumentStatus
from tests.fakes import (
    FakeAdaptationOrchestrationService,
    FakeObjectStorage,
)

_ADAPTATION_DATA = {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
    "learning_objective": (
        "Comprender la inactivación y reactivación lógica de documentos."
    ),
}


def _upload_test_document(
    client: TestClient,
    api_prefix: str,
    filename: str = "manual.txt",
    content: bytes = b"Contenido de prueba para inactivacion",
):
    """Carga un documento de prueba."""
    return client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={"file": (filename, content, "text/plain")},
    )


def test_deactivate_existing_document_leaves_inactive_and_preserves_attributes(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """PATCH /deactivate marca is_active = False sin modificar status, OCI ni metadata."""
    upload_res = _upload_test_document(
        client,
        api_prefix,
        "documento_a_inactivar.txt",
        b"contenido permanente",
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # Consulta estado antes de inactivar
    doc_before = client.app.state.document_service.get_document(doc_id)
    assert doc_before.is_active is True
    assert doc_before.status == DocumentStatus.INDEXED
    oci_object_name_before = doc_before.oci_object_name
    assert oci_object_name_before is not None

    # Inactivación
    response = client.patch(
        f"{api_prefix}/documents/{doc_id}/deactivate"
    )
    assert response.status_code == 204
    assert response.text == ""

    # Verifica entidad y persistencia
    doc_after = client.app.state.document_service.get_document(doc_id)
    assert doc_after.is_active is False
    assert doc_after.status == DocumentStatus.INDEXED
    assert doc_after.oci_object_name == oci_object_name_before
    assert doc_after.original_filename == "documento_a_inactivar.txt"


def test_deactivate_document_is_idempotent(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """Repetir PATCH /deactivate en un documento ya inactivo es idempotente."""
    upload_res = _upload_test_document(
        client,
        api_prefix,
        "idempotente.txt",
        b"contenido idempotente",
    )
    doc_id = upload_res.json()["document_id"]

    # Primera inactivación
    res1 = client.patch(f"{api_prefix}/documents/{doc_id}/deactivate")
    assert res1.status_code == 204

    # Segunda inactivación repetida
    res2 = client.patch(f"{api_prefix}/documents/{doc_id}/deactivate")
    assert res2.status_code == 204

    # Tercera inactivación repetida
    res3 = client.patch(f"{api_prefix}/documents/{doc_id}/deactivate")
    assert res3.status_code == 204

    doc = client.app.state.document_service.get_document(doc_id)
    assert doc.is_active is False


def test_deactivate_non_existent_document_returns_404(
    client: TestClient,
    api_prefix: str,
) -> None:
    """PATCH /deactivate con document_id inexistente devuelve 404 DOCUMENT_NOT_FOUND."""
    response = client.patch(
        f"{api_prefix}/documents/doc_inexistente_123/deactivate"
    )
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == ErrorCode.DOCUMENT_NOT_FOUND
    assert "doc_inexistente_123" in body["detail"]


def test_list_documents_excludes_inactive_documents(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """GET /api/v1/documents devuelve únicamente documentos activos."""
    res1 = _upload_test_document(
        client, api_prefix, "activo.txt", b"doc activo"
    )
    res2 = _upload_test_document(
        client, api_prefix, "a_inactivar.txt", b"doc a inactivar"
    )

    doc_id1 = res1.json()["document_id"]
    doc_id2 = res2.json()["document_id"]

    # Antes de inactivar, ambos aparecen
    list_res = client.get(f"{api_prefix}/documents")
    assert list_res.status_code == 200
    listed_ids = [d["document_id"] for d in list_res.json()["documents"]]
    assert doc_id1 in listed_ids
    assert doc_id2 in listed_ids

    # Inactivar doc2
    deact_res = client.patch(f"{api_prefix}/documents/{doc_id2}/deactivate")
    assert deact_res.status_code == 204

    # Ahora solo aparece doc1
    list_res_after = client.get(f"{api_prefix}/documents")
    assert list_res_after.status_code == 200
    listed_ids_after = [d["document_id"] for d in list_res_after.json()["documents"]]
    assert doc_id1 in listed_ids_after
    assert doc_id2 not in listed_ids_after


def test_reupload_inactive_document_reactivates_it(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """Re-subir un documento inactivo lo reactiva y reutiliza su document_id."""
    content = b"archivo unico para reactivacion por re-subida"
    upload1 = _upload_test_document(client, api_prefix, "archivo.txt", content)
    assert upload1.status_code == 201
    doc_id = upload1.json()["document_id"]
    assert upload1.json()["duplicate"] is False

    # Inactivamos el documento
    deact_res = client.patch(f"{api_prefix}/documents/{doc_id}/deactivate")
    assert deact_res.status_code == 204

    # Confirmamos que no figura en la biblioteca
    list_res = client.get(f"{api_prefix}/documents")
    assert doc_id not in [d["document_id"] for d in list_res.json()["documents"]]

    # Re-subimos exactamente el mismo contenido
    upload2 = _upload_test_document(client, api_prefix, "archivo.txt", content)
    assert upload2.status_code == 200

    body2 = upload2.json()
    assert body2["document_id"] == doc_id
    assert body2["duplicate"] is True
    assert body2["status"] == "indexed"

    # Verificamos que el documento quedó activo en persistencia
    doc = client.app.state.document_service.get_document(doc_id)
    assert doc.is_active is True
    assert doc.status == DocumentStatus.INDEXED

    # Verificamos que volvió a figurar en la biblioteca
    list_res_after = client.get(f"{api_prefix}/documents")
    assert doc_id in [d["document_id"] for d in list_res_after.json()["documents"]]

    # Confirmamos que no se duplicó el objeto en Object Storage
    expected_oci_key = f"documents/{doc_id}/original.txt"
    assert expected_oci_key in object_storage.uploaded_objects


def test_reupload_already_active_duplicate_maintains_behavior(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """Re-subir un documento que ya estaba activo mantiene el comportamiento previo de duplicado."""
    content = b"archivo ya activo"
    upload1 = _upload_test_document(client, api_prefix, "activo.txt", content)
    assert upload1.status_code == 201
    doc_id = upload1.json()["document_id"]

    upload2 = _upload_test_document(client, api_prefix, "activo.txt", content)
    assert upload2.status_code == 200
    assert upload2.json()["document_id"] == doc_id
    assert upload2.json()["duplicate"] is True

    doc = client.app.state.document_service.get_document(doc_id)
    assert doc.is_active is True


def test_non_regression_operations_not_blocked_for_inactive_document(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: FakeAdaptationOrchestrationService,
) -> None:
    """Consultas individuales, formatos y descarga NO deben bloquearse para documentos inactivos."""
    content = b"contenido legible y descargable"
    upload = _upload_test_document(client, api_prefix, "consulta.txt", content)
    doc_id = upload.json()["document_id"]

    # Inactivar
    client.patch(f"{api_prefix}/documents/{doc_id}/deactivate")

    # 1. Consulta individual sigue funcionando
    detail_res = client.get(f"{api_prefix}/documents/{doc_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["document_id"] == doc_id

    # 2. Descarga de documento original sigue funcionando
    download_res = client.get(f"{api_prefix}/documents/{doc_id}/download")
    assert download_res.status_code == 200
    assert download_res.content == content

    # 3. Consulta de formatos generados sigue funcionando
    formats_res = client.get(f"{api_prefix}/documents/{doc_id}/formats")
    assert formats_res.status_code == 200
    assert formats_res.json()["document_id"] == doc_id
