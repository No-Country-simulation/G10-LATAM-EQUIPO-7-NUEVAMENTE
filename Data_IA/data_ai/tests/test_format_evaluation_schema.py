"""
Tests automáticos del contrato de evaluación de formatos.

Valida los cinco mocks de Sprint 2:
- 2 payloads válidos deben ser aceptados.
- 3 payloads inválidos deben fallar por la razón esperada.
"""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from data_ai.schemas.format_evaluation import EvaluationRequest


DATA_IA_ROOT = Path(__file__).resolve().parents[2]
MOCK_DIR = DATA_IA_ROOT / "data" / "evaluation" / "mock"

evaluation_request_adapter = TypeAdapter(EvaluationRequest)


def load_mock(filename: str) -> dict:
    """Carga un mock JSON desde data/evaluation/mock."""
    path = MOCK_DIR / filename

    if not path.exists():
        pytest.fail(f"No se encontró el archivo mock: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@pytest.mark.parametrize(
    ("filename", "expected_format"),
    [
        ("evaluation_quiz_valid_v1.json", "quiz"),
        ("evaluation_flashcards_valid_v1.json", "flashcards"),
    ],
)
def test_valid_format_evaluation_payloads(filename: str, expected_format: str):
    """Los payloads válidos deben cumplir EvaluationRequest."""
    payload = load_mock(filename)

    result = evaluation_request_adapter.validate_python(payload)

    assert result.document_id == "DOC-001"
    assert result.format == expected_format
    assert len(result.chunks_used) >= 1


@pytest.mark.parametrize(
    ("filename", "expected_error"),
    [
        (
            "evaluation_quiz_invalid_answer_v1.json",
            "correct_answer debe coincidir con una de las opciones.",
        ),
        (
            "evaluation_flashcards_invalid_duplicate_id_v1.json",
            "Los card_id deben ser únicos.",
        ),
        (
            "evaluation_invalid_chunk_document_v1.json",
            "Todos los chunks_used deben pertenecer al document_id",
        ),
    ],
)
def test_invalid_format_evaluation_payloads_fail_for_expected_reason(
    filename: str,
    expected_error: str,
):
    """Los payloads inválidos deben fallar por la causa esperada."""
    payload = load_mock(filename)

    with pytest.raises(ValidationError) as exc_info:
        evaluation_request_adapter.validate_python(payload)

    assert expected_error in str(exc_info.value)
