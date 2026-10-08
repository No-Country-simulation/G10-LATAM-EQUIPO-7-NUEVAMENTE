"""Pruebas HTTP del endpoint de regeneración de formatos."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

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


class NoOpBackgroundOrchestration:
    """Evita llamadas externas al ejecutar BackgroundTasks en TestClient."""

    def __init__(self) -> None:
        self.completed_attempt_ids: list[
            tuple[str, ...]
        ] = []

    async def complete_default_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
    ) -> list[GeneratedFormat]:
        self.completed_attempt_ids.append(
            tuple(
                attempt.format_id
                for attempt in attempts
            )
        )

        return list(
            attempts
        )

    def fail_default_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
        error_message: str,
    ) -> list[GeneratedFormat]:
        return []


class FailingRegenerationService:
    """Simula un fallo de persistencia durante la preparación."""

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


def build_context() -> GenerationContext:
    """Contexto pedagógico persistido por la generación anterior."""
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
        learning_objective=(
            "Comprender la arquitectura."
        ),
    )


def persist_document(
    *,
    document_id: str,
    status: DocumentStatus,
) -> None:
    """Persiste un documento en la base configurada para el test."""
    from app.core.config import settings

    repository = (
        create_document_repository(
            settings.DATABASE_URL
        )
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


def persist_attempt(
    *,
    document_id: str,
    format_id: str,
    format_type: GeneratedFormatType,
    status: GeneratedFormatStatus,
    context: GenerationContext | None = None,
) -> GeneratedFormat:
    """Persiste un intento previo para regeneración."""
    from app.core.config import settings

    repository = (
        create_generated_format_repository(
            settings.DATABASE_URL
        )
    )

    attempt = GeneratedFormat(
        format_id=format_id,
        document_id=document_id,
        format_type=format_type,
        status=status,
        generation_context=(
            context
            or build_context()
        ),
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
        created_at=datetime.now(
            UTC
        ),
        updated_at=datetime.now(
            UTC
        ),
    )

    repository.create(
        attempt
    )

    return attempt


def install_noop_background(
    client: TestClient,
) -> NoOpBackgroundOrchestration:
    """Sustituye solo la ejecución background del endpoint."""
    service = (
        NoOpBackgroundOrchestration()
    )

    client.app.state.adaptation_orchestration_service = (
        service
    )

    return service


def test_regenerate_one_format_returns_202_and_new_processing_attempt(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Regenera un formato preservando el intento anterior."""
    document_id = "doc_regenerate_one"

    persist_document(
        document_id=document_id,
        status=DocumentStatus.INDEXED,
    )

    previous = persist_attempt(
        document_id=document_id,
        format_id="fmt_quiz_old",
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.FAILED,
    )

    background = install_noop_background(
        client
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

    assert response.status_code == 202

    body = response.json()

    assert (
        body["document_id"]
        == document_id
    )
    assert (
        body["status"]
        == "processing"
    )
    assert set(
        body["formats"]
    ) == {
        "quiz"
    }

    regenerated = (
        body["formats"]["quiz"]
    )

    assert (
        regenerated["status"]
        == "processing"
    )
    assert (
        regenerated["format_id"]
        != previous.format_id
    )

    assert background.completed_attempt_ids == [
        (
            regenerated["format_id"],
        )
    ]

    from app.core.config import settings

    repository = (
        create_generated_format_repository(
            settings.DATABASE_URL
        )
    )

    history = (
        repository.find_by_document_id(
            document_id
        )
    )

    assert len(history) == 2

    persisted_regeneration = next(
        generated_format
        for generated_format in history
        if (
            generated_format.format_id
            == regenerated["format_id"]
        )
    )

    assert (
        persisted_regeneration.status
        == GeneratedFormatStatus.PROCESSING
    )
    assert (
        persisted_regeneration.generation_context
        == previous.generation_context
    )


def test_regenerate_multiple_formats_returns_both_processing(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Acepta Quiz y Flashcards dentro de la misma solicitud."""
    document_id = (
        "doc_regenerate_multiple"
    )

    persist_document(
        document_id=document_id,
        status=DocumentStatus.INDEXED,
    )

    context = build_context()

    persist_attempt(
        document_id=document_id,
        format_id="fmt_quiz_old",
        format_type=GeneratedFormatType.QUIZ,
        status=GeneratedFormatStatus.FAILED,
        context=context,
    )

    persist_attempt(
        document_id=document_id,
        format_id=(
            "fmt_flashcards_old"
        ),
        format_type=(
            GeneratedFormatType.FLASHCARDS
        ),
        status=(
            GeneratedFormatStatus.NO_RESULTS
        ),
        context=context,
    )

    background = install_noop_background(
        client
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

    assert response.status_code == 202

    body = response.json()

    assert (
        body["status"]
        == "processing"
    )

    assert set(
        body["formats"]
    ) == {
        "quiz",
        "flashcards",
    }

    assert all(
        format_response["status"]
        == "processing"
        for format_response
        in body["formats"].values()
    )

    assert len(
        background.completed_attempt_ids
    ) == 1

    assert set(
        background.completed_attempt_ids[0]
    ) == {
        body["formats"]["quiz"][
            "format_id"
        ],
        body["formats"]["flashcards"][
            "format_id"
        ],
    }


def test_regenerate_returns_404_for_unknown_document(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Devuelve 404 si document_id no existe."""
    install_noop_background(
        client
    )

    response = client.post(
        f"{api_prefix}/documents/"
        "doc_unknown/formats/regenerate",
        json={
            "formats": [
                "quiz"
            ]
        },
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "No existe el documento doc_unknown."
    )


def test_regenerate_returns_409_when_document_is_not_indexed(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Devuelve 409 si el documento todavía no está indexed."""
    document_id = (
        "doc_not_indexed"
    )

    persist_document(
        document_id=document_id,
        status=DocumentStatus.STORED,
    )

    install_noop_background(
        client
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

    assert response.status_code == 409

    assert "indexed" in (
        response.json()["detail"]
    )


def test_regenerate_returns_409_when_requested_format_is_processing(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Devuelve 409 si ya existe un intento activo del formato."""
    document_id = (
        "doc_processing_conflict"
    )

    persist_document(
        document_id=document_id,
        status=DocumentStatus.INDEXED,
    )

    persist_attempt(
        document_id=document_id,
        format_id=(
            "fmt_quiz_processing"
        ),
        format_type=GeneratedFormatType.QUIZ,
        status=(
            GeneratedFormatStatus.PROCESSING
        ),
    )

    install_noop_background(
        client
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

    assert response.status_code == 409

    assert "processing" in (
        response.json()["detail"]
    )


def test_regenerate_returns_409_without_previous_context(
    client: TestClient,
    api_prefix: str,
) -> None:
    """No inventa contexto cuando el formato nunca fue generado."""
    document_id = (
        "doc_without_history"
    )

    persist_document(
        document_id=document_id,
        status=DocumentStatus.INDEXED,
    )

    install_noop_background(
        client
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

    assert response.status_code == 409

    assert "generación previa" in (
        response.json()["detail"]
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "formats": []
        },
        {
            "formats": [
                "quiz",
                "quiz",
            ]
        },
        {
            "formats": [
                "podcast"
            ]
        },
    ],
)
def test_regenerate_returns_422_for_invalid_formats(
    client: TestClient,
    api_prefix: str,
    payload: dict[
        str,
        list[str],
    ],
) -> None:
    """Valida vacío, duplicados y formatos realmente no soportados."""
    response = client.post(
        f"{api_prefix}/documents/"
        "doc_validation/formats/regenerate",
        json=payload,
    )

    assert response.status_code == 422


def test_regenerate_returns_500_when_attempts_cannot_be_persisted(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Traduce un fallo de persistencia al contrato HTTP acordado."""
    client.app.state.format_regeneration_service = (
        FailingRegenerationService()
    )

    install_noop_background(
        client
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

    assert response.status_code == 500

    assert (
        response.json()["detail"]
        == (
            "No fue posible registrar los nuevos "
            "intentos de regeneración."
        )
    )
