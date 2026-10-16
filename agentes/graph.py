"""
Grafo de LangGraph para la Generación y Corrección de Formatos.

Arquitectura alineada (Sprint 4):
* Agentes NO orquesta la evaluación HTTP. Backend es el responsable del ciclo de vida.
* Este módulo expone dos grafos:
  1. `compilar_grafo_generacion`: Grafo global (Map-Reduce) que ejecuta el Investigador (RAG),
     extrae metadatos y hace fan-out para generar la primera versión de múltiples formatos.
  2. `compilar_subgrafo_formato`: Grafo inteligente con nodo Revisor, lógica condicional de nueva evidencia
     y el Redactor Pedagógico. Se usa tanto internamente en el fan-out como externamente para la corrección.
"""
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .agent_v1 import ESQUEMAS_POR_FORMATO, AgentV1, _titulo_desde_resultados
from .errors import build_error, classify_exception
from .evaluator_contract import EvaluationResponseV2
from .nodes import crear_nodo_redactor, nodo_finalizar
from .state import (
    AgentState,
    FormatState,
    ReviewFeedback,
    construir_outcome,
    new_format_state,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENCY = 3


def max_concurrency_por_defecto() -> int:
    """Tope de formatos en paralelo para proteger cuotas (env GRAPH_MAX_CONCURRENCY)."""
    try:
        return max(1, int(os.getenv("GRAPH_MAX_CONCURRENCY", str(DEFAULT_MAX_CONCURRENCY))))
    except ValueError:
        return DEFAULT_MAX_CONCURRENCY


def _estado_de_error(error: Dict[str, Any]) -> str:
    return "no_results" if error.get("code") == "NO_CONTEXT" else "failed"


# ----------------------------------------------------------------------
# 1. INVESTIGADOR Y METADATOS (RAG global)
# ----------------------------------------------------------------------
def crear_nodo_investigador(agente: AgentV1, top_k: int = 5) -> Callable[[AgentState], Dict[str, Any]]:
    def nodo_investigador(state: AgentState) -> Dict[str, Any]:
        document_id = state["document_id"]
        logger.info("Investigador: document_id=%s", document_id)
        try:
            resultados = agente.retriever.retrieve(
                query=state["query_rag"], top_k=top_k, metadata_filters={"document_id": document_id}
            )
        except Exception as e:
            logger.exception("Investigador: la recuperación falló")
            return {"retrieved_context": "", "sources_used": [], "retrieval_error": classify_exception(e)}

        if not resultados:
            return {
                "retrieved_context": "",
                "sources_used": [],
                "retrieval_error": build_error("NO_CONTEXT", "No hay contenido indexado para el document_id solicitado."),
            }

        fuentes = [
            {
                "rank": rank,
                "chunk_id": r.chunk_id,
                "document_id": (r.metadata or {}).get("document_id", document_id),
                "score": getattr(r, "score", 0.0),
                "text": r.text,
            }
            for rank, r in enumerate(resultados, start=1)
        ]
        return {
            "retrieved_context": "\n\n".join(r.text for r in resultados),
            "sources_used": fuentes,
            "document_title": _titulo_desde_resultados(resultados),
            "retrieval_error": None,
        }

    return nodo_investigador


def crear_nodo_metadatos(agente: AgentV1) -> Callable[[AgentState], Dict[str, Any]]:
    def nodo_metadatos(state: AgentState) -> Dict[str, Any]:
        error = state.get("retrieval_error")
        if error:
            return {
                "learning_metadata": None,
                "learning_metadata_status": _estado_de_error(error),
                "learning_metadata_error": error,
            }
        try:
            r = agente.extract_metadata_from_context(
                contexto=state.get("retrieved_context", ""),
                niche=state["niche"],
                titulo=state.get("document_title"),
            )
        except Exception as e:
            logger.exception("Metadatos: excepción inesperada")
            return {
                "learning_metadata": None,
                "learning_metadata_status": "failed",
                "learning_metadata_error": classify_exception(e),
            }
        exito = r.get("status") == "success"
        return {
            "learning_metadata": r.get("content") if exito else None,
            "learning_metadata_status": r.get("status", "failed"),
            "learning_metadata_error": None if exito else r.get("error"),
            "document_description": r.get("document_description"),
        }

    return nodo_metadatos


# ----------------------------------------------------------------------
# 2. ADAPTADORES DE CONTRATO (DTO Mappers)
# ----------------------------------------------------------------------
class ContratoEvaluadorError(ValueError):
    """Bug de integración: la respuesta inyectada por Backend no cumple el Contrato V2."""

class RespuestaEvaluadorInvalida(ContratoEvaluadorError):
    pass

class EvaluacionSinVeredicto(Exception):
    """verdict=null: fallo de evaluación en Data/IA, no es un rechazo pedagógico."""


_ORDEN_SEVERIDAD = {"high": 0, "medium": 1, "low": 2}


def _resumir_errores(error: ValidationError, maximo: int = 3) -> str:
    errores = error.errors()
    partes = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in errores[:maximo]]
    resto = len(errores) - maximo
    return "; ".join(partes) + (f" (+{resto} más)" if resto > 0 else "")


