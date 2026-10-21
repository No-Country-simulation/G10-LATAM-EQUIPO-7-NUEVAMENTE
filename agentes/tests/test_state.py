import pytest
from agentes.state import (
    construir_query_rag,
    new_agent_state,
    new_format_state,
    puede_revisar,
    error_permite_revision,
    ordenar_resultados,
    DEFAULT_MAX_REVISIONS
)

# ==========================================
# TESTS DE ESTADO DE LANGGRAPH
# ==========================================

def test_construir_query_rag():
    """Valida que la query se construya correctamente según la prioridad."""
    # 1. Si hay query directa, ignora lo demás
    assert construir_query_rag("TI", "dev", "alto", query="mi query") == "mi query"
    
    # 2. Si no hay query, pero hay objetivo, concatena el objetivo
    esperado = "Conceptos principales sobre TI para un perfil dev con nivel alto. Objetivo: aprender"
    assert construir_query_rag("TI", "dev", "alto", learning_objective="aprender") == esperado
    
    # 3. Sin query y sin objetivo
    esperado_basico = "Conceptos principales sobre TI para un perfil dev con nivel alto."
    assert construir_query_rag("TI", "dev", "alto") == esperado_basico


def test_new_agent_state_inicializacion():
    """Valida que el estado global nazca con las llaves correctas y vacías."""
    state = new_agent_state(
        document_id="doc1", 
        profile="dev", 
        niche="TI", 
        detail_level="alto", 
        formats=["quiz", "tldr"]
    )
    
    assert state["document_id"] == "doc1"
    assert state["formats_requested"] == ["quiz", "tldr"]
    assert state["final_results"] == []  # El acumulador debe nacer vacío
    assert "started_at" in state


def test_new_format_state_hereda_correctamente():
    """Valida que el estado individual del formato herede bien del estado global."""
    agent_state = new_agent_state(
        document_id="doc1", profile="dev", niche="TI", detail_level="alto", formats=["quiz"]
    )
    # Simulamos que el RAG ya hizo su trabajo
    agent_state["retrieved_context"] = "contexto_prueba"

    format_state = new_format_state(agent_state, "quiz")
    
    assert format_state["format"] == "quiz"
    assert format_state["document_id"] == "doc1"
    assert format_state["retrieved_context"] == "contexto_prueba"
    assert format_state["revision_count"] == 0  # Inicia sin revisiones
    assert format_state["feedback_history"] == []


def test_puede_revisar():
    """Valida la matemática básica del presupuesto de reintentos."""
    state = {"revision_count": 0, "max_revisions": 2}
    assert puede_revisar(state) is True

    state["revision_count"] = 1
    assert puede_revisar(state) is True
    
    state["revision_count"] = 2
    assert puede_revisar(state) is False


def test_error_permite_revision():
    """Valida que solo errores específicos entren al lazo de revisión."""
    error_revisable = {"code": "INVALID_MODEL_OUTPUT", "message": "Mal JSON"}
    assert error_permite_revision(error_revisable) is True

    error_fatal = {"code": "RESOURCE_EXHAUSTED", "message": "Cuota"}
    assert error_permite_revision(error_fatal) is False

    assert error_permite_revision(None) is False


def test_ordenar_resultados():
    """Valida que los resultados concurrentes se ordenen como los pidió el usuario."""
    # Simulamos que TLDR terminó primero por ser más rápido, aunque se pidió segundo
    resultados_desordenados = [
        {"format": "tldr", "status": "success"},
        {"format": "quiz", "status": "success"}
    ]
    
    # El usuario los pidió en orden: quiz, luego tldr
    ordenados = ordenar_resultados(resultados_desordenados, ["quiz", "tldr"])
    
    assert ordenados[0]["format"] == "quiz"
    assert ordenados[1]["format"] == "tldr"