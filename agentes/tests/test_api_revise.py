import pytest
from fastapi.testclient import TestClient
from agentes.api import app, _revision_cache

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_cache():
    """Limpia el caché de idempotencia antes de cada test para no contaminar el estado."""
    _revision_cache.clear()

def payload_base(revision_id="rev_test_01"):
    return {
        "revision_id": revision_id,
        "original_format_id": "fmt_001",
        "document_id": "doc_123",
        "format": "quiz",
        "generation_context": {
            "profile": "senior",
            "niche": "arquitectura",
            "detail_level": "experto"
        },
        "previous_content": {"title": "Viejo Quiz"},
        "chunks_used": [{"text": "Contexto inicial"}],
        "evaluator_response": {"verdict": "requires_revision"}
    }

def test_revise_idempotency(monkeypatch):
    """Garantiza que llamadas duplicadas con el mismo revision_id no ejecuten el motor 2 veces."""
    invocaciones_grafo = 0

    class MockGraph:
        def invoke(self, state):
            nonlocal invocaciones_grafo
            invocaciones_grafo += 1
            return {"outcome": {"content": {"title": "Nuevo Quiz"}, "error": None}}
            
    monkeypatch.setattr("agentes.api.compilar_subgrafo_formato", lambda x: MockGraph())
    
    payload = payload_base()
    
    # 1er Llamado: Ejecuta LangGraph
    r1 = client.post("/api/v1/revise", json=payload)
    assert r1.status_code == 200
    assert r1.json()["content"]["title"] == "Nuevo Quiz"
    assert invocaciones_grafo == 1
    
    # 2do Llamado: Mismo revision_id, debe leer de caché
    r2 = client.post("/api/v1/revise", json=payload)
    assert r2.status_code == 200
    assert r2.json()["content"]["title"] == "Nuevo Quiz"
    assert invocaciones_grafo == 1  # ¡Sigue en 1, no invocó al grafo de nuevo!

def test_revise_fallback_rag(monkeypatch):
    """Garantiza que si chunks_used viene vacío, el sistema llama al Retriever con la firma real (top_k y metadata_filters)."""
    class MockRetriever:
        def __init__(self):
            self.calls = []

        def retrieve(self, query, top_k=5, metadata_filters=None):
            self.calls.append({
                "query": query,
                "top_k": top_k,
                "metadata_filters": metadata_filters,
            })
            class FakeChunk:
                text = "Texto desde ChromaDBFallback"
                def model_dump(self):
                    return {"text": "Texto desde ChromaDBFallback"}
            return [FakeChunk()]
            
    mock_agent = type("FakeAgent", (), {})()
    mock_agent.retriever = MockRetriever()
    
    monkeypatch.setattr("agentes.api.agent", mock_agent)
    
    class MockGraph:
        def invoke(self, state):
            assert "Texto desde ChromaDBFallback" in state["retrieved_context"]
            return {"outcome": {"content": {"title": "Quiz RAG"}, "error": None}}
            
    monkeypatch.setattr("agentes.api.compilar_subgrafo_formato", lambda x: MockGraph())
    
    payload = payload_base("rev_test_02")
    payload["chunks_used"] = []  # Forzamos el fallback
    
    r = client.post("/api/v1/revise", json=payload)
    assert r.status_code == 200
    
    # Validamos que el retriever fue llamado con los filtros correctos acordados
    assert len(mock_agent.retriever.calls) == 1
    assert mock_agent.retriever.calls[0]["top_k"] == 5
    assert mock_agent.retriever.calls[0]["metadata_filters"] == {"document_id": "doc_123"}

def test_revise_error_propagation(monkeypatch):
    """Garantiza que los fallos del Revisor cumplen con el modelo ErrorDetail completo y se guardan en caché."""
    class MockGraphError:
        def invoke(self, state):
            return {
                "outcome": {
                    "format": "quiz",
                    "status": "failed",
                    "content": None,
                    "sources_used": [],
                    "error_message": "Gemini caído",
                    "error": {
                        "code": "PROVIDER_UNAVAILABLE",
                        "message": "Gemini caído",
                        "retryable": True,
                        "http_status": 503,
                        "upstream_status": 503,
                        "provider": "gemini"
                    },
                    "execution_time_seconds": 0.01
                }
            }
            
    monkeypatch.setattr("agentes.api.compilar_subgrafo_formato", lambda x: MockGraphError())
    
    payload = payload_base("rev_test_03")
    r1 = client.post("/api/v1/revise", json=payload)
    assert r1.status_code == 503
    assert r1.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
    
    # Debe seguir devolviendo 503 por caché
    r2 = client.post("/api/v1/revise", json=payload)
    assert r2.status_code == 503