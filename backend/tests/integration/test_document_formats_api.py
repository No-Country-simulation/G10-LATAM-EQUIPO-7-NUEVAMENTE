"""Pruebas HTTP de consulta de formatos generados."""

from datetime import UTC, datetime
from pathlib import Path

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
from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)
from tests.fakes import (
    FakeAdaptationOrchestrationService,
)

DOCUMENT_ID_KEY = "document_id"

_ADAPTATION_DATA = {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
    "learning_objective": (
        "Comprender los conceptos principales del documento."
    ),
}


def build_database(
    tmp_path: Path,
) -> SQLiteDatabase:
    """Obtiene la base SQLite utilizada por el cliente de prueba."""
    database_path = (
        tmp_path / "nuevamente_test.db"
    )

    database = SQLiteDatabase(
        f"sqlite:///{database_path.as_posix()}"
    )

    database.initialize()

    return database


def build_generated_format_repository(
    tmp_path: Path,
) -> SQLiteGeneratedFormatRepositoryAdapter:
    """Obtiene el repositorio de formatos de la BD de prueba."""
    return SQLiteGeneratedFormatRepositoryAdapter(
        build_database(
            tmp_path
        )
    )


def persist_indexed_document(
    *,
    tmp_path: Path,
    document_id: str,
) -> None:
    """Persiste directamente un documento indexado para pruebas de consulta."""
    repository = SQLiteDocumentRepositoryAdapter(
        build_database(
            tmp_path
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


def build_context() -> GenerationContext:
    """Construye contexto pedagógico válido."""
    return GenerationContext(
        profile="beginner",
        niche="technology",
        detail_level="detailed",
    )


def build_evidence(
    document_id: str,
) -> tuple[ChunkEvidence, ...]:
    """Construye evidencia asociada al documento."""
    return (
        ChunkEvidence(
            chunk_id=f"{document_id}_1_0",
            document_id=document_id,
            rank=1,
            score=0.93,
            text=(
                "BackendAPI centraliza la "
                "orquestación del producto."
            ),
        ),
    )


def build_quiz(
    *,
    document_id: str,
    status: GeneratedFormatStatus = (
        GeneratedFormatStatus.SUCCESS
    ),
) -> GeneratedFormat:
    """Construye un Quiz persistible."""
    successful = (
        status
        == GeneratedFormatStatus.SUCCESS
    )

    return GeneratedFormat(
        format_id="fmt_quiz_api",
        document_id=document_id,
        format_type=GeneratedFormatType.QUIZ,
        status=status,
        generation_context=build_context(),
        content=(
            QuizContent(
                title="Quiz BackendAPI",
                instructions=(
                    "Seleccione la respuesta correcta."
                ),
                questions=(
                    QuizQuestion(
                        question_id="q1",
                        question=(
                            "¿Cuál es la responsabilidad "
                            "de BackendAPI?"
                        ),
                        options=(
                            "Orquestar el producto",
                            "Crear embeddings",
                        ),
                        correct_answer=(
                            "Orquestar el producto"
                        ),
                        explanation=(
                            "BackendAPI coordina las "
                            "integraciones externas."
                        ),
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
            else (
                "No fue posible generar el Quiz."
            )
        ),
        created_at=datetime.now(
            UTC
        ),
        updated_at=datetime.now(
            UTC
        ),
    )


def build_flashcards(
    *,
    document_id: str,
    status: GeneratedFormatStatus = (
        GeneratedFormatStatus.SUCCESS
    ),
) -> GeneratedFormat:
    """Construye Flashcards persistibles."""
    successful = (
        status
        == GeneratedFormatStatus.SUCCESS
    )

    return GeneratedFormat(
        format_id="fmt_flashcards_api",
        document_id=document_id,
        format_type=(
            GeneratedFormatType.FLASHCARDS
        ),
        status=status,
        generation_context=build_context(),
        content=(
            FlashcardsContent(
                title="Flashcards BackendAPI",
                instructions=(
                    "Revise cada tarjeta."
                ),
                cards=(
                    FlashcardItem(
                        card_id="card_1",
                        front="BackendAPI",
                        back=(
                            "Orquestador del producto."
                        ),
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
            else (
                "No fue posible generar Flashcards."
            )
        ),
        created_at=datetime.now(
            UTC
        ),
        updated_at=datetime.now(
            UTC
        ),
    )


def upload_document(
    *,
    client: TestClient,
    api_prefix: str,
) -> str:
    """Carga y adapta un documento mediante el flujo público."""
    response = client.post(
        f"{api_prefix}/documents",
        data=_ADAPTATION_DATA,
        files={
            "file": (
                "manual.txt",
                b"Contenido para generar formatos",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201

    return response.json()[
        DOCUMENT_ID_KEY
    ]


def test_formats_returns_404_for_unknown_document(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Devuelve 404 para un documento inexistente."""
    response = client.get(
        f"{api_prefix}/documents/"
        "doc_inexistente/formats"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "No existe el documento "
        "doc_inexistente."
    )


def test_formats_returns_ready_after_upload(
    client: TestClient,
    api_prefix: str,
    fake_adaptation_orchestration_service: (
        FakeAdaptationOrchestrationService
    ),
) -> None:
    """La carga indexa y genera Quiz y Flashcards en etapas separadas."""
    document_id = upload_document(
        client=client,
        api_prefix=api_prefix,
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
        .generation_requests
    ) == 1

    generation_request = (
        fake_adaptation_orchestration_service
        .generation_requests[0]
    )

    assert (
        generation_request["document_id"]
        == document_id
    )

    response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["document_id"]
        == document_id
    )
    assert body["status"] == "ready"

    assert set(
        body["formats"]
    ) == {
        "quiz",
        "flashcards",
    }

    assert (
        body["formats"]["quiz"]["status"]
        == "success"
    )
    assert (
        body["formats"]["flashcards"]["status"]
        == "success"
    )


def test_formats_returns_ready_with_canonical_content(
    client: TestClient,
    api_prefix: str,
    tmp_path: Path,
) -> None:
    """Expone Quiz y Flashcards mediante el contrato canónico."""
    document_id = (
        "doc_formats_canonical"
    )

    persist_indexed_document(
        tmp_path=tmp_path,
        document_id=document_id,
    )

    repository = (
        build_generated_format_repository(
            tmp_path
        )
    )

    repository.create(
        build_quiz(
            document_id=document_id
        )
    )

    repository.create(
        build_flashcards(
            document_id=document_id
        )
    )

    response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ready"

    quiz = body["formats"]["quiz"]

    assert (
        quiz["format_id"]
        == "fmt_quiz_api"
    )
    assert quiz["status"] == "success"
    assert quiz["error_message"] is None

    assert (
        quiz["content"]["title"]
        == "Quiz BackendAPI"
    )

    question = (
        quiz["content"]["questions"][0]
    )

    assert (
        question["question_id"]
        == "q1"
    )

    assert question["options"] == [
        "Orquestar el producto",
        "Crear embeddings",
    ]

    assert (
        question["correct_answer"]
        == "Orquestar el producto"
    )

    assert question["explanation"] == (
        "BackendAPI coordina las "
        "integraciones externas."
    )

    flashcards = (
        body["formats"]["flashcards"]
    )

    assert (
        flashcards["format_id"]
        == "fmt_flashcards_api"
    )
    assert (
        flashcards["status"]
        == "success"
    )

    card = (
        flashcards["content"]["cards"][0]
    )

    assert card == {
        "card_id": "card_1",
        "front": "BackendAPI",
        "back": "Orquestador del producto.",
    }


def test_formats_returns_partial_when_one_format_fails(
    client: TestClient,
    api_prefix: str,
    tmp_path: Path,
) -> None:
    """Un éxito y un fallo producen estado global partial."""
    document_id = (
        "doc_formats_partial"
    )

    persist_indexed_document(
        tmp_path=tmp_path,
        document_id=document_id,
    )

    repository = (
        build_generated_format_repository(
            tmp_path
        )
    )

    repository.create(
        build_quiz(
            document_id=document_id
        )
    )

    repository.create(
        build_flashcards(
            document_id=document_id,
            status=(
                GeneratedFormatStatus.FAILED
            ),
        )
    )

    response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "partial"

    assert (
        body["formats"]["quiz"]["status"]
        == "success"
    )

    failed_flashcards = (
        body["formats"]["flashcards"]
    )

    assert (
        failed_flashcards["status"]
        == "failed"
    )
    assert (
        failed_flashcards["content"]
        is None
    )
    assert (
        failed_flashcards[
            "error_message"
        ]
        == (
            "No fue posible generar "
            "Flashcards."
        )
    )


def test_formats_returns_error_when_no_format_succeeds(
    client: TestClient,
    api_prefix: str,
    tmp_path: Path,
) -> None:
    """Sin resultados exitosos devuelve estado global error."""
    document_id = (
        "doc_formats_error"
    )

    persist_indexed_document(
        tmp_path=tmp_path,
        document_id=document_id,
    )

    repository = (
        build_generated_format_repository(
            tmp_path
        )
    )

    repository.create(
        build_quiz(
            document_id=document_id,
            status=(
                GeneratedFormatStatus.FAILED
            ),
        )
    )

    repository.create(
        build_flashcards(
            document_id=document_id,
            status=(
                GeneratedFormatStatus.NO_RESULTS
            ),
        )
    )

    response = client.get(
        f"{api_prefix}/documents/"
        f"{document_id}/formats"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "error"

    assert (
        body["formats"]["quiz"]["status"]
        == "failed"
    )

    assert (
        body["formats"]["flashcards"]
        ["status"]
        == "no_results"
    )