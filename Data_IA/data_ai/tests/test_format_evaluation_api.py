"""
Tests automáticos de la API de evaluación de formatos.

Valida:
- GET /health -> 200
- POST /evaluate con Quiz válido -> 200
- POST /evaluate con Flashcards válidas -> 200
- POST /evaluate sin learning_objective -> 200
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


def test_valid_quiz_returns_evaluation():
    """Un Quiz válido debe ser evaluado y responder 200."""
    payload = load_mock("evaluation_quiz_valid_v1.json")

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body["document_id"] == "DOC-001"
    assert body["format"] == "quiz"

    assert body["status"] in {
        "aprobado",
        "requiere_revision",
        "rechazado",
    }

    assert "scores" in body
    assert "relevancia" in body["scores"]
    assert "coherencia" in body["scores"]
    assert "adaptacion_didactica" in body["scores"]
    assert "informacion_respaldada" in body["scores"]

    assert isinstance(
        body["informacion_no_respaldada"],
        bool,
    )

    assert isinstance(body["observaciones"], list)


def test_valid_flashcards_returns_evaluation():
    """Flashcards válidas deben ser evaluadas y responder 200."""
    payload = load_mock(
        "evaluation_flashcards_valid_v1.json"
    )

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body["document_id"] == "DOC-001"
    assert body["format"] == "flashcards"

    assert body["status"] in {
        "aprobado",
        "requiere_revision",
        "rechazado",
    }

    assert "scores" in body

    assert isinstance(
        body["informacion_no_respaldada"],
        bool,
    )

    assert isinstance(body["observaciones"], list)


def test_request_without_learning_objective_returns_evaluation():
    """
    learning_objective es opcional y no debe impedir la evaluación.
    """
    payload = load_mock(
        "evaluation_quiz_valid_v1.json"
    )

    payload["generation_context"].pop(
        "learning_objective"
    )

    response = client.post("/evaluate", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body["document_id"] == "DOC-001"
    assert body["format"] == "quiz"

    assert body["status"] in {
        "aprobado",
        "requiere_revision",
        "rechazado",
    }


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
