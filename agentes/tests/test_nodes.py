"""
Tests del nodo Redactor, el router y el nodo de cierre. No llaman a Gemini.

Las pruebas con `AgentV1` real simulan la respuesta de Gemini; la de LangGraph arma el lazo
completo Redactor <-> Revisor con un Revisor de mentira.
"""
import pytest
from types import SimpleNamespace

from google.genai import errors as genai_errors
from langgraph.graph import END, START, StateGraph

import agentes.agent_v1 as av
from agentes.agent_v1 import AgentV1
from agentes.errors import build_error
from agentes.generated_schemas import QuizContent, QuizItem
from agentes.nodes import (
    construir_instrucciones_revision,
    crear_nodo_redactor,
    nodo_finalizar,
    ruta_tras_redactor,
)
from agentes.rag.models import Chunk
from agentes.rag.vector_store import VectorStore
from agentes.state import FormatState, new_agent_state, new_format_state


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def estado_formato(formato="quiz", **cambios):
    base = new_agent_state(document_id="d", profile="p", niche="n", detail_level="avanzado", formats=[formato])
    base["retrieved_context"] = "contexto recuperado por el investigador"
    base["sources_used"] = [{"rank": 1, "chunk_id": "c1", "text": "t"}]
    estado = new_format_state(base, formato)
    estado.update(cambios)
    return estado


class AgenteFalso:
    """Reemplaza a AgentV1: devuelve resultados en orden y guarda las llamadas."""

    def __init__(self, *resultados):
        self.resultados = list(resultados)
        self.llamadas = []

    def generate_from_context(self, **kwargs):
        self.llamadas.append(kwargs)
        r = self.resultados.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def ok(contenido=None):
    return {"status": "success", "content": contenido or {"title": "t"}, "sources_used": [],
            "error_message": None, "error": None}


def fallo(codigo, mensaje="fallo"):
    return {"status": "failed", "content": None, "sources_used": [], "error_message": mensaje,
            "error": build_error(codigo, mensaje)}


# ----------------------------------------------------------------------
# Modo creación y modo reescritura
# ----------------------------------------------------------------------
def test_primer_intento_es_creacion_sin_instrucciones_y_sin_gastar_revision():
    agente = AgenteFalso(ok())
    r = crear_nodo_redactor(agente)(estado_formato())
    assert r == {"revision_count": 0, "current_content": {"title": "t"}, "current_error": None, "feedback": None}
    llamada = agente.llamadas[0]
    assert llamada["extra_instructions"] == ""
    assert llamada["contexto"] == "contexto recuperado por el investigador"  # no vuelve a buscar en el RAG


def test_reescritura_por_feedback_inyecta_problemas_sugerencias_e_historial_y_version_previa():
    agente = AgenteFalso(ok({"title": "v2"}))
    estado = estado_formato(
        revision_count=0,
        current_content={"title": "v1"},
        feedback={"approved": False, "issues": ["distractores débiles"], "suggestions": ["usa opciones plausibles"]},
        feedback_history=[{"approved": False, "issues": ["pregunta ambigua"]}],
    )
    r = crear_nodo_redactor(agente)(estado)
    assert r["revision_count"] == 1 and r["current_content"] == {"title": "v2"}
    assert r["feedback"] is None and r["current_error"] is None
    texto = agente.llamadas[0]["extra_instructions"]
    for esperado in ("REVISIÓN", "distractores débiles", "usa opciones plausibles", "pregunta ambigua", '"title": "v1"'):
        assert esperado in texto, esperado


def test_reescritura_por_salida_invalida_inyecta_el_mensaje_del_error():
    agente = AgenteFalso(ok())
    error = build_error("INVALID_MODEL_OUTPUT", "correct_answer debe coincidir con una de las options")
    r = crear_nodo_redactor(agente)(estado_formato(current_error=error))
    assert r["revision_count"] == 1 and r["current_error"] is None
    assert "correct_answer debe coincidir" in agente.llamadas[0]["extra_instructions"]


def test_instrucciones_vacias_si_no_hay_nada_que_corregir():
    assert construir_instrucciones_revision(estado_formato()) == ""


def test_problemas_repetidos_en_el_historial_no_se_duplican():
    fb = {"approved": False, "issues": ["Distractores débiles", "distractores  débiles"]}
    texto = construir_instrucciones_revision(estado_formato(feedback=fb, feedback_history=[fb]))
    assert texto.lower().count("distractores débiles") == 1


# ----------------------------------------------------------------------
# Manejo de errores: el estado registra el HECHO; el router decide
# ----------------------------------------------------------------------
def test_error_de_cuota_se_registra_en_current_error_y_no_se_pierde():
    agente = AgenteFalso(fallo("RESOURCE_EXHAUSTED", "cuota agotada"))
    r = crear_nodo_redactor(agente)(estado_formato())
    assert r["current_error"]["code"] == "RESOURCE_EXHAUSTED"
    assert "outcome" not in r  # el outcome lo construye solo nodo_finalizar


