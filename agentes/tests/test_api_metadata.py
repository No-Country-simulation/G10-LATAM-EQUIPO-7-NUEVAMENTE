import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from agentes.api import app

client = TestClient(app)

SUCCESS_METADATA = {
    "status": "success",
    "content": {
        "document_title": "Guía de Python",
        "key_concepts": ["Listas", "Diccionarios", "Funciones"],
        "prerequisites": ["Lógica básica"],
        "estimated_time_minutes": 15
    }
}

FAILED_METADATA = {
    "status": "failed",
    "content": None,
    "error_message": "Timeout del LLM",
    "error": {
        "code": "PROVIDER_TIMEOUT",
        "message": "Timeout del LLM",
        "retryable": True,
        "http_status": 504,
        "provider": "gemini"
    }
}

SUCCESS_QUIZ = {
    "format": "quiz",
    "status": "success",
    "content": {"title": "Quiz de Python"},
    "sources_used": [{"chunk_id": "1"}],
    "execution_time_seconds": 1.5
}

SUCCESS_FLASHCARDS = {
    "format": "flashcards",
    "status": "success",
    "content": {"title": "Flashcards de Python"},
    "sources_used": [{"chunk_id": "2"}],
    "execution_time_seconds": 1.2
}

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_root_metadata_success(mock_ejecutar):
    """Verifica que learning_metadata viaje en la raíz usando LangGraph."""
    mock_ejecutar.return_value = {
        "metadata_result": SUCCESS_METADATA,
        "format_results": [SUCCESS_QUIZ, SUCCESS_FLASHCARDS]
    }
    
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
    assert data["learning_metadata"]["document_title"] == "Guía de Python"
    assert len(data["results"]) == 2

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_metadata_fallback(mock_ejecutar):
    """Verifica que si la extracción de metadatos falla, se devuelva 207 y el fallback."""
    mock_ejecutar.return_value = {
        "metadata_result": FAILED_METADATA,
        "format_results": [SUCCESS_QUIZ]
    }
    
    payload = {
        "document_id": "doc_test_fallback",
        "formats": ["quiz"],
        "profile": "estudiante",
        "niche": "general",
        "detail_level": "básico"
    }
    
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 207
    data = response.json()
    assert data["learning_metadata_status"] == "failed"
    assert data["learning_metadata"]["document_title"] == "Título no generado"

@patch("agentes.api.ejecutar_grafo")
def test_niche_variation_affects_output(mock_ejecutar):
    """Verifica que al cambiar el nicho, los metadatos reflejen el cambio (Simulado vía LangGraph)."""
    niche_metadata = {
        "status": "success",
        "content": {
            "key_concepts": ["Apalancamiento", "Gestión de riesgo", "Margin call"],
            "prerequisites": ["Matemáticas financieras básicas"],
            "estimated_time_minutes": 20,
            "document_title": "Finanzas Avanzadas"
        }
    }
    mock_ejecutar.return_value = {
        "metadata_result": niche_metadata,
        "format_results": [SUCCESS_QUIZ]
    }
    
    payload = {
        "document_id": "doc_test_nicho",
        "formats": ["quiz"],
        "profile": "inversionista",
        "niche": "finanzas",
        "detail_level": "avanzado"
    }
    
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["learning_metadata"]["key_concepts"] == ["Apalancamiento", "Gestión de riesgo", "Margin call"]