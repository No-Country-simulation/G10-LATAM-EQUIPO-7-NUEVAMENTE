"""
Nodos del grafo de LangGraph para el ciclo de un formato: Redactor -> (Revisor) -> cierre.

Reparto de responsabilidades (para que cada decisión viva en UN solo lugar):

* nodo_redactor   : escribe HECHOS en el estado (contenido nuevo o error). No decide el rumbo
                    y no construye el outcome.
* ruta_tras_redactor: decide el rumbo (revisar / reescribir / cerrar) con las reglas de state.py.
* nodo_finalizar  : único lugar que construye el outcome del formato.

El Redactor tiene dos modos, que se distinguen por lo que haya en el estado, no por un contador:

    creación     : no hay current_error ni feedback  -> revision_count no cambia
    reescritura  : hay current_error o feedback      -> revision_count += 1

revision_count cuenta reescrituras (la primera generación NO cuenta), así que con
max_revisions=2 el formato puede generarse hasta 3 veces: 1 creación + 2 reescrituras.
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

if TYPE_CHECKING:  # solo para tipado: no importa chromadb ni el reranker al cargar este módulo
    from .agent_v1 import AgentV1

logger = logging.getLogger(__name__)

# Tope del JSON anterior que se le muestra al modelo al reescribir (evita prompts enormes).
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
    """
    Texto del modo reescritura. Devuelve "" si no hay nada que corregir (modo creación).
    Reúne el error estructural previo, los problemas y sugerencias del Revisor (último
    veredicto más el historial, sin repetir) y la versión anterior del contenido.
    """
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


def crear_nodo_redactor(agente: "AgentV1") -> Callable[[FormatState], Dict[str, Any]]:
    """
    Fábrica del nodo: LangGraph llama a los nodos con un solo argumento (el estado), así que el
    agente se inyecta por cierre en vez de como segundo parámetro.

        graph.add_node("redactor", crear_nodo_redactor(agente))
    """

    def nodo_redactor(state: FormatState) -> Dict[str, Any]:
        formato = state["format"]
        es_reescritura = bool(state.get("current_error") or state.get("feedback"))
        revision = state.get("revision_count", 0) + (1 if es_reescritura else 0)
        instrucciones = construir_instrucciones_revision(state) if es_reescritura else ""

        logger.info(
            "Redactor: formato=%s modo=%s reescrituras=%d/%d",
            formato, "reescritura" if es_reescritura else "creación",
            revision, state.get("max_revisions", DEFAULT_MAX_REVISIONS),
        )

        try:
            # Reutiliza el contexto que ya recuperó el Investigador: no vuelve a buscar en el RAG.
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
        except Exception as e:  # defensa: generate_from_context no lanza, pero nada debe abortar el grafo
            logger.exception("Redactor: excepción inesperada (formato=%s)", formato)
            return {"revision_count": revision, "current_error": classify_exception(e)}

        if resultado.get("status") == "success":
            # El feedback ya se consumió; el historial se conserva en feedback_history.
            return {
                "revision_count": revision,
                "current_content": resultado["content"],
                "current_error": None,
                "feedback": None,
            }

        error = resultado.get("error") or build_error(
            "INTERNAL_ERROR", resultado.get("error_message") or "Fallo sin detalle."
        )
        logger.warning("Redactor: fallo en %s: %s", formato, error["code"])
        # current_content y feedback se conservan: el siguiente intento los necesita como contexto.
        return {"revision_count": revision, "current_error": error}

    return nodo_redactor


def ruta_tras_redactor(state: FormatState) -> str:
    """
    Router posterior al Redactor:

        sin error                                  -> "revisor"
        INVALID_MODEL_OUTPUT y quedan revisiones   -> "redactor"  (reescribir)
        cualquier otro error, o sin presupuesto    -> "finalizar" (cuota, saturación, config...)
    """
    error = state.get("current_error")
    if error is None:
        return "revisor"
    if error_permite_revision(error) and puede_revisar(state):
        return "redactor"
    return "finalizar"


def nodo_finalizar(state: FormatState) -> Dict[str, Any]:
    """Único lugar donde se construye el outcome del formato (forma de results[] de /generate)."""
    error = state.get("current_error")
    if error is not None:
        estado = "no_results" if error.get("code") == "NO_CONTEXT" else "failed"
        return {"outcome": construir_outcome(state, status=estado, error=error)}
    return {"outcome": construir_outcome(state, status="success", content=state.get("current_content"))}
