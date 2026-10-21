import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from agentes.api import app

client = TestClient(app)

SUCCESS_METADATA = {
    "key_concepts": ["Listas", "Diccionarios", "Funciones"],
    "prerequisites": ["Lógica básica"],
    "estimated_time_minutes": 15
}

FAILED_METADATA = {
    "key_concepts": ["Error al extraer conceptos"],
    "prerequisites": ["No se pudieron determinar"],
    "estimated_time_minutes": 0
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
    """Verifica que learning_metadata viaje en la raíz y use claves reales de LangGraph."""
    mock_ejecutar.return_value = {
        "learning_metadata_status": "success",
        "learning_metadata": SUCCESS_METADATA,
        "document_title": "Guía de Python",
        "document_description": "Descripción semántica de la guía",
        "final_results": [SUCCESS_QUIZ, SUCCESS_FLASHCARDS]
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
    assert data["document_title"] == "Guía de Python"
    assert len(data["results"]) == 2

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_metadata_fallback(mock_ejecutar):
    """Verifica que si la extracción de metadatos falla, se use el nombre original del archivo."""
    mock_ejecutar.return_value = {
        "learning_metadata_status": "failed",
        "learning_metadata": FAILED_METADATA,
        "document_title": "manual_python.pdf", # Simulando que el fallback de agent_v1 rescató el archivo
        "final_results": [SUCCESS_QUIZ]
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
    # Validamos que se devuelve el nombre original del archivo y no un ID genérico o un Título no generado
    assert data["document_title"] == "manual_python.pdf"

@patch("agentes.api.ejecutar_grafo")
def test_niche_variation_affects_output(mock_ejecutar):
    """Verifica que los metadatos reflejen el cambio."""
    niche_metadata = {
        "key_concepts": ["Apalancamiento", "Gestión de riesgo", "Margin call"],
        "prerequisites": ["Matemáticas financieras básicas"],
        "estimated_time_minutes": 20
    }
    mock_ejecutar.return_value = {
        "learning_metadata_status": "success",
        "learning_metadata": niche_metadata,
        "document_title": "Finanzas Avanzadas",
        "final_results": [SUCCESS_QUIZ]
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