def test_excepcion_inesperada_del_agente_no_aborta_el_grafo():
    agente = AgenteFalso(RuntimeError("boom"))
    r = crear_nodo_redactor(agente)(estado_formato())
    assert r["current_error"]["code"] == "INTERNAL_ERROR"


def test_fallo_conserva_contenido_y_feedback_previos():
    agente = AgenteFalso(fallo("INVALID_MODEL_OUTPUT"))
    estado = estado_formato(current_content={"title": "v1"}, feedback={"approved": False, "issues": ["x"]})
    r = crear_nodo_redactor(agente)(estado)
    assert "current_content" not in r and "feedback" not in r  # no se tocan


@pytest.mark.parametrize("error,revision,max_rev,esperado", [
    (None, 0, 2, "revisor"),
    (build_error("INVALID_MODEL_OUTPUT", "x"), 0, 2, "redactor"),
    (build_error("INVALID_MODEL_OUTPUT", "x"), 1, 2, "redactor"),
    (build_error("INVALID_MODEL_OUTPUT", "x"), 2, 2, "finalizar"),   # sin presupuesto
    (build_error("RESOURCE_EXHAUSTED", "x"), 0, 2, "finalizar"),     # cuota: no se revisa
    (build_error("PROVIDER_UNAVAILABLE", "x"), 0, 2, "finalizar"),
    (build_error("PROVIDER_AUTH_ERROR", "x"), 0, 2, "finalizar"),
    (build_error("NO_CONTEXT", "x"), 0, 2, "finalizar"),
])
def test_router_tras_redactor(error, revision, max_rev, esperado):
    estado = estado_formato(current_error=error, revision_count=revision, max_revisions=max_rev)
    assert ruta_tras_redactor(estado) == esperado


def test_finalizar_construye_el_outcome_con_la_forma_del_contrato():
    ok_ = nodo_finalizar(estado_formato(current_content={"title": "t"}))["outcome"]
    assert ok_["status"] == "success" and ok_["content"] == {"title": "t"} and ok_["error"] is None
    assert ok_["sources_used"] and set(ok_) == {
        "format", "status", "content", "sources_used", "error_message", "error", "execution_time_seconds"}

    cuota = nodo_finalizar(estado_formato(current_error=build_error("RESOURCE_EXHAUSTED", "cuota")))["outcome"]
    assert cuota["status"] == "failed" and cuota["error"]["code"] == "RESOURCE_EXHAUSTED"
    assert cuota["content"] is None and cuota["sources_used"] == [] and cuota["error_message"] == "cuota"

    sin_ctx = nodo_finalizar(estado_formato(current_error=build_error("NO_CONTEXT", "sin contexto")))["outcome"]
    assert sin_ctx["status"] == "no_results"


# ----------------------------------------------------------------------
# Con el AgentV1 REAL: agent.answer nunca lanza, así que el error debe leerse del dict
# ----------------------------------------------------------------------
@pytest.fixture
def agente_real(monkeypatch):
    monkeypatch.setattr(av.time, "sleep", lambda s: None)
    return AgentV1(VectorStore())


def quiz_valido():
    item = QuizItem(question_id="q1", question="¿?", options=["a", "b"], correct_answer="a", explanation="e")
    return QuizContent(title="t", instructions="i", questions=[item])


def test_agente_real_con_429_el_nodo_registra_el_error_y_no_lo_da_por_exito(monkeypatch, agente_real):
    def cuota(model, contents, config):
        raise genai_errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})

    monkeypatch.setattr(av, "client", SimpleNamespace(models=SimpleNamespace(generate_content=cuota)))
    r = crear_nodo_redactor(agente_real)(estado_formato())
    assert r["current_error"]["code"] == "RESOURCE_EXHAUSTED" and r["current_error"]["retryable"] is True
    assert "current_content" not in r


def test_agente_real_las_instrucciones_de_revision_llegan_al_prompt(monkeypatch, agente_real):
    prompts = []

    def gemini(model, contents, config):
        prompts.append(contents)
        return SimpleNamespace(parsed=quiz_valido())

    monkeypatch.setattr(av, "client", SimpleNamespace(models=SimpleNamespace(generate_content=gemini)))
    nodo = crear_nodo_redactor(agente_real)
    nodo(estado_formato())
    nodo(estado_formato(feedback={"approved": False, "issues": ["distractores débiles"]}))
    assert "distractores débiles" not in prompts[0] and "distractores débiles" in prompts[1]
    assert prompts[0] != prompts[1]
    assert "contexto recuperado por el investigador" in prompts[1]