def _donde(item_id: Optional[str]) -> str:
    return f" (elemento {item_id})" if item_id else ""


def traducir_respuesta_evaluador(
    data: Any, document_id: Optional[str] = None, formato: Optional[str] = None
) -> ReviewFeedback:
    """
    Traduce el payload EvaluationResponseV2 (inyectado por Backend) a ReviewFeedback.
    Redacta las observaciones y recomendaciones como texto para el prompt del Redactor.
    """
    try:
        resp = EvaluationResponseV2.model_validate(data)
    except ValidationError as e:
        raise RespuestaEvaluadorInvalida(f"Respuesta no cumple el contrato V2: {_resumir_errores(e)}") from e
    
    if document_id is not None and resp.document_id != document_id:
        raise RespuestaEvaluadorInvalida(f"Respuesta del doc '{resp.document_id}', esperado '{document_id}'")
    if formato is not None and resp.format != formato:
        raise RespuestaEvaluadorInvalida(f"Respuesta del formato '{resp.format}', esperado '{formato}'")

    semantica = resp.semantic_evaluation
    if resp.verdict is None:
        detalle = f"status={semantica.status}, error_code={semantica.error_code}"
        raise EvaluacionSinVeredicto(f"Evaluador no emitió veredicto ({detalle})")

    observaciones = sorted(semantica.observations, key=lambda o: _ORDEN_SEVERIDAD[o.severity])
    problemas = [f"[{o.dimension} · severidad {o.severity}] {o.message}{_donde(o.item_id)}" for o in observaciones]
    problemas += [
        f"Afirmación sin respaldo: «{u.claim}». Motivo: {u.reason}{_donde(u.item_id)}"
        for u in semantica.unsupported_information
    ]
    sugerencias = [f"[{r.dimension}] {r.message}{_donde(r.item_id)}" for r in semantica.recommendations]

    if semantica.scores is not None:
        puntajes = semantica.scores.model_dump()
    elif resp.heuristic_scores is not None:
        puntajes = resp.heuristic_scores.model_dump()
    else:
        puntajes = None

    aprobado = resp.verdict == "approved"
    if not aprobado and not problemas and not sugerencias:
        detalle = f" Puntajes: {', '.join(f'{k} {v}' for k, v in puntajes.items())}." if puntajes else ""
        problemas.append("El evaluador solicitó revisión sin detalle semántico." + detalle)

    return {
        "approved": aprobado,
        "verdict": resp.verdict,
        "score": round(sum(puntajes.values()) / len(puntajes), 2) if puntajes else None,
        "scores": puntajes,
        "issues": problemas,
        "suggestions": sugerencias,
        "reviewed": True,
        "evaluator_error": None,
        "evaluator_version": resp.evaluator_version,
        "rubric_version": resp.rubric_version,
    }


# ----------------------------------------------------------------------
# 3. NODO REVISOR Y FLUJO CONDICIONAL DE NUEVA EVIDENCIA (Sprint 4)
# ----------------------------------------------------------------------
def crear_nodo_revisor(agente: AgentV1) -> Callable[[FormatState], Dict[str, Any]]:
    """
    Nodo Revisor activo: analiza el feedback y determina si requiere nueva evidencia o ajuste directo.
    """
    def nodo_revisor(state: FormatState) -> Dict[str, Any]:
        feedback = state.get("feedback")
        if not feedback or feedback.get("approved"):
            return {"needs_new_evidence": False}

        # Analizar si las observaciones indican falta de contexto o afirmaciones sin respaldo
        issues = feedback.get("issues", [])
        requiere_busqueda = any("respaldo" in issue.lower() or "contexto" in issue.lower() for issue in issues)
        
        return {"needs_new_evidence": requiere_busqueda}
    return nodo_revisor


