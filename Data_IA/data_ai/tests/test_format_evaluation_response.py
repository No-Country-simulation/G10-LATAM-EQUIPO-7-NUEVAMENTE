"""
Tests automáticos de EvaluationResponse.

Valida las reglas de consistencia entre:
- scores;
- informacion_no_respaldada;
- status final.

Reglas esperadas:
- aprobado:
    todos los scores >= 4
    e informacion_no_respaldada = False
- requiere_revision:
    ningún score <= 2
    y al menos un score == 3
- rechazado:
    algún score <= 2
    o informacion_no_respaldada = True
"""

import pytest
from pydantic import ValidationError

from data_ai.schemas.format_evaluation import (
    EvaluationResponse,
    EvaluationScores,
)
from data_ai.evaluation.config import (
    EVALUATOR_VERSION,
    RUBRIC_VERSION,
)

def build_scores(
    relevancia: int = 5,
    coherencia: int = 5,
    adaptacion_didactica: int = 5,
    informacion_respaldada: int = 5,
) -> EvaluationScores:
    """Construye scores válidos para reutilizar en los tests."""
    return EvaluationScores(
        relevancia=relevancia,
        coherencia=coherencia,
        adaptacion_didactica=adaptacion_didactica,
        informacion_respaldada=informacion_respaldada,
    )


def test_approved_response_is_valid():
    """Todos los scores >= 4 y sin información no respaldada -> aprobado."""
    response = EvaluationResponse(
        document_id="DOC-001",
        format="quiz",
        status="aprobado",
        scores=build_scores(
            relevancia=5,
            coherencia=4,
            adaptacion_didactica=4,
            informacion_respaldada=5,
        ),
        informacion_no_respaldada=False,
        observaciones=[],
    )

    assert response.status == "aprobado"
    assert response.informacion_no_respaldada is False


def test_review_required_response_is_valid():
    """Un score igual a 3 y ninguno <= 2 -> requiere_revision."""
    response = EvaluationResponse(
        document_id="DOC-001",
        format="flashcards",
        status="requiere_revision",
        scores=build_scores(
            relevancia=4,
            coherencia=3,
            adaptacion_didactica=4,
            informacion_respaldada=5,
        ),
        informacion_no_respaldada=False,
        observaciones=[
            "La coherencia requiere revisión."
        ],
    )

    assert response.status == "requiere_revision"


def test_low_score_response_is_rejected():
    """Un score <= 2 -> rechazado."""
    response = EvaluationResponse(
        document_id="DOC-001",
        format="quiz",
        status="rechazado",
        scores=build_scores(
            relevancia=2,
            coherencia=4,
            adaptacion_didactica=4,
            informacion_respaldada=5,
        ),
        informacion_no_respaldada=False,
        observaciones=[
            "La relevancia es insuficiente."
        ],
    )

    assert response.status == "rechazado"


def test_unbacked_information_response_is_rejected():
    """informacion_no_respaldada=True -> rechazado."""
    response = EvaluationResponse(
        document_id="DOC-001",
        format="flashcards",
        status="rechazado",
        scores=build_scores(
            relevancia=5,
            coherencia=5,
            adaptacion_didactica=5,
            informacion_respaldada=5,
        ),
        informacion_no_respaldada=True,
        observaciones=[
            "Se detectó información no respaldada por los chunks."
        ],
    )

    assert response.status == "rechazado"
    assert response.informacion_no_respaldada is True


def test_inconsistent_approved_status_is_rejected():
    """
    No debe permitirse status='aprobado'
    cuando un score requiere revisión.
    """
    with pytest.raises(ValidationError) as exc_info:
        EvaluationResponse(
            document_id="DOC-001",
            format="quiz",
            status="aprobado",
            scores=build_scores(
                relevancia=5,
                coherencia=3,
                adaptacion_didactica=5,
                informacion_respaldada=5,
            ),
            informacion_no_respaldada=False,
            observaciones=[],
        )

    assert "status inconsistente con la evaluación" in str(exc_info.value)


def test_inconsistent_review_status_is_rejected():
    """
    No debe permitirse status='requiere_revision'
    cuando algún score obliga a rechazar.
    """
    with pytest.raises(ValidationError) as exc_info:
        EvaluationResponse(
            document_id="DOC-001",
            format="flashcards",
            status="requiere_revision",
            scores=build_scores(
                relevancia=5,
                coherencia=2,
                adaptacion_didactica=4,
                informacion_respaldada=4,
            ),
            informacion_no_respaldada=False,
            observaciones=[],
        )

    assert "status inconsistente con la evaluación" in str(exc_info.value)


def test_score_outside_allowed_range_is_rejected():
    """Los scores deben permanecer entre 1 y 5."""
    with pytest.raises(ValidationError):
        build_scores(
            relevancia=6,
            coherencia=5,
            adaptacion_didactica=5,
            informacion_respaldada=5,
        )
        

def test_evaluation_response_versions_from_config():
    """Valida que EvaluationResponse exponga las versiones definidas en config."""

    response = EvaluationResponse(
        document_id="DOC-001",
        format="quiz",
        status="aprobado",
        scores=build_scores(
            relevancia=5,
            coherencia=5,
            adaptacion_didactica=5,
            informacion_respaldada=5,
        ),
        informacion_no_respaldada=False,
        observaciones=[],
    )

    assert response.evaluator_version == EVALUATOR_VERSION
    assert response.rubric_version == RUBRIC_VERSION