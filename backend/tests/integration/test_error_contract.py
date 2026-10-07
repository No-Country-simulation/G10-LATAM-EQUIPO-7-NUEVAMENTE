"""Pruebas del contrato transversal de errores expuesto a Frontend."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.application.adaptation_orchestration_service import (
    AdaptationDocumentStateError,
)
from app.application.document_service import (
    DocumentRetrievalError,
)
from app.application.rag_integration_service import (
    RAGIntegrationError,
)
from app.core.config import settings
from app.domain.document import Document
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
    GenerationContext,
)
from app.infrastructure.persistence.repository_factory import (
    create_document_repository,
    create_generated_format_repository,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
)
from tests.fakes import FailingObjectStorage

_ADAPTATION_DATA = {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
}


class RAGFailureOrchestration:
    """Simula un fallo RAG durante la etapa síncrona de indexación."""

    async def ensure_document_indexed(
        self,
        document_id: str,
    ) -> None:
        raise RAGIntegrationError(
            f"No fue posible indexar {document_id}."
        )


class RetrievalFailureOrchestration:
    """Simula un fallo recuperando el documento antes de indexarlo."""

    async def ensure_document_indexed(
        self,
        document_id: str,
    ) -> None:
        raise DocumentRetrievalError(
            f"No fue posible recuperar {document_id}."
        )


class StateConflictOrchestration:
    """Simula un documento en estado incompatible con indexación."""

    async def ensure_document_indexed(
        self,
        document_id: str,
    ) -> None:
        raise AdaptationDocumentStateError(
            f"El documento {document_id} no puede indexarse."
        )


class FormatRegistrationFailureOrchestration:
    """Indexa correctamente, pero falla al registrar formatos."""

    async def ensure_document_indexed(
        self,
        document_id: str,
    ) -> None:
        return None

    def prepare_default_formats(
        self,
        **_: object,
    ) -> list[GeneratedFormat]:
        raise GeneratedFormatRepositoryError(
            "Fallo simulado al registrar formatos."
        )


class FailingRegenerationService:
    """Simula un fallo al registrar intentos de regeneración."""

    def prepare_regeneration(
        self,
        *,
        document_id: str,
        formats: tuple[
            GeneratedFormatType,
            ...,
        ],
    ) -> list[GeneratedFormat]:
        raise GeneratedFormatRepositoryError(
            "Fallo simulado."
        )


def _persist_document(
    *,
    document_id: str,
    status: DocumentStatus,
) -> None:
    """Persiste un documento para escenarios de regeneración."""
    repository = create_document_repository(
        settings.DATABASE_URL
    )

    repository.create(
        Document(
            document_id=document_id,
            original_filename="manual.txt",
            sha256="a" * 64,
            content_type="text/plain",
            size_bytes=100,
            status=status,
            oci_object_name=(
                f"documents/{document_id}/original.txt"
            ),
        )
    )


def _persist_attempt(
    *,
    document_id: str,
    format_id: str,
    format_type: GeneratedFormatType,
    status: GeneratedFormatStatus,
    context: GenerationContext,
) -> None:
    """Persiste un intento previo con contexto pedagógico."""
    repository = (
        create_generated_format_repository(
            settings.DATABASE_URL
        )
    )

    repository.create(
        GeneratedFormat(
            format_id=format_id,
            document_id=document_id,
            format_type=format_type,
            status=status,
            generation_context=context,
            content=None,
            chunks_used=(),
            error_message=(
                None
                if (
                    status
                    == GeneratedFormatStatus.PROCESSING
                )
                else "Resultado previo."
            ),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )


def _assert_error_contract(
    response,
    *,
    expected_status: int,
    expected_code: str,
) -> dict[str, object]:
    """Verifica el envelope transversal sin acoplarse al timestamp."""
    assert response.status_code == expected_status

    body = response.json()

    assert body["code"] == expected_code
    assert isinstance(
        body["detail"],
        str,
    )
    assert isinstance(
        body["errors"],
        list,
    )
    assert isinstance(
        body["timestamp"],
        str,
    )

    return body


def test_validation_error_exposes_root_code_and_field_details(
    client: TestClient,
    api_prefix: str,
) -> None:
    """422 conserva el código raíz y los errores estructurados."""
    response = client.post(
        f"{api_prefix}/documents"
    )

    body = _assert_error_contract(
        response,
        expected_status=422,
        expected_code=(
            "REQUEST_VALIDATION_ERROR"
        ),
    )

    error_fields = {
        error["field"]
        for error in body["errors"]
    }

    assert {
        "file",
        "profile",
        "niche",
        "detail_level",
    }.issubset(
        error_fields
    )


@pytest.mark.parametrize(
    (
        "filename",
        "content_type",
        "expected_code",
    ),
    [
        (
            "imagen.jpg",
            "image/jpeg",
            "UNSUPPORTED_FILE_TYPE",
        ),
        (
            "manual.pdf",
            "text/plain",
            "MIME_TYPE_MISMATCH",
        ),
    ],
)
def test_upload_classifies_file_type_errors(
    client: TestClient,
    api_prefix: str,
    filename: str,
    content_type: str,
    expected_code: str,
) -> None:
    """Distingue extensión no soportada de MIME incompatible."""
    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={
            "file": (
                filename,
                b"contenido",
                content_type,
            )
        },
    )

    _assert_error_contract(
        response,
        expected_status=415,
        expected_code=expected_code,
    )


def test_upload_classifies_empty_document(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Identifica explícitamente un documento vacío."""
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

    _assert_error_contract(
        response,
        expected_status=400,
        expected_code="DOCUMENT_EMPTY",
    )


