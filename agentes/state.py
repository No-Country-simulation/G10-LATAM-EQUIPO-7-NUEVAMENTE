"""
Memoria compartida del grafo de LangGraph (Investigador, Redactor y Revisor).

Hay DOS estados porque hay dos tiempos de vida:

* AgentState: uno por solicitud. El Investigador (RAG + metadatos) lo llena UNA vez y todos
  los formatos lo comparten. Aquí se acumulan los resultados finales.
* FormatState: uno por formato, con su propio lazo Redactor <-> Revisor. Cada formato arranca
  limpio (revision_count en 0, sin feedback de otro formato) y puede fallar sin afectar a los
  demás: es la atomicidad por formato del contrato de /api/v1/generate.

Patrón de uso:

    START -> investigador -> fan_out: [Send("formato", new_format_state(state, f)) para cada f]
          -> (cada "formato" corre su lazo y devuelve {"final_results": [outcome]}) -> END

    # al leer el resultado (en la API, no dentro del grafo):
    resultados = ordenar_resultados(out["final_results"], out["formats_requested"])

Reglas que este estado asume (ver los helpers al final):

* Un fallo del PROVEEDOR (cuota, saturación, config) no entra al lazo de revisión: se reporta
  tal cual como error estructurado de ese formato. Gastar revisiones ahí solo consume más cuota.
* Una salida inválida del modelo (INVALID_MODEL_OUTPUT) SÍ es revisable: el mensaje del
  validador sirve como feedback para que el Redactor reescriba.
* final_results solo se alimenta al terminar cada formato, nunca en cada revisión.
"""
import operator
import time
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

# Cada revisión cuesta una llamada a Gemini (y una al evaluador). Con las cuotas del plan
# gratuito conviene un presupuesto bajo; es configurable por solicitud.
DEFAULT_MAX_REVISIONS = 2

# Códigos de agentes/errors.py cuya causa es la calidad de la salida, no el proveedor.
CODIGOS_REVISABLES = frozenset({"INVALID_MODEL_OUTPUT"})

EstadoUnidad = Literal["success", "failed", "no_results"]


# ----------------------------------------------------------------------
# Tipos auxiliares (reflejan el contrato de /api/v1/generate)
# ----------------------------------------------------------------------
class ErrorInfo(TypedDict):
    """Mismo objeto `error` que construye agentes/errors.py::build_error."""
    code: str
    message: str
    retryable: bool
    http_status: int
    upstream_status: Optional[int]
    provider: str


class ReviewFeedback(TypedDict, total=False):
    """
    Veredicto del Revisor, derivado de la respuesta V2 del Evaluador Semántico de Data/IA.
    El router del lazo solo necesita `approved`; el resto le sirve al Redactor para corregir
    y a Backend para auditar.
    """
    approved: bool
    verdict: Optional[str]                 # approved | requires_revision | rejected (None si no hubo evaluación)
    score: Optional[float]                 # promedio 1-5 de las cuatro dimensiones
    scores: Optional[Dict[str, float]]     # relevance, coherence, didactic_adaptation, content_support
    issues: List[str]                      # observaciones + información sin respaldo, ya redactadas en español
    suggestions: List[str]                 # recomendaciones, ya redactadas
    # False cuando la aprobación NO vino del evaluador (servicio caído, timeout, respuesta o petición
    # inválida, verdict null o sin URL configurada): se aprobó "por defecto". Permite auditar esos casos.
    reviewed: bool
    evaluator_error: Optional[str]
    evaluator_version: Optional[str]
    rubric_version: Optional[str]


class FormatOutcome(TypedDict):
    """Resultado final de UN formato. Idéntico a results[] de /api/v1/generate."""
    format: str
    status: EstadoUnidad
    content: Optional[Dict[str, Any]]
    sources_used: List[Dict[str, Any]]
    error_message: Optional[str]
    error: Optional[ErrorInfo]
    execution_time_seconds: float


# ----------------------------------------------------------------------
# Estado global: una vez por solicitud
# ----------------------------------------------------------------------
class AgentState(TypedDict, total=False):
    # 1. Entrada de la solicitud (la fija la API con new_agent_state)
    document_id: str
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str]
    query_rag: str
    formats_requested: List[str]  # orden original: sirve para ordenar final_results al final
    max_revisions: int

    # 2. Investigador: se ejecuta una sola vez y lo comparten todos los formatos
    retrieved_context: str
    sources_used: List[Dict[str, Any]]
    retrieval_error: Optional[ErrorInfo]  # si el Investigador falló o no halló contenido: los formatos cierran con este error
    document_title: Optional[str]
    document_description: Optional[str]
    learning_metadata: Optional[Dict[str, Any]]
    learning_metadata_status: Optional[EstadoUnidad]
    learning_metadata_error: Optional[ErrorInfo]

    # 3. Acumulador de resultados. Annotated + operator.add suma (append) lo que devuelve
    #    cada formato en vez de sobrescribirlo. Cada nodo debe devolver una LISTA:
    #        return {"final_results": [outcome]}      # correcto
    #        return {"final_results": outcome}        # incorrecto: list + dict falla
    #    Con formatos en paralelo el orden de llegada no está garantizado: usar
    #    ordenar_resultados() al leer.
    final_results: Annotated[List[FormatOutcome], operator.add]

    # 4. Medición (time.time(): sobrevive a un checkpoint reanudado en otro proceso)
    started_at: float


