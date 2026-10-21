"""
Nodos del grafo de LangGraph para el ciclo de un formato: Redactor -> (Revisor) -> cierre.

Reparto de responsabilidades (para que cada decisión viva en UN solo lugar):

* nodo_redactor        : escribe HECHOS en el estado (contenido nuevo o error). No decide el rumbo
                         y no construye el outcome.
* crear_nodo_revisor   : analiza el feedback del evaluador y determina si se requiere nueva evidencia.
* crear_nodo_nueva_evidencia: recupera nuevos fragmentos de ChromaDB si el revisor lo solicita.
* ruta_tras_redactor   : decide el rumbo (revisar / reescribir / cerrar) con las reglas de state.py.
* nodo_finalizar       : único lugar que construye el outcome del formato.
"""
import json
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List

from .errors import build_error, classify_exception
from .state import (
    DEFAULT_MAX_REVISIONS,
    FormatState,
    construir_outcome,
    error_permite_revision,
    puede_revisar,
)

if TYPE_CHECKING:
    from .agent_v1 import AgentV1

logger = logging.getLogger(__name__)

MAX_CHARS_CONTENIDO_PREVIO = 6000


def _sin_duplicados(items: Iterable[str]) -> List[str]:
    vistos, salida = set(), []
    for item in items:
        texto = " ".join(str(item).split())
        if texto and texto.lower() not in vistos:
            vistos.add(texto.lower())
            salida.append(texto)
    return salida


def construir_instrucciones_revision(state: FormatState) -> str:
    error_previo = state.get("current_error")
    feedback = state.get("feedback")
    if not error_previo and not feedback:
        return ""

    veredictos = list(state.get("feedback_history") or [])
    if feedback:
        veredictos.append(feedback)
    problemas = _sin_duplicados(i for v in veredictos for i in (v.get("issues") or []))
    sugerencias = _sin_duplicados(i for v in veredictos for i in (v.get("suggestions") or []))

    lineas = ["ESTA ES UNA REVISIÓN de tu intento anterior. Corrige lo siguiente y conserva lo que ya estaba bien:"]
    if error_previo:
        lineas.append(f"- Tu salida anterior no fue válida: {error_previo['message']}")
    if problemas:
        lineas.append("- Problemas señalados por el revisor:\n  * " + "\n  * ".join(problemas))
    if sugerencias:
        lineas.append("- Sugerencias de mejora:\n  * " + "\n  * ".join(sugerencias))

    previo = state.get("current_content")
    if previo:
        texto = json.dumps(previo, ensure_ascii=False)
        if len(texto) > MAX_CHARS_CONTENIDO_PREVIO:
            texto = texto[:MAX_CHARS_CONTENIDO_PREVIO] + "…"
        lineas.append("Tu versión anterior (JSON):\n" + texto)

    return "\n".join(lineas)


def crear_nodo_revisor(agente: "AgentV1") -> Callable[[FormatState], Dict[str, Any]]:
    def nodo_revisor(state: FormatState) -> Dict[str, Any]:
        feedback = state.get("feedback")
        
        if not feedback or feedback.get("approved"):
            return {"needs_new_evidence": False}

        issues = feedback.get("issues", [])
        requiere_busqueda = any("respaldo" in issue.lower() or "contexto" in issue.lower() for issue in issues)
                
        return {"needs_new_evidence": requiere_busqueda}
    return nodo_revisor


def crear_nodo_nueva_evidencia(agente: "AgentV1", top_k: int = 5) -> Callable[[FormatState], Dict[str, Any]]:
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
    if state.get("needs_new_evidence", False):
        return "nueva_evidencia"
    return "redactor"


def crear_nodo_redactor(agente: "AgentV1") -> Callable[[FormatState], Dict[str, Any]]:
    def nodo_redactor(state: FormatState) -> Dict[str, Any]:
        formato = state["format"]
        es_reescritura = bool(state.get("current_error") or state.get("feedback"))
        revision = state.get("revision_count", 0) + (1 if es_reescritura else 0)
        instrucciones = construir_instrucciones_revision(state) if es_reescritura else ""

        try:
            resultado = agente.generate_from_context(
                contexto=state.get("retrieved_context", ""),
                sources_used=state.get("sources_used", []),
                formato=formato,
                perfil=state["profile"],
                nicho=state["niche"],
                nivel=state["detail_level"],
                learning_objective=state.get("learning_objective"),
                extra_instructions=instrucciones,
            )
        except Exception as e:
            logger.exception("Redactor: excepción inesperada (formato=%s)", formato)
            return {"revision_count": revision, "current_error": classify_exception(e)}

        if resultado.get("status") == "success":
            return {
                "revision_count": revision,
                "current_content": resultado["content"],
                "current_error": None,
                "feedback": None,
            }

        error = resultado.get("error") or build_error(
            "INTERNAL_ERROR", resultado.get("error_message") or "Fallo sin detalle."
        )
        return {"revision_count": revision, "current_error": error}

    return nodo_redactor


def ruta_tras_redactor(state: FormatState) -> str:
    error = state.get("current_error")
    if error is None:
        return "revisor"
    if error_permite_revision(error) and puede_revisar(state):
        return "redactor"
    return "finalizar"


def nodo_finalizar(state: FormatState) -> Dict[str, Any]:
    error = state.get("current_error")
    if error is not None:
        estado = "no_results" if error.get("code") == "NO_CONTEXT" else "failed"
        return {"outcome": construir_outcome(state, status=estado, error=error)}
    return {"outcome": construir_outcome(state, status="success", content=state.get("current_content"))}