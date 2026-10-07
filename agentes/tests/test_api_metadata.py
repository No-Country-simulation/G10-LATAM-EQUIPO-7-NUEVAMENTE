import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from agentes.api import app

# Inicializamos el cliente de pruebas de FastAPI
client = TestClient(app)

# ==========================================
# MOCKS (Simulaciones de respuesta de Gemini)
# ==========================================
SUCCESS_METADATA = {
    "status": "success",
    "content": {
        "key_concepts": ["Concepto A", "Concepto B"],
        "prerequisites": ["Conocimiento previo"],
        "estimated_time_minutes": 15
    }
}

FAILED_METADATA = {
    "status": "failed",
    "content": None
}

SUCCESS_QUIZ = {
    "status": "success",
    "content": {"title": "Quiz", "instructions": "Instrucciones", "questions": []},
    "sources_used": []
}

SUCCESS_FLASHCARDS = {
    "status": "success",
    "content": {"title": "Flashcards", "instructions": "Instrucciones", "cards": []},
    "sources_used": []
}

# ==========================================
# PRUEBAS AUTOMATIZADAS
# ==========================================

@patch("agentes.api.agent.extract_learning_metadata")
@patch("agentes.api.agent.answer")
def test_generate_endpoint_root_metadata_success(mock_answer, mock_extract):
    """
    Validación 1 y 3: Verifica que learning_metadata viaje en la raíz y que 
    los resultados de Quiz/Flashcards mantengan su contrato limpio.
    """
    # Configuramos el mock de metadatos para que sea exitoso
    mock_extract.return_value = SUCCESS_METADATA
    
    # Configuramos el mock de answer para que devuelva Quiz y luego Flashcards
    mock_answer.side_effect = [SUCCESS_QUIZ, SUCCESS_FLASHCARDS]

    payload = {
        "document_id": "doc_test_123",
        "formats": ["quiz", "flashcards"],
        "profile": "profesional",
        "niche": "tecnología",
        "detail_level": "avanzado"
    }

    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Validación 1: Llaves en la raíz
    assert "document_id" in data
    assert "learning_metadata" in data
    assert "results" in data

    # Verificamos que los datos se inyectaron bien
    assert data["learning_metadata"]["estimated_time_minutes"] == 15
    
    # Validación 3: Los formatos mantienen su contrato y no incluyen learning_metadata
    results = data["results"]
    assert len(results) == 2
    assert results[0]["format"] == "quiz"
    assert "learning_metadata" not in results[0]["content"]
    
    assert results[1]["format"] == "flashcards"
    assert "learning_metadata" not in results[1]["content"]


@patch("agentes.api.agent.extract_learning_metadata")
@patch("agentes.api.agent.answer")
def test_generate_endpoint_metadata_fallback(mock_answer, mock_extract):
    """
    Validación 2: Verifica que si la extracción de metadatos falla, 
    se devuelva el fallback por defecto y se sigan generando los formatos.
    """
    # Configuramos el mock para simular que Gemini falló sacando los metadatos
    mock_extract.return_value = FAILED_METADATA
    
    # El formato (Quiz) sigue funcionando normal
    mock_answer.return_value = SUCCESS_QUIZ

    payload = {
        "document_id": "doc_test_fallback",
        "formats": ["quiz"],
        "profile": "estudiante",
        "niche": "general",
        "detail_level": "básico"
    }

    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Validación 2: Comportamiento estricto de Fallback
    fallback_metadata = data["learning_metadata"]
    assert fallback_metadata["key_concepts"] == []
    assert fallback_metadata["prerequisites"] == []
    assert fallback_metadata["estimated_time_minutes"] == 0

    # Verificamos que el formato no se rompió por culpa del fallo de los metadatos
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "success"