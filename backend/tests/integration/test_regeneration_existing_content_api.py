"""Contrato HTTP para regenerar contenido educativo ya existente."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.domain.document import Document
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    FlashcardItem,
    FlashcardsContent,
    QuizContent,
    QuizQuestion,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.infrastructure.persistence.repository_factory import (
    create_document_repository,
    create_generated_format_repository,
)


class NoOpBackgroundOrchestration:
    """Evita integraciones externas después de aceptar la regeneración."""

    async def complete_default_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
    ) -> list[GeneratedFormat]:
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


def build_context() -> GenerationContext:
    """Construye el contexto reutilizable por regeneración."""
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
        learning_objective=(
            "Comprender el contenido."
        ),
    )


def build_evidence(
    document_id: str,
) -> tuple[
    ChunkEvidence,
    ...
]:
    """Construye evidencia válida para formatos exitosos."""
    return (
        ChunkEvidence(
            chunk_id=f"{document_id}_chunk_1",
            document_id=document_id,
            rank=1,
            score=0.95,
            text="Contenido utilizado.",
        ),
    )


def persist_document(
    document_id: str,
) -> None:
    """Persiste un documento indexado."""
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
            status=DocumentStatus.INDEXED,
            oci_object_name=(
                f"documents/{document_id}/original.txt"
            ),
        )
    )


def persist_quiz_success(
    document_id: str,
    format_id: str,
) -> None:
    """Persiste un Quiz exitoso previo."""
    from app.core.config import settings

    repository = (
        create_generated_format_repository(
            settings.DATABASE_URL
        )
    )

    now = datetime.now(
        UTC
    )

    repository.create(
        GeneratedFormat(
            format_id=format_id,
            document_id=document_id,
            format_type=GeneratedFormatType.QUIZ,
            status=GeneratedFormatStatus.SUCCESS,
            generation_context=build_context(),
            content=QuizContent(
                title="Quiz existente",
                instructions="Seleccione una opción.",
                questions=(
                    QuizQuestion(
                        question_id="q1",
                        question="¿Qué es BackendAPI?",
                        options=(
                            "Orquestador",
                            "Vector Store",
                        ),
                        correct_answer="Orquestador",
                        explanation="Coordina el flujo.",
                    ),
                ),
            ),
            chunks_used=build_evidence(
                document_id
            ),
            created_at=now,
            updated_at=now,
        )
    )


def persist_flashcards(
    *,
    document_id: str,
    format_id: str,
    status: GeneratedFormatStatus,
) -> None:
    """Persiste Flashcards exitosas o fallidas."""
    from app.core.config import settings

    repository = (
        create_generated_format_repository(
            settings.DATABASE_URL
        )
    )

    now = datetime.now(
        UTC
    )

    successful = (
        status
        == GeneratedFormatStatus.SUCCESS
    )

    repository.create(
        GeneratedFormat(
            format_id=format_id,
            document_id=document_id,
            format_type=(
                GeneratedFormatType.FLASHCARDS
            ),
            status=status,
            generation_context=build_context(),
            content=(
                FlashcardsContent(
                    title="Flashcards existentes",
                    instructions="Revise las tarjetas.",
                    cards=(
                        FlashcardItem(
                            card_id="c1",
                            front="BackendAPI",
                            back="Orquestador",
                        ),
                    ),
                )
                if successful
                else None
            ),
            chunks_used=(
                build_evidence(
                    document_id
                )
                if successful
                else ()
            ),
            error_message=(
                None
                if successful
                else "Fallo previo."
            ),
            created_at=now,
            updated_at=now,
        )
    )


def install_noop_background(
    client: TestClient,
) -> None:
    """Sustituye únicamente la ejecución background."""
    client.app.state.adaptation_orchestration_service = (
        NoOpBackgroundOrchestration()
    )


def test_ready_document_can_regenerate_existing_successful_quiz(
    client: TestClient,
    api_prefix: str,
) -> None:
    """READY no bloquea crear un nuevo intento para contenido existente."""
    document_id = "doc_ready_regenerate"

    persist_document(
        document_id
    )
    persist_quiz_success(
        document_id,
        "fmt_quiz_success",
    )
    persist_flashcards(
        document_id=document_id,
        format_id="fmt_flashcards_success",
        status=GeneratedFormatStatus.SUCCESS,
    )

    formats_response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert (
        formats_response.status_code
        == 200
    )
    assert (
        formats_response.json()["status"]
        == "ready"
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

    assert response.status_code == 202

    body = response.json()

    assert (
        body["status"]
        == "processing"
    )
    assert (
        body["formats"]["quiz"]["status"]
        == "processing"
    )
    assert (
        body["formats"]["quiz"]["format_id"]
        != "fmt_quiz_success"
    )


def test_partial_document_can_regenerate_format_that_was_already_successful(
    client: TestClient,
    api_prefix: str,
) -> None:
    """PARTIAL tampoco limita la regeneración al formato fallido."""
    document_id = "doc_partial_regenerate_success"

    persist_document(
        document_id
    )
    persist_quiz_success(
        document_id,
        "fmt_quiz_success",
    )
    persist_flashcards(
        document_id=document_id,
        format_id="fmt_flashcards_failed",
        status=GeneratedFormatStatus.FAILED,
    )

    formats_response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert (
        formats_response.status_code
        == 200
    )
    assert (
        formats_response.json()["status"]
        == "partial"
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

    assert response.status_code == 202

    body = response.json()

    assert (
        body["formats"]["quiz"]["status"]
        == "processing"
    )
    assert (
        body["formats"]["quiz"]["format_id"]
        != "fmt_quiz_success"
    )