def test_agente_real_sin_contexto_devuelve_no_results_sin_llamar_a_gemini(monkeypatch, agente_real):
    llamadas = []
    monkeypatch.setattr(av, "client", SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **kw: llamadas.append(kw))))
    r = crear_nodo_redactor(agente_real)(estado_formato(retrieved_context=""))
    assert r["current_error"]["code"] == "NO_CONTEXT" and llamadas == []


# ----------------------------------------------------------------------
# Lazo completo en LangGraph: Redactor <-> Revisor <-> cierre
# ----------------------------------------------------------------------
def armar_subgrafo(agente, revisor):
    g = StateGraph(FormatState)
    g.add_node("redactor", crear_nodo_redactor(agente))
    g.add_node("revisor", revisor)
    g.add_node("finalizar", nodo_finalizar)

    def tras_revisor(s):
        from agentes.state import puede_revisar
        return "finalizar" if (not s.get("feedback") or not puede_revisar(s)) else "redactor"

    g.add_edge(START, "redactor")
    g.add_conditional_edges("redactor", ruta_tras_redactor, ["redactor", "revisor", "finalizar"])
    g.add_conditional_edges("revisor", tras_revisor, ["redactor", "finalizar"])
    g.add_edge("finalizar", END)
    return g.compile()


def revisor_que_rechaza(n):
    """Rechaza las primeras n versiones y luego aprueba."""
    def revisor(s):
        if s.get("revision_count", 0) < n:
            fb = {"approved": False, "issues": [f"problema {s.get('revision_count', 0) + 1}"]}
            return {"feedback": fb, "feedback_history": [fb]}
        return {"feedback": None, "feedback_history": [{"approved": True}]}
    return revisor


def test_lazo_completo_crea_y_reescribe_hasta_que_el_revisor_aprueba():
    agente = AgenteFalso(ok({"v": 1}), ok({"v": 2}), ok({"v": 3}))
    out = armar_subgrafo(agente, revisor_que_rechaza(2)).invoke(estado_formato(max_revisions=2))
    assert len(agente.llamadas) == 3  # 1 creación + 2 reescrituras (max_revisions=2)
    assert out["outcome"]["status"] == "success" and out["outcome"]["content"] == {"v": 3}
    assert out["revision_count"] == 2
    assert "problema 1" in agente.llamadas[1]["extra_instructions"]
    assert "problema 1" in agente.llamadas[2]["extra_instructions"] and "problema 2" in agente.llamadas[2]["extra_instructions"]


def test_lazo_completo_el_presupuesto_de_revisiones_se_respeta():
    agente = AgenteFalso(ok({"v": 1}), ok({"v": 2}), ok({"v": 3}), ok({"v": 4}))
    out = armar_subgrafo(agente, revisor_que_rechaza(99)).invoke(estado_formato(max_revisions=2))
    assert len(agente.llamadas) == 3 and out["revision_count"] == 2  # nunca más de 1 + max_revisions


def test_lazo_completo_la_cuota_cierra_de_inmediato_sin_gastar_revisiones():
    agente = AgenteFalso(fallo("RESOURCE_EXHAUSTED", "cuota agotada"))
    out = armar_subgrafo(agente, revisor_que_rechaza(0)).invoke(estado_formato(max_revisions=3))
    assert len(agente.llamadas) == 1
    assert out["outcome"]["status"] == "failed" and out["outcome"]["error"]["code"] == "RESOURCE_EXHAUSTED"


def test_lazo_completo_la_salida_invalida_se_reescribe_con_el_mensaje_del_validador():
    agente = AgenteFalso(fallo("INVALID_MODEL_OUTPUT", "correct_answer fuera de options"), ok({"v": 2}))
    out = armar_subgrafo(agente, revisor_que_rechaza(0)).invoke(estado_formato(max_revisions=2))
    assert len(agente.llamadas) == 2
    assert "correct_answer fuera de options" in agente.llamadas[1]["extra_instructions"]
    assert out["outcome"]["status"] == "success" and out["revision_count"] == 1


def test_lazo_completo_salida_invalida_sin_presupuesto_falla_con_su_error():
    agente = AgenteFalso(fallo("INVALID_MODEL_OUTPUT"), fallo("INVALID_MODEL_OUTPUT"), fallo("INVALID_MODEL_OUTPUT"))
    out = armar_subgrafo(agente, revisor_que_rechaza(0)).invoke(estado_formato(max_revisions=1))
    assert len(agente.llamadas) == 2  # 1 creación + 1 reescritura
    assert out["outcome"]["status"] == "failed" and out["outcome"]["error"]["code"] == "INVALID_MODEL_OUTPUT"
