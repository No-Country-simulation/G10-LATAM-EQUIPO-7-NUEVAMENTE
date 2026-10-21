import pytest
from fastapi.testclient import TestClient
from agentes.api import app, _revision_cache
from agentes.rag.models import SearchResult

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
            return {"outcome": {"status": "success", "content": {"title": "Nuevo Quiz"}, "error": None}}
            
    monkeypatch.setattr("agentes.api.compilar_subgrafo_formato", lambda x: MockGraph())
    
    payload = payload_base()
    
    r1 = client.post("/api/v1/revise", json=payload)
    assert r1.status_code == 200
    assert r1.json()["content"]["title"] == "Nuevo Quiz"
    assert invocaciones_grafo == 1
    
    r2 = client.post("/api/v1/revise", json=payload)
    assert r2.status_code == 200
    assert r2.json()["content"]["title"] == "Nuevo Quiz"
    assert invocaciones_grafo == 1

def test_revise_fallback_rag(monkeypatch):
    """Garantiza que si chunks_used viene vacío, el sistema llama al Retriever con la firma real."""
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
            return {"outcome": {"status": "success", "content": {"title": "Quiz RAG"}, "error": None}}
            
    monkeypatch.setattr("agentes.api.compilar_subgrafo_formato", lambda x: MockGraph())
    
    payload = payload_base("rev_test_02")
    payload["chunks_used"] = []
    
    r = client.post("/api/v1/revise", json=payload)
    assert r.status_code == 200
    assert len(mock_agent.retriever.calls) == 1
    assert mock_agent.retriever.calls[0]["top_k"] == 5
    assert mock_agent.retriever.calls[0]["metadata_filters"] == {"document_id": "doc_123"}

def test_revise_error_propagation(monkeypatch):
    """Garantiza que los fallos del Revisor cumplen con el modelo ErrorDetail y limpian sources_used a [] (Caché y R1)."""
    class MockGraphError:
        def invoke(self, state):
            return {
                "outcome": {
                    "format": "quiz",
                    "status": "failed",
                    "content": None,
                    "sources_used": [{"text": "basura"}],
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
    assert r1.json()["sources_used"] == []
    
    r2 = client.post("/api/v1/revise", json=payload)
    assert r2.status_code == 503
    assert r2.json()["sources_used"] == []

def test_revise_includes_new_evidence_sources(monkeypatch):
    """Verifica que el Revisor usa Contrato V2 real y pasa la evidencia mixta al Generador."""
    
    from agentes.api import agent
    from agentes.rag.models import SearchResult
    
    retrieve_calls = []

    def fake_retrieve(query, top_k=5, metadata_filters=None):
        retrieve_calls.append({
            "query": query,
            "top_k": top_k,
            "metadata_filters": metadata_filters
        })
        return [
            SearchResult(
                chunk_id="chunk_new_001",
                text="Evidencia adicional recuperada.",
                score=0.91,
                metadata={"document_id": "doc_123", "source": "test.pdf"}
            )
        ]

    monkeypatch.setattr(agent.retriever, "retrieve", fake_retrieve)

    def fake_generate(**kwargs):
        contexto = kwargs.get("contexto", "")
        # Aserciones para confirmar que el contexto se mezcla
        assert "Contexto original." in contexto
        assert "Evidencia adicional recuperada." in contexto

        sources = kwargs.get("sources_used", [])
        serialized_sources = [
            s.model_dump() if hasattr(s, "model_dump") else (s.__dict__ if hasattr(s, "__dict__") else s)
            for s in sources
        ]
        return {
            "status": "success",
            "content": {"title": "Quiz corregido"},
            "sources_used": serialized_sources
        }

    monkeypatch.setattr(agent, "generate_from_context", fake_generate)
    
    payload = payload_base("rev_new_evidence")
    payload["chunks_used"] = [
        {
            "rank": 1,
            "chunk_id": "chunk_old_001",
            "document_id": "doc_123",
            "score": 0.5,
            "text": "Contexto original.",
        }
    ]
    
    # Contrato oficial V2 inyectado (reemplaza la estructura vieja)
    payload["evaluator_response"] = {
        "document_id": "doc_123",
        "format": "quiz",
        "verdict": "requires_revision",
        "heuristic_scores": {
            "relevance": 4.0, "coherence": 4.0, "didactic_adaptation": 4.0, "content_support": 2.0
        },
        "semantic_evaluation": {
            "status": "success",
            "scores": {
                "relevance": 4.0, "coherence": 4.0, "didactic_adaptation": 4.0, "content_support": 2.0
            },
            "observations": [
                {
                    "dimension": "content_support",
                    "severity": "high",
                    "message": "La afirmación requiere más respaldo contextual."
                }
            ],
            "recommendations": [],
            "unsupported_information": [],
        },
        "evaluator_version": "test-v2",
        "rubric_version": "test-v2",
    }
    
    response = client.post("/api/v1/revise", json=payload)
    
    assert response.status_code == 200
    assert len(retrieve_calls) == 1
    
    filtros = retrieve_calls[0].get("metadata_filters")
    assert filtros.get("document_id") == "doc_123"

    body = response.json()
    source_ids = {
        source.get("chunk_id")
        for source in body["sources_used"]
        if isinstance(source, dict) and "chunk_id" in source
    }
    assert "chunk_old_001" in source_ids, "El grafo perdió la fuente original."
    assert "chunk_new_001" in source_ids, "El grafo NO propagó la nueva fuente recuperada."