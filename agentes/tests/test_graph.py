"""
Tests del nuevo Grafo Lineal (Investigador -> Redactor -> Fin).
Arquitectura Sprint 4: La orquestación HTTP la hace Backend, no Agentes.
Aquí probamos que el motor procesa el RAG, genera, y es capaz de recibir feedback inyectado.
"""
import pytest
from pydantic import ValidationError

from agentes.agent_v1 import AgentV1
from agentes.graph import (
    compilar_grafo_generacion,
    compilar_subgrafo_formato,
    traducir_respuesta_evaluador,
    ContratoEvaluadorError,
    EvaluacionSinVeredicto
)
from agentes.state import new_agent_state, new_format_state, ordenar_resultados
from agentes.rag.models import Chunk, SearchResult

# ----------------------------------------------------------------------
# Dobles de prueba (Mocks)
# ----------------------------------------------------------------------
class RetrieverFalso:
    def __init__(self, resultados=None, error=None):
        self.resultados = resultados or []
        self.error = error
        self.llamadas = []

    def retrieve(self, query, top_k=5, document_id=None, metadata_filters=None):
        self.llamadas.append({"query": query, "metadata_filters": metadata_filters})
        if self.error:
            raise self.error
        return self.resultados

class AgenteFalso:
    def __init__(self, retriever):
        self.retriever = retriever
        self.llamadas = []

    def generate_from_context(self, **kw):
        self.llamadas.append(kw)
        # Devolvemos un contenido válido dummy
        if kw["formato"] == "quiz":
            content = {"title": "T", "instructions": "I", "questions": [{"question_id": "q1", "question": "Q", "options": ["A", "B"], "correct_answer": "A", "explanation": "E"}]}
        else:
            content = {"title": "T", "summary": "S", "conclusion": "C"}
        return {"status": "success", "content": content, "sources_used": [], "error_message": None, "error": None}

    def extract_metadata_from_context(self, contexto, niche="", titulo=None):
        return {
            "status": "success",
            "content": {"key_concepts": ["A"], "prerequisites": ["B"], "estimated_time_minutes": 5},
            "error_message": None, "error": None,
            "document_title": "doc.pdf", "document_description": "Desc"
        }

def hallazgo(chunk_id, texto):
    return SearchResult(chunk_id, texto, 1.5, {"document_id": "d1", "source": "doc.pdf"})

# ----------------------------------------------------------------------
# Tests de Traducción del Contrato V2
# ----------------------------------------------------------------------
def test_traducir_respuesta_v2_correcta():
    payload_data_ia = {
        "document_id": "d1",
        "format": "quiz",
        "verdict": "requires_revision",
        "heuristic_scores": None,
        "semantic_evaluation": {
            "status": "success",
            "scores": {"relevance": 4.5, "coherence": 4.0, "didactic_adaptation": 3.0, "content_support": 4.0},
            "observations": [{"dimension": "didactic_adaptation", "severity": "high", "message": "Lenguaje complejo", "item_id": "q1"}],
            "recommendations": [],
            "unsupported_information": [],
            "error_code": None, "error_message": None, "model": "gemini", "prompt_version": "v1", "latency_ms": 100
        },
        "evaluator_version": "2.0", "rubric_version": "1.0"
    }
    
    feedback = traducir_respuesta_evaluador(payload_data_ia, document_id="d1", formato="quiz")
    
    assert feedback["approved"] is False
    assert feedback["verdict"] == "requires_revision"
    assert "Lenguaje complejo" in feedback["issues"][0]
    assert "high" in feedback["issues"][0]
    assert feedback["reviewed"] is True

def test_traducir_respuesta_verdict_nulo_lanza_excepcion():
    payload_data_ia = {
        "document_id": "d1", "format": "quiz", "verdict": None, "heuristic_scores": None,
        "semantic_evaluation": {
            "status": "failed", "scores": None, "observations": [], "recommendations": [], "unsupported_information": [],
            "error_code": "timeout", "error_message": None, "model": None, "prompt_version": None, "latency_ms": None
        },
        "evaluator_version": "2.0", "rubric_version": "1.0"
    }
    with pytest.raises(EvaluacionSinVeredicto) as exc:
        traducir_respuesta_evaluador(payload_data_ia)
    assert "timeout" in str(exc.value)

# ----------------------------------------------------------------------
# Tests del Grafo Global (Generación V1)
# ----------------------------------------------------------------------
def test_grafo_generacion_ejecuta_rag_y_fanout():
    agente = AgenteFalso(RetrieverFalso([hallazgo("c1", "texto de prueba")]))
    grafo = compilar_grafo_generacion(agente)
    
    estado_inicial = new_agent_state(document_id="d1", profile="p", niche="n", detail_level="d", formats=["quiz", "tldr"])
    estado_final = grafo.invoke(estado_inicial, {"max_concurrency": 2})
    
    resultados = ordenar_resultados(estado_final["final_results"], ["quiz", "tldr"])
    
    assert len(resultados) == 2
    assert resultados[0]["status"] == "success"
    assert resultados[1]["status"] == "success"
    assert estado_final["learning_metadata_status"] == "success"
    assert len(agente.llamadas) == 2  # Se llamó a Gemini para Quiz y TLDR

# ----------------------------------------------------------------------
# Tests del Subgrafo de Corrección (Para el futuro endpoint /revise)
# ----------------------------------------------------------------------
def test_subgrafo_formato_inyecta_feedback_en_llm():
    agente = AgenteFalso(RetrieverFalso([]))
    subgrafo = compilar_subgrafo_formato(agente)
    
    # Simulamos un estado que Backend nos enviaría tras un rechazo
    estado_base = new_agent_state(document_id="d1", profile="p", niche="n", detail_level="d", formats=["quiz"])
    estado_formato = new_format_state(estado_base, "quiz")
    
    # Inyectamos el feedback simulado de Data/IA
    estado_formato["feedback"] = {
        "approved": False,
        "issues": ["El contenido inventa datos sobre finanzas."],
        "suggestions": ["Cíñete al contexto."],
        "reviewed": True
    }
    
    resultado = subgrafo.invoke(estado_formato)
    
    # Verificamos que el Redactor recibió las instrucciones de corrección
    llamada_llm = agente.llamadas[0]
    instrucciones_extra = llamada_llm["extra_instructions"]
    
    assert "El contenido inventa datos" in instrucciones_extra
    assert "Cíñete al contexto" in instrucciones_extra
    assert resultado["outcome"]["status"] == "success"