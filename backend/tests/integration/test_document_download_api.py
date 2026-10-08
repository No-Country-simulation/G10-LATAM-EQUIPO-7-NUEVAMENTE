"""Pruebas de integración para la descarga del documento original."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.application.document_service import (
    DocumentService,
)
from tests.fakes import (
    FailingDownloadObjectStorage,
    FakeAdaptationOrchestrationService,
    FakeObjectStorage,
)

_ADAPTATION_DATA = {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
    "learning_objective": (
        "Comprender el contenido del documento."
    ),
}


def _upload_document(
    *,
    client: TestClient,
    api_prefix: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> str:
    """Carga un documento y retorna el document_id creado."""
    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={
            "file": (
                filename,
                content,
                content_type,
            )
        },
    )

    assert response.status_code == 201

    return response.json()["document_id"]


def test_download_original_document_from_object_storage(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Retorna exactamente los bytes originales almacenados."""
    original_content = (
        b"%PDF-1.7\ncontenido binario de prueba"
    )

    document_id = _upload_document(
        client=client,
        api_prefix=api_prefix,
        filename="manual.pdf",
        content=original_content,
        content_type="application/pdf",
    )

    response = client.get(
        f"{api_prefix}/documents/{document_id}/download"
    )

    assert response.status_code == 200
    assert response.content == original_content
    assert (
        response.headers["content-type"]
        == "application/pdf"
    )
    assert (
        response.headers["content-disposition"]
        == (
            'attachment; filename="manual.pdf"; '
            "filename*=UTF-8''manual.pdf"
        )
    )


def test_download_preserves_utf8_filename(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Expone filename* RFC 5987 para nombres no ASCII."""
    document_id = _upload_document(
        client=client,
        api_prefix=api_prefix,
        filename="guía técnica.txt",
        content=b"contenido con acentos",
        content_type="text/plain",
    )

    response = client.get(
        f"{api_prefix}/documents/{document_id}/download"
    )

    assert response.status_code == 200
    assert response.headers[
        "content-disposition"
    ] == (
        'attachment; filename="gua tcnica.txt"; '
        "filename*=UTF-8''"
        "gu%C3%ADa%20t%C3%A9cnica.txt"
    )
    assert response.headers[
        "content-type"
    ].startswith(
        "text/plain"
    )


def test_download_exposes_content_disposition_through_cors(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Permite que Frontend lea el nombre original en contexto CORS."""
    document_id = _upload_document(
        client=client,
        api_prefix=api_prefix,
        filename="manual.md",
        content=b"# Documento",
        content_type="text/markdown",
    )

    response = client.get(
        f"{api_prefix}/documents/{document_id}/download",
        headers={
            "Origin": "http://localhost:3000",
        },
    )

    assert response.status_code == 200

    exposed_headers = response.headers.get(
        "access-control-expose-headers",
        "",
    )

    assert (
        "Content-Disposition"
        in exposed_headers
    )


def test_download_unknown_document_returns_404(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Devuelve el contrato de error para document_id inexistente."""
    response = client.get(
        f"{api_prefix}/documents/doc_inexistente/download"
    )

    assert response.status_code == 404

    body = response.json()

    assert body["code"] == "DOCUMENT_NOT_FOUND"
    assert (
        body["detail"]
        == "No existe el documento doc_inexistente."
    )
    assert body["errors"] == []
    assert "timestamp" in body


def test_download_document_without_object_returns_409(
    client: TestClient,
    api_prefix: str,
    tmp_path: Path,
) -> None:
    """Un documento registrado sin objeto OCI no puede descargarse."""
    document_service: DocumentService = (
        client.app.state.document_service
    )

    file_path = tmp_path / "pendiente.txt"
    file_path.write_bytes(
        b"contenido registrado pero no almacenado"
    )

    registration = (
        document_service.register_document(
            local_path=file_path,
            original_filename="pendiente.txt",
            content_type="text/plain",
            size_bytes=file_path.stat().st_size,
        )
    )

    document_id = (
        registration.document.document_id
    )

    response = client.get(
        f"{api_prefix}/documents/{document_id}/download"
    )

    assert response.status_code == 409

    body = response.json()

    assert (
        body["code"]
        == "DOCUMENT_STATE_CONFLICT"
    )
    assert "no tiene un objeto almacenado" in body["detail"]


def test_download_object_storage_failure_returns_502(
    client: TestClient,
    api_prefix: str,
    temporary_upload_directory: Path,
    object_storage: FakeObjectStorage,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """Traduce el fallo de OCI al contrato público de recuperación."""
    document_id = _upload_document(
        client=client,
        api_prefix=api_prefix,
        filename="manual.txt",
        content=b"contenido",
        content_type="text/plain",
    )

    client.app.state.object_storage = (
        FailingDownloadObjectStorage()
    )

    response = client.get(
        f"{api_prefix}/documents/{document_id}/download"
    )

    assert response.status_code == 502

    body = response.json()

    assert (
        body["code"]
        == "DOCUMENT_RETRIEVAL_FAILED"
    )
    assert body["detail"] == (
        "No fue posible recuperar el archivo original "
        "desde OCI Object Storage."
    )
    assert body["errors"] == []
    assert "timestamp" in body
