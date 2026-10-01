"""
Tests automáticos de la API de evaluación de formatos.

Valida:
- GET /health -> 200
- POST /evaluate con Quiz válido -> 501 temporal
- POST /evaluate con Flashcards válidas -> 501 temporal
- POST /evaluate sin learning_objective -> 501 temporal
- POST /evaluate sin generation_context -> 422
- POST /evaluate con payload inválido -> 422
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from data_ai.api.app import app


client = TestClient(app)

DATA_IA_ROOT = Path(__file__).resolve().parents[2]
MOCK_DIR = DATA_IA_ROOT / "data" / "evaluation" / "mock"


def load_mock(filename: str) -> dict:
    """Carga un mock JSON desde data/evaluation/mock."""
    path = MOCK_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo mock: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_health_returns_ok():
    """El endpoint de salud debe responder correctamente."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_quiz_reaches_evaluator_placeholder():
    """
    Un Quiz válido debe superar la validación del contrato y llegar
    al placeholder del evaluator, que temporalmente responde 501.
    """
    payload = load_mock("evaluation_quiz_valid_v1.json")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 501

    body = response.json()
    assert body["detail"]["code"] == "QUALITY_EVALUATOR_NOT_IMPLEMENTED"
    assert body["detail"]["document_id"] == "DOC-001"
    assert body["detail"]["format"] == "quiz"


def test_valid_flashcards_reaches_evaluator_placeholder():
    """
    Flashcards válidas deben superar la validación del contrato y llegar
    al placeholder del evaluator, que temporalmente responde 501.
    """
    payload = load_mock("evaluation_flashcards_valid_v1.json")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 501

    body = response.json()
    assert body["detail"]["code"] == "QUALITY_EVALUATOR_NOT_IMPLEMENTED"
    assert body["detail"]["document_id"] == "DOC-001"
    assert body["detail"]["format"] == "flashcards"


def test_request_without_learning_objective_reaches_evaluator_placeholder():
    """
    learning_objective es opcional, por lo que su ausencia no debe impedir
    que un request válido llegue al evaluator.
    """
    payload = load_mock("evaluation_quiz_valid_v1.json")
    payload["generation_context"].pop("learning_objective")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 501

    body = response.json()
    assert body["detail"]["code"] == "QUALITY_EVALUATOR_NOT_IMPLEMENTED"
    assert body["detail"]["document_id"] == "DOC-001"
    assert body["detail"]["format"] == "quiz"


def test_missing_generation_context_returns_422():
    """Un request sin generation_context debe ser rechazado."""
    payload = load_mock("evaluation_quiz_valid_v1.json")
    payload.pop("generation_context")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 422

    body = response.json()
    assert "detail" in body

    errors = body["detail"]

    assert any(
        "generation_context" in str(error.get("loc", []))
        for error in errors
    )


def test_invalid_quiz_returns_422():
    """Un Quiz con correct_answer fuera de options debe ser rechazado."""
    payload = load_mock("evaluation_quiz_invalid_answer_v1.json")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 422

    body = response.json()
    assert "detail" in body

    errors = body["detail"]
    messages = [error["msg"] for error in errors]

    assert any(
        "correct_answer debe coincidir con una de las opciones." in message
        for message in messages
    )


def test_invalid_flashcards_returns_422():
    """Flashcards con card_id duplicados deben ser rechazadas."""
    payload = load_mock("evaluation_flashcards_invalid_duplicate_id_v1.json")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 422

    body = response.json()
    assert "detail" in body

    errors = body["detail"]
    messages = [error["msg"] for error in errors]

    assert any(
        "Los card_id deben ser únicos." in message
        for message in messages
    )


def test_invalid_chunk_document_returns_422():
    """Los chunks deben pertenecer al mismo document_id de la solicitud."""
    payload = load_mock("evaluation_invalid_chunk_document_v1.json")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 422

    body = response.json()
    assert "detail" in body

    errors = body["detail"]
    messages = [error["msg"] for error in errors]

    assert any(
        "Todos los chunks_used deben pertenecer al document_id" in message
        for message in messages
    )