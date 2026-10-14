"""Pruebas del repositorio SQLite de evaluaciones (V1 y V2)."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.document import Document
from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.format_evaluation import (
    EvaluationScores,
    FormatEvaluation,
    HeuristicScoresV2,
    SemanticEvaluationResult,
    SemanticObservation,
    SemanticRecommendation,
    SemanticScores,
    UnsupportedClaim,
)
from app.domain.generated_content import (
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
from app.infrastructure.persistence.sqlite_format_evaluation_repository_adapter import (
    SQLiteFormatEvaluationRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)
from app.ports.format_evaluation_repository_port import (
    FormatEvaluationAlreadyExistsError,
)

DOCUMENT_ID = "doc_123"
FORMAT_ID = "fmt_quiz_1"


def build_repositories(
    tmp_path: Path,
) -> tuple[
    SQLiteDocumentRepositoryAdapter,
    SQLiteGeneratedFormatRepositoryAdapter,
    SQLiteFormatEvaluationRepositoryAdapter,
]:
    """Crea los tres repositorios SQLite sobre una BD aislada."""
    database = SQLiteDatabase(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    database.initialize()

    return (
        SQLiteDocumentRepositoryAdapter(database),
        SQLiteGeneratedFormatRepositoryAdapter(database),
        SQLiteFormatEvaluationRepositoryAdapter(database),
    )


def seed_generated_format(
    document_repository: SQLiteDocumentRepositoryAdapter,
    generated_format_repository: SQLiteGeneratedFormatRepositoryAdapter,
    *,
    format_id: str = FORMAT_ID,
) -> None:
    """Persiste un documento y una generación exitosa para satisfacer la FK."""
    content = f"Documento {DOCUMENT_ID}".encode()

    document_repository.create(
        Document(
            document_id=DOCUMENT_ID,
            original_filename="manual.pdf",
            sha256=hashlib.sha256(content).hexdigest(),
            content_type="application/pdf",
            size_bytes=len(content),
        )
    )

    generated_format_repository.create(
        GeneratedFormat(
            format_id=format_id,
            document_id=DOCUMENT_ID,
            format_type=GeneratedFormatType.QUIZ,
            status=GeneratedFormatStatus.SUCCESS,
            generation_context=GenerationContext(
                profile="beginner",
                niche="technology",
                detail_level="detailed",
            ),
            content=QuizContent(
                title="Quiz de prueba",
                instructions="Seleccione la respuesta correcta.",
                questions=(
                    QuizQuestion(
                        question_id="q1",
                        question="¿Qué es REST?",
                        options=("Un estilo arquitectónico", "Un lenguaje"),
                        correct_answer="Un estilo arquitectónico",
                        explanation="REST define convenciones sobre HTTP.",
                    ),
                ),
            ),
            chunks_used=(
                ChunkEvidence(
                    chunk_id="chunk_1",
                    document_id=DOCUMENT_ID,
                    rank=1,
                    score=0.9,
                    text="REST es un estilo arquitectónico.",
                ),
            ),
        )
    )


def build_v1_evaluation(
    *,
    evaluation_id: str | None = None,
    format_id: str = FORMAT_ID,
    created_at: datetime | None = None,
) -> FormatEvaluation:
    """Construye una evaluación V1 (heurístico 1.1) completa."""
    return FormatEvaluation(
        evaluation_id=evaluation_id or f"eval_{uuid4().hex}",
        format_id=format_id,
        status=FormatEvaluationStatus.APPROVED,
        scores=EvaluationScores(
            relevance=5,
            coherence=5,
            didactic_adaptation=4,
            content_support=5,
        ),
        unsupported_information=False,
        observations=("Buena cobertura del tema.",),
        evaluator_version="1.1.0",
        rubric_version="1.1.0",
        created_at=created_at or datetime.now(UTC),
    )


def build_v2_evaluation_success(
    *,
    evaluation_id: str | None = None,
    format_id: str = FORMAT_ID,
    created_at: datetime | None = None,
) -> FormatEvaluation:
    """Construye una evaluación V2 completa con semántico exitoso."""
    return FormatEvaluation(
        evaluation_id=evaluation_id or f"eval_{uuid4().hex}",
        format_id=format_id,
        evaluator_version="2.0.0",
        rubric_version="2.0.0",
        verdict="requires_revision",
        heuristic_scores=HeuristicScoresV2(
            relevance=4.0,
            coherence=4.0,
            didactic_adaptation=2.0,
            content_support=4.0,
        ),
        semantic_evaluation=SemanticEvaluationResult(
            status="success",
            scores=SemanticScores(
                relevance=4.6,
                coherence=4.7,
                didactic_adaptation=2.8,
                content_support=4.2,
            ),
            observations=(
                SemanticObservation(
                    dimension="didactic_adaptation",
                    severity="high",
                    message=(
                        "El contenido utiliza conceptos superiores "
                        "al nivel junior solicitado."
                    ),
                    item_id="q1",
                ),
            ),
            recommendations=(
                SemanticRecommendation(
                    dimension="didactic_adaptation",
                    message=(
                        "Explicar los conceptos básicos antes de "
                        "introducir terminología avanzada."
                    ),
                    item_id="q1",
                ),
            ),
            unsupported_information=(
                UnsupportedClaim(
                    claim="Docker reemplaza completamente a Kubernetes.",
                    reason="Los chunks utilizados no respaldan la afirmación.",
                    item_id="q1",
                    related_chunk_ids=("chunk_001", "chunk_002"),
                ),
            ),
            model="gemini-test",
            prompt_version="semantic-evaluator-v0.1",
            latency_ms=875,
        ),
        created_at=created_at or datetime.now(UTC),
    )


def build_v2_evaluation_semantic_failed(
    *,
    evaluation_id: str | None = None,
    format_id: str = FORMAT_ID,
) -> FormatEvaluation:
    """Construye una evaluación V2 con el componente semántico fallido."""
    return FormatEvaluation(
        evaluation_id=evaluation_id or f"eval_{uuid4().hex}",
        format_id=format_id,
        evaluator_version="2.0.0",
        rubric_version="2.0.0",
        verdict=None,
        semantic_evaluation=SemanticEvaluationResult(
            status="failed",
            error_code="timeout",
            error_message="El proveedor semántico no respondió a tiempo.",
        ),
    )


def build_v2_evaluation_semantic_unavailable(
    *,
    evaluation_id: str | None = None,
    format_id: str = FORMAT_ID,
) -> FormatEvaluation:
    """Construye una evaluación V2 con el evaluador semántico no configurado."""
    return FormatEvaluation(
        evaluation_id=evaluation_id or f"eval_{uuid4().hex}",
        format_id=format_id,
        evaluator_version="2.0.0",
        rubric_version="2.0.0",
        verdict="approved",
        heuristic_scores=HeuristicScoresV2(
            relevance=4.0,
            coherence=4.0,
            didactic_adaptation=4.0,
            content_support=4.0,
        ),
        semantic_evaluation=SemanticEvaluationResult(
            status="unavailable",
            error_code="not_configured",
        ),
    )


# ---------------------------------------------------------------------------
# V1 — compatibilidad (no debe romperse con la extensión V2)
# ---------------------------------------------------------------------------


def test_create_and_find_v1_evaluation_round_trips(
    tmp_path: Path,
) -> None:
    """Una evaluación V1 persistida se recupera idéntica y sin campos V2."""
    document_repository, generated_format_repository, evaluation_repository = (
        build_repositories(tmp_path)
    )
    seed_generated_format(document_repository, generated_format_repository)

    evaluation = build_v1_evaluation(evaluation_id="eval_v1")
    evaluation_repository.create(evaluation)

    found = evaluation_repository.find_by_id("eval_v1")

    assert found is not None
    assert found.status == FormatEvaluationStatus.APPROVED
    assert found.scores == evaluation.scores
    assert found.unsupported_information is False
    assert found.observations == ("Buena cobertura del tema.",)
    assert found.evaluator_version == "1.1.0"
    assert found.is_v2 is False
    assert found.verdict is None
    assert found.heuristic_scores is None
    assert found.semantic_evaluation is None


# ---------------------------------------------------------------------------
# V2 — éxito total, fallo técnico y no disponibilidad del semántico
# ---------------------------------------------------------------------------


def test_create_and_find_v2_evaluation_with_successful_semantic_round_trips(
    tmp_path: Path,
) -> None:
    """Una evaluación V2 completa conserva exactamente su estructura anidada."""
    document_repository, generated_format_repository, evaluation_repository = (
        build_repositories(tmp_path)
    )
    seed_generated_format(document_repository, generated_format_repository)

    evaluation = build_v2_evaluation_success(evaluation_id="eval_v2_success")
    evaluation_repository.create(evaluation)

    found = evaluation_repository.find_by_id("eval_v2_success")

    assert found is not None
    assert found.is_v2 is True
    assert found.status is None
    assert found.scores is None
    assert found.verdict == "requires_revision"
    assert found.heuristic_scores == evaluation.heuristic_scores

    semantic = found.semantic_evaluation
    assert semantic is not None
    assert semantic.status == "success"
    assert semantic.scores == evaluation.semantic_evaluation.scores
    assert semantic.observations == evaluation.semantic_evaluation.observations
    assert (
        semantic.recommendations
        == evaluation.semantic_evaluation.recommendations
    )
    assert (
        semantic.unsupported_information
        == evaluation.semantic_evaluation.unsupported_information
    )
    assert semantic.model == "gemini-test"
    assert semantic.prompt_version == "semantic-evaluator-v0.1"
    assert semantic.latency_ms == 875
    assert semantic.error_code is None


def test_create_and_find_v2_evaluation_with_failed_semantic(
    tmp_path: Path,
) -> None:
    """Un fallo técnico del semántico se conserva sin fabricar scores."""
    document_repository, generated_format_repository, evaluation_repository = (
        build_repositories(tmp_path)
    )
    seed_generated_format(document_repository, generated_format_repository)

    evaluation = build_v2_evaluation_semantic_failed(
        evaluation_id="eval_v2_failed"
    )
    evaluation_repository.create(evaluation)

    found = evaluation_repository.find_by_id("eval_v2_failed")

    assert found is not None
    assert found.verdict is None
    assert found.heuristic_scores is None

    semantic = found.semantic_evaluation
    assert semantic is not None
    assert semantic.status == "failed"
    assert semantic.scores is None
    assert semantic.error_code == "timeout"
    assert (
        semantic.error_message
        == "El proveedor semántico no respondió a tiempo."
    )


def test_create_and_find_v2_evaluation_with_unavailable_semantic(
    tmp_path: Path,
) -> None:
    """Un semántico no configurado conserva verdict/heurístico sin pisarlos."""
    document_repository, generated_format_repository, evaluation_repository = (
        build_repositories(tmp_path)
    )
    seed_generated_format(document_repository, generated_format_repository)

    evaluation = build_v2_evaluation_semantic_unavailable(
        evaluation_id="eval_v2_unavailable"
    )
    evaluation_repository.create(evaluation)

    found = evaluation_repository.find_by_id("eval_v2_unavailable")

    assert found is not None
    assert found.verdict == "approved"
    assert found.heuristic_scores == evaluation.heuristic_scores

    semantic = found.semantic_evaluation
    assert semantic is not None
    assert semantic.status == "unavailable"
    assert semantic.scores is None
    assert semantic.error_code == "not_configured"


# ---------------------------------------------------------------------------
# Coexistencia V1 + V2 e historial por format_id
# ---------------------------------------------------------------------------


def test_find_by_format_id_returns_v1_and_v2_in_chronological_order(
    tmp_path: Path,
) -> None:
    """El historial de un format_id puede mezclar evaluaciones V1 y V2."""
    document_repository, generated_format_repository, evaluation_repository = (
        build_repositories(tmp_path)
    )
    seed_generated_format(document_repository, generated_format_repository)

    older = build_v1_evaluation(
        evaluation_id="eval_old",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = build_v2_evaluation_success(
        evaluation_id="eval_new",
        created_at=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
    )

    evaluation_repository.create(older)
    evaluation_repository.create(newer)

    history = evaluation_repository.find_by_format_id(FORMAT_ID)

    assert [item.evaluation_id for item in history] == [
        "eval_old",
        "eval_new",
    ]
    assert history[0].is_v2 is False
    assert history[1].is_v2 is True


def test_find_by_format_id_returns_empty_list_when_no_evaluations(
    tmp_path: Path,
) -> None:
    """Un format_id sin evaluaciones devuelve una lista vacía, no None."""
    document_repository, generated_format_repository, evaluation_repository = (
        build_repositories(tmp_path)
    )
    seed_generated_format(document_repository, generated_format_repository)

    assert evaluation_repository.find_by_format_id(FORMAT_ID) == []


def test_find_by_id_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    """Buscar un evaluation_id inexistente devuelve None, no una excepción."""
    _, _, evaluation_repository = build_repositories(tmp_path)

    assert evaluation_repository.find_by_id("eval_missing") is None


def test_create_rejects_duplicate_evaluation_id(
    tmp_path: Path,
) -> None:
    """Dos evaluaciones con el mismo evaluation_id deben rechazarse."""
    document_repository, generated_format_repository, evaluation_repository = (
        build_repositories(tmp_path)
    )
    seed_generated_format(document_repository, generated_format_repository)

    evaluation_repository.create(
        build_v2_evaluation_success(evaluation_id="eval_dup")
    )

    with pytest.raises(FormatEvaluationAlreadyExistsError):
        evaluation_repository.create(
            build_v2_evaluation_success(evaluation_id="eval_dup")
        )