# ----------------------------------------------------------------------
# Estado por formato: una vez por formato (entrada del Send)
# ----------------------------------------------------------------------
class FormatState(TypedDict, total=False):
    # Copia de lo que necesita del estado global
    format: str
    document_id: str
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str]
    retrieved_context: str
    sources_used: List[Dict[str, Any]]
    retrieval_error: Optional[ErrorInfo]
    max_revisions: int
    started_at: float

    # Lazo Redactor <-> Revisor
    current_content: Optional[Dict[str, Any]]   # JSON del Redactor
    current_error: Optional[ErrorInfo]          # fallo del último intento (None si salió bien)
    feedback: Optional[ReviewFeedback]          # último veredicto del Revisor
    feedback_history: Annotated[List[ReviewFeedback], operator.add]  # para que el Redactor no repita errores
    revision_count: int                         # reescrituras ya hechas; lo incrementa SOLO el Redactor

    # Salida del subgrafo
    outcome: Optional[FormatOutcome]


# ----------------------------------------------------------------------
# Constructores: evitan KeyError por claves sin inicializar
# ----------------------------------------------------------------------
def construir_query_rag(
    niche: str,
    profile: str,
    detail_level: str,
    learning_objective: Optional[str] = None,
    query: Optional[str] = None,
) -> str:
    """Misma lógica que /api/v1/generate: `query` directa tiene prioridad."""
    if query:
        return query
    texto = f"Conceptos principales sobre {niche} para un perfil {profile} con nivel {detail_level}."
    if learning_objective:
        texto += f" Objetivo: {learning_objective}"
    return texto


def new_agent_state(
    *,
    document_id: str,
    profile: str,
    niche: str,
    detail_level: str,
    formats: List[str],
    learning_objective: Optional[str] = None,
    query: Optional[str] = None,
    max_revisions: int = DEFAULT_MAX_REVISIONS,
) -> AgentState:
    """Estado inicial COMPLETO: ningún nodo debería leer una clave que no exista."""
    return {
        "document_id": document_id,
        "profile": profile,
        "niche": niche,
        "detail_level": detail_level,
        "learning_objective": learning_objective,
        "query_rag": construir_query_rag(niche, profile, detail_level, learning_objective, query),
        "formats_requested": list(formats),
        "max_revisions": max_revisions,
        "retrieved_context": "",
        "sources_used": [],
        "retrieval_error": None,
        "document_title": None,
        "document_description": None,
        "learning_metadata": None,
        "learning_metadata_status": None,
        "learning_metadata_error": None,
        "final_results": [],
        "started_at": time.time(),
    }


def new_format_state(state: AgentState, formato: str) -> FormatState:
    """Payload del Send: cada formato arranca con contadores y feedback en limpio."""
    return {
        "format": formato,
        "document_id": state["document_id"],
        "profile": state["profile"],
        "niche": state["niche"],
        "detail_level": state["detail_level"],
        "learning_objective": state.get("learning_objective"),
        "retrieved_context": state.get("retrieved_context", ""),
        "sources_used": list(state.get("sources_used", [])),
        "retrieval_error": state.get("retrieval_error"),
        "max_revisions": state.get("max_revisions", DEFAULT_MAX_REVISIONS),
        "started_at": time.time(),
        "current_content": None,
        "current_error": None,
        "feedback": None,
        "feedback_history": [],
        "revision_count": 0,
        "outcome": None,
    }


# ----------------------------------------------------------------------
# Helpers para los routers y para cerrar cada formato
# ----------------------------------------------------------------------
def puede_revisar(state: FormatState) -> bool:
    """¿Queda presupuesto para una reescritura más?"""
    return state.get("revision_count", 0) < state.get("max_revisions", DEFAULT_MAX_REVISIONS)


def error_permite_revision(error: Optional[ErrorInfo]) -> bool:
    """Solo la salida inválida del modelo entra al lazo; cuota, saturación o config no."""
    return error is not None and error.get("code") in CODIGOS_REVISABLES


def construir_outcome(
    state: FormatState,
    *,
    status: EstadoUnidad,
    content: Optional[Dict[str, Any]] = None,
    error: Optional[ErrorInfo] = None,
) -> FormatOutcome:
    """Cierra un formato con la forma exacta de results[] del contrato /generate."""
    inicio = state.get("started_at") or time.time()
    return {
        "format": state["format"],
        "status": status,
        "content": content if status == "success" else None,
        "sources_used": list(state.get("sources_used", [])) if status == "success" else [],
        "error_message": error["message"] if error else None,
        "error": None if status == "success" else error,
        "execution_time_seconds": round(max(0.0, time.time() - inicio), 3),
    }


def ordenar_resultados(resultados: List[FormatOutcome], formats_requested: List[str]) -> List[FormatOutcome]:
    """Devuelve los resultados en el orden en que se pidieron los formatos (orden estable)."""
    posicion: Dict[str, int] = {}
    for i, nombre in enumerate(formats_requested):
        posicion.setdefault(nombre, i)
    return sorted(resultados, key=lambda r: posicion.get(r["format"], len(posicion)))