def crear_nodo_nueva_evidencia(agente: AgentV1, top_k: int = 5) -> Callable[[FormatState], Dict[str, Any]]:
    """
    Recupera nueva evidencia de ChromaDB si el revisor determinó que el feedback lo exige.
    """
    def nodo_nueva_evidencia(state: FormatState) -> Dict[str, Any]:
        document_id = state["document_id"]
        niche = state["niche"]
        query = f"Ampliación sobre {niche} para corregir observaciones del revisor."
        
        try:
            resultados = agente.retriever.retrieve(
                query=query, top_k=top_k, metadata_filters={"document_id": document_id}
            )
        except Exception as e:
            logger.exception("Nodo nueva evidencia: fallo en el retriever")
            return {"retrieval_error": classify_exception(e)}

        if not resultados:
            return {}

        nuevos_chunks = [
            {
                "rank": rank,
                "chunk_id": r.chunk_id,
                "document_id": (r.metadata or {}).get("document_id", document_id),
                "score": getattr(r, "score", 0.0),
                "text": r.text,
            }
            for rank, r in enumerate(resultados, start=1)
        ]
        
        contexto_actualizado = state.get("retrieved_context", "") + "\n\n" + "\n\n".join(r.text for r in resultados)
        
        return {
            "retrieved_context": contexto_actualizado,
            "sources_used": state.get("sources_used", []) + nuevos_chunks,
        }
    return nodo_nueva_evidencia


def decidir_ruta_revision(state: FormatState) -> str:
    """Enrutamiento condicional: si necesita nueva evidencia, va al buscador; si no, directo al redactor."""
    if state.get("needs_new_evidence", False):
        return "nueva_evidencia"
    return "redactor"


# ----------------------------------------------------------------------
# 4. SUBGRAFO ATÓMICO POR FORMATO (Con Revisor y Redactor)
# ----------------------------------------------------------------------
def compilar_subgrafo_formato(agente: AgentV1):
    """
    Subgrafo robusto: START -> Revisor -> (Condicional: nueva_evidencia o redactor) -> Redactor -> Finalizar -> END.
    """
    sub = StateGraph(FormatState)
    sub.add_node("revisor", crear_nodo_revisor(agente))
    sub.add_node("nueva_evidencia", crear_nodo_nueva_evidencia(agente))
    sub.add_node("redactor", crear_nodo_redactor(agente))
    sub.add_node("finalizar", nodo_finalizar)
    
    sub.add_edge(START, "revisor")
    sub.add_conditional_edges(
        "revisor",
        decidir_ruta_revision,
        {
            "nueva_evidencia": "nueva_evidencia",
            "redactor": "redactor"
        }
    )
    sub.add_edge("nueva_evidencia", "redactor")
    sub.add_edge("redactor", "finalizar")
    sub.add_edge("finalizar", END)
    
    return sub.compile()


def crear_nodo_formato(app_formato) -> Callable[[FormatState], Dict[str, Any]]:
    """Envoltura protectora para el subgrafo en la ejecución concurrente."""
    def procesar_formato(state: FormatState) -> Dict[str, Any]:
        formato = state["format"]
        try:
            if formato.lower() not in ESQUEMAS_POR_FORMATO:
                mensaje = f"El formato '{formato}' no está soportado."
                outcome = construir_outcome(state, status="failed", error=build_error("UNSUPPORTED_FORMAT", mensaje))
            elif state.get("retrieval_error"):
                error = state["retrieval_error"]
                outcome = construir_outcome(state, status=_estado_de_error(error), error=error)
            else:
                outcome = app_formato.invoke(state)["outcome"]
        except Exception as e:
            logger.exception("procesar_formato: excepción inesperada (formato=%s)", formato)
            outcome = construir_outcome(state, status="failed", error=classify_exception(e))
        return {"final_results": [outcome]}
    return procesar_formato


# ----------------------------------------------------------------------
# 5. COMPILACIÓN GLOBAL (ORQUESTADOR)
# ----------------------------------------------------------------------
def compilar_grafo_generacion(agente: AgentV1, *, top_k: int = 5):
    """
    Grafo principal: Extrae contexto (RAG) e invoca paralelamente el worker de formato
    para construir la primera versión.
    """
    app_formato = compilar_subgrafo_formato(agente)

    def despachar(state: AgentState) -> List[Send]:
        envios = [Send("metadatos", state)]
        envios += [Send("procesar_formato", new_format_state(state, f)) for f in state["formats_requested"]]
        return envios

    g = StateGraph(AgentState)
    g.add_node("investigador", crear_nodo_investigador(agente, top_k))
    g.add_node("metadatos", crear_nodo_metadatos(agente))
    g.add_node("procesar_formato", crear_nodo_formato(app_formato))
    
    g.add_edge(START, "investigador")
    g.add_conditional_edges("investigador", despachar, ["metadatos", "procesar_formato"])
    g.add_edge("metadatos", END)
    g.add_edge("procesar_formato", END)
    
    return g.compile()


def ejecutar_grafo(grafo, estado: AgentState, max_concurrency: Optional[int] = None) -> AgentState:
    limite = max_concurrency or max_concurrency_por_defecto()
    return grafo.invoke(estado, {"max_concurrency": limite})