def test_upload_classifies_file_too_large(
    client: TestClient,
    api_prefix: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expone FILE_TOO_LARGE para el límite de staging."""
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
                "manual.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    _assert_error_contract(
        response,
        expected_status=413,
        expected_code="FILE_TOO_LARGE",
    )


def test_upload_distinguishes_object_storage_failure(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Un 502 de OCI no se confunde con un fallo de RAG."""
    client.app.state.object_storage = (
        FailingObjectStorage()
    )

    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={
            "file": (
                "manual.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    _assert_error_contract(
        response,
        expected_status=502,
        expected_code=(
            "DOCUMENT_STORAGE_FAILED"
        ),
    )


@pytest.mark.parametrize(
    (
        "service",
        "expected_status",
        "expected_code",
    ),
    [
        (
            RAGFailureOrchestration(),
            502,
            "RAG_INDEXING_FAILED",
        ),
        (
            RetrievalFailureOrchestration(),
            502,
            "DOCUMENT_RETRIEVAL_FAILED",
        ),
        (
            StateConflictOrchestration(),
            409,
            "DOCUMENT_STATE_CONFLICT",
        ),
    ],
)
def test_upload_classifies_indexing_failures(
    client: TestClient,
    api_prefix: str,
    service: object,
    expected_status: int,
    expected_code: str,
) -> None:
    """Distingue causas que antes compartían 409/502."""
    client.app.state.adaptation_orchestration_service = (
        service
    )

    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={
            "file": (
                "manual.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    _assert_error_contract(
        response,
        expected_status=expected_status,
        expected_code=expected_code,
    )


def test_upload_classifies_format_registration_failure(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Un documento indexado distingue el fallo al registrar formatos."""
    client.app.state.adaptation_orchestration_service = (
        FormatRegistrationFailureOrchestration()
    )

    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={
            "file": (
                "manual.txt",
                b"contenido",
                "text/plain",
            )
        },
    )

    _assert_error_contract(
        response,
        expected_status=500,
        expected_code=(
            "FORMAT_REGISTRATION_FAILED"
        ),
    )


@pytest.mark.parametrize(
    "path",
    [
        "/documents/doc_missing",
        "/documents/doc_missing/formats",
    ],
)
def test_document_queries_expose_not_found_code(
    client: TestClient,
    api_prefix: str,
    path: str,
) -> None:
    """Las consultas de documento usan DOCUMENT_NOT_FOUND."""
    response = client.get(
        f"{api_prefix}{path}"
    )

    _assert_error_contract(
        response,
        expected_status=404,
        expected_code="DOCUMENT_NOT_FOUND",
    )


def test_regeneration_exposes_document_not_found_code(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Regeneración diferencia documento inexistente."""
    response = client.post(
        f"{api_prefix}/documents/"
        "doc_missing/formats/regenerate",
        json={
            "formats": [
                "quiz"
            ]
        },
    )

    _assert_error_contract(
        response,
        expected_status=404,
        expected_code="DOCUMENT_NOT_FOUND",
    )


def test_regeneration_exposes_not_indexed_code(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Regeneración diferencia documento todavía no indexado."""
    document_id = "doc_not_indexed"

    _persist_document(
        document_id=document_id,
        status=DocumentStatus.STORED,
    )

    response = client.post(
        f"{api_prefix}/documents/"
        f"{document_id}/formats/regenerate",
        json={
            "formats": [
                "quiz"
            ]
        },
    )

    _assert_error_contract(
        response,
        expected_status=409,
        expected_code="DOCUMENT_NOT_INDEXED",
    )


def test_regeneration_exposes_processing_conflict_code(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Regeneración activa tiene un código accionable por Frontend."""
    document_id = "doc_processing"

    _persist_document(
        document_id=document_id,
        status=DocumentStatus.INDEXED,
    )

    context = GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
    )

    _persist_attempt(
        document_id=document_id,
        format_id="fmt_processing",
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.PROCESSING,
        context=context,
    )

    response = client.post(
        f"{api_prefix}/documents/"
        f"{document_id}/formats/regenerate",
        json={
            "formats": [
                "quiz"
            ]
        },
    )

    _assert_error_contract(
        response,
        expected_status=409,
        expected_code=(
            "FORMAT_REGENERATION_IN_PROGRESS"
        ),
    )


def test_regeneration_exposes_missing_context_code(
    client: TestClient,
    api_prefix: str,
) -> None:
    """No inventa contexto cuando nunca hubo generación previa."""
    document_id = "doc_without_context"

    _persist_document(
        document_id=document_id,
        status=DocumentStatus.INDEXED,
    )

    response = client.post(
        f"{api_prefix}/documents/"
        f"{document_id}/formats/regenerate",
        json={
            "formats": [
                "quiz"
            ]
        },
    )

    _assert_error_contract(
        response,
        expected_status=409,
        expected_code="FORMAT_CONTEXT_NOT_FOUND",
    )


def test_regeneration_exposes_context_conflict_code(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Distingue contextos pedagógicos incompatibles."""
    document_id = "doc_context_conflict"

    _persist_document(
        document_id=document_id,
        status=DocumentStatus.INDEXED,
    )

    quiz_context = GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
    )
    flashcards_context = GenerationContext(
        profile="advanced",
        niche="backend",
        detail_level="detailed",
    )

    _persist_attempt(
        document_id=document_id,
        format_id="fmt_quiz_previous",
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.FAILED,
        context=quiz_context,
    )
    _persist_attempt(
        document_id=document_id,
        format_id="fmt_flashcards_previous",
        format_type=GeneratedFormatType.FLASHCARDS,
        status=GeneratedFormatStatus.FAILED,
        context=flashcards_context,
    )

    response = client.post(
        f"{api_prefix}/documents/"
        f"{document_id}/formats/regenerate",
        json={
            "formats": [
                "quiz",
                "flashcards",
            ]
        },
    )

    _assert_error_contract(
        response,
        expected_status=409,
        expected_code="FORMAT_CONTEXT_CONFLICT",
    )


def test_regeneration_validation_uses_request_validation_code(
    client: TestClient,
    api_prefix: str,
) -> None:
    """422 de regeneración conserva detalle por campo."""
    response = client.post(
        f"{api_prefix}/documents/"
        "doc_validation/formats/regenerate",
        json={
            "formats": [
                "quiz",
                "quiz",
            ]
        },
    )

    body = _assert_error_contract(
        response,
        expected_status=422,
        expected_code=(
            "REQUEST_VALIDATION_ERROR"
        ),
    )

    assert any(
        error["field"] == "formats"
        for error in body["errors"]
    )


def test_regeneration_exposes_registration_failure_code(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Fallo de persistencia de regeneración tiene código específico."""
    client.app.state.format_regeneration_service = (
        FailingRegenerationService()
    )

    response = client.post(
        f"{api_prefix}/documents/"
        "doc_repository_error/formats/regenerate",
        json={
            "formats": [
                "quiz"
            ]
        },
    )

    _assert_error_contract(
        response,
        expected_status=500,
        expected_code=(
            "FORMAT_REGENERATION_REGISTRATION_FAILED"
        ),
    )


def test_unclassified_framework_http_error_uses_safe_fallback(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Un 404 del router no se etiqueta falsamente como documento."""
    response = client.get(
        f"{api_prefix}/route-that-does-not-exist"
    )

    _assert_error_contract(
        response,
        expected_status=404,
        expected_code="HTTP_ERROR",
    )
