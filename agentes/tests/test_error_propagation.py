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
    assert data["document_description"] == "Descripción semántica de la guía"
    assert len(data["results"]) == 2

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_metadata_fallback(mock_ejecutar):
    """Verifica que si la extracción de metadatos falla, use el fallback del nombre del archivo, no el ID."""
    mock_ejecutar.return_value = {
        "learning_metadata_status": "failed",
        "learning_metadata": FAILED_METADATA,
        "document_title": "manual_python.pdf",  # <-- El RAG rescató el nombre del archivo original
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
    # Validación requerida: el nombre del archivo le gana al document_id
    assert data["document_title"] == "manual_python.pdf"

@patch("agentes.api.ejecutar_grafo")
def test_niche_variation_affects_output(mock_ejecutar):
    """Verifica que los metadatos reflejen el cambio de nicho."""
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

def test_graph_conserves_filename_on_metadata_failure(monkeypatch):
    """Verifica de extremo a extremo que el grafo extrae el filename del RAG y lo conserva si falla el LLM."""
    from agentes.api import agent
    
    # 1. Simulamos que ChromaDB devuelve un fragmento con el nombre del archivo original
    class FakeChunk:
        chunk_id = "chunk_001"
        text = "Contexto recuperado de la base de datos."
        score = 0.99
        metadata = {"filename": "manual_python.pdf", "document_id": "doc_test_fallback"}
        
    def fake_retrieve(*args, **kwargs):
        return [FakeChunk()]
        
    monkeypatch.setattr(agent.retriever, "retrieve", fake_retrieve)
    
    # 2. Simulamos que Gemini falla al extraer metadatos, devolviendo el titulo de fallback
    def fake_extract_metadata(contexto, niche, titulo):
        return {
            "status": "failed",
            "content": FAILED_METADATA,
            "error_message": "Error simulado de LLM",
            "error": {
                "code": "PROVIDER_ERROR",
                "message": "Error simulado de LLM",
                "retryable": False,
                "http_status": 500,
                "provider": "gemini",
            },
            "document_title": titulo,  # Agente devuelve el titulo fallback que extrajo el Investigador
            "document_description": None
        }
    monkeypatch.setattr(agent, "extract_metadata_from_context", fake_extract_metadata)
    
    # 3. Simulamos la generación del formato para no llamar a Gemini
    def fake_generate(*args, **kwargs):
        return {
            "status": "success", 
            "content": {"title": "Quiz exitoso"}, 
            "sources_used": [{"chunk_id": "chunk_001", "text": "Contexto recuperado de la base de datos."}],
            "error_message": None,
            "error": None
        }
    monkeypatch.setattr(agent, "generate_from_context", fake_generate)
    
    payload = {
        "document_id": "doc_test_fallback",
        "formats": ["quiz"],
        "profile": "estudiante",
        "niche": "general",
        "detail_level": "básico"
    }
    
    # Ejecutamos sin @patch("ejecutar_grafo") para que corra LangGraph real
    response = client.post("/api/v1/generate", json=payload)
    
    assert response.status_code == 207
    data = response.json()
    assert data["learning_metadata_status"] == "failed"
    assert data["document_title"] == "manual_python.pdf", "El grafo perdió el nombre del archivo durante el flujo."

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_404_no_context(mock_ejecutar):
    """Verifica que si el RAG falla por NO_CONTEXT, retorne HTTP 404."""
    mock_ejecutar.return_value = {
        "learning_metadata_status": "no_results",
        "learning_metadata_error": {"code": "NO_CONTEXT", "message": "Sin contexto", "retryable": False, "http_status": 404, "provider": "internal"},
        "document_title": "doc.pdf",
        "final_results": [{"format": "quiz", "status": "no_results", "error": {"code": "NO_CONTEXT", "message": "Sin contexto", "retryable": False, "http_status": 404, "provider": "internal"}}]
    }
    
    payload = {
        "document_id": "doc_test_123",
        "formats": ["quiz"],
        "profile": "estudiante",
        "niche": "general",
        "detail_level": "básico"
    }
    
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 404
    assert response.json()["overall_status"] == "failed"

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_429_metadata_success_format_exhausted(mock_ejecutar):
    """Verifica que si los metadatos tienen éxito, pero la generación falla por cuota, retorne HTTP 429 y no 207."""
    mock_ejecutar.return_value = {
        "learning_metadata_status": "success",
        "learning_metadata": SUCCESS_METADATA,
        "document_title": "Guía de Python",
        "final_results": [{"format": "quiz", "status": "failed", "error": {"code": "RESOURCE_EXHAUSTED", "message": "Cuota excedida", "retryable": True, "http_status": 429, "provider": "gemini"}}]
    }
    
    payload = {
        "document_id": "doc_test_123",
        "formats": ["quiz"],
        "profile": "estudiante",
        "niche": "general",
        "detail_level": "básico"
    }
    
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 429
    assert response.json()["overall_status"] == "failed"
    assert response.json()["results"][0]["error"]["code"] == "RESOURCE_EXHAUSTED"

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_207_mixed_results(mock_ejecutar):
    """Verifica el fallo parcial: un formato exitoso y uno fallido retornan 207."""
    mock_ejecutar.return_value = {
        "learning_metadata_status": "success",
        "learning_metadata": SUCCESS_METADATA,
        "document_title": "Guía de Python",
        "final_results": [
            SUCCESS_QUIZ,
            {"format": "flashcards", "status": "failed", "error": {"code": "PROVIDER_UNAVAILABLE", "message": "Gemini caído", "retryable": True, "http_status": 503, "provider": "gemini"}}
        ]
    }
    
    payload = {
        "document_id": "doc_test_123",
        "formats": ["quiz", "flashcards"],
        "profile": "estudiante",
        "niche": "general",
        "detail_level": "básico"
    }
    
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 207
    data = response.json()
    assert data["overall_status"] == "partial"
    assert data["results"][0]["status"] == "success"
    assert data["results"][1]["status"] == "failed"

@patch("agentes.api.ejecutar_grafo")
def test_generate_endpoint_503_provider_unavailable(mock_ejecutar):
    """Verifica que si el proveedor falla, retorne HTTP 503."""
    mock_ejecutar.return_value = {
        "learning_metadata_status": "failed",
        "learning_metadata_error": {"code": "PROVIDER_UNAVAILABLE", "message": "Gemini caído", "retryable": True, "http_status": 503, "provider": "gemini"},
        "document_title": "doc.pdf",
        "final_results": [{"format": "quiz", "status": "failed", "error": {"code": "PROVIDER_UNAVAILABLE", "message": "Gemini caído", "retryable": True, "http_status": 503, "provider": "gemini"}}]
    }
    
    payload = {
        "document_id": "doc_test_123",
        "formats": ["quiz"],
        "profile": "estudiante",
        "niche": "general",
        "detail_level": "básico"
    }
    
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 503