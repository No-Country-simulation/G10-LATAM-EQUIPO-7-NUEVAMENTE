"""
PROPUESTA de contratos Pydantic (Sprint 4) para Data/IA, agente evaluador y backend.

NO está conectada al código: es la propuesta para acordar. Está pensada como reemplazo
directo de generated_schemas.py (exporta los mismos 8 nombres que hoy importan api.py y
agent_v1.py) más los modelos nuevos de errores, evaluación y respuestas.

Principios:

1. Dos capas. Los modelos de CONTENIDO (parte 1) son los que se envían a Gemini como
   response_schema. Por eso NO usan min_length/max_length/pattern ni extra="forbid":
   eso genera minItems/maxItems/additionalProperties en el JSON schema y algunas
   versiones de Gemini lo rechazan con 400. Las reglas semánticas van en validadores
   que corren DESPUÉS de que Gemini responde y no cambian el schema que Gemini ve.

2. Reparar lo determinista, rechazar solo lo irreparable. Duplicados, espacios, ids
   repetidos y la aritmética de duraciones se corrigen en código (no se le confía al LLM).
   Solo se rechaza lo que no se puede arreglar sin inventar contenido (por ejemplo, que
   correct_answer no coincida con ninguna opción). Un rechazo se reporta como
   INVALID_MODEL_OUTPUT (reintentable), no como un fallo genérico.

3. Los modelos de ENTRADA y de RESPUESTA (partes 2 a 4) nunca viajan a Gemini, así que
   pueden ser estrictos.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_KEY_CONCEPTS = 5
MAX_PREREQUISITES = 3


# ----------------------------------------------------------------------
# Helpers de normalización (deterministas)
# ----------------------------------------------------------------------
def _limpiar_lista(items: List[str]) -> List[str]:
    """Quita espacios sobrantes, vacíos y duplicados (sin distinguir mayúsculas), conservando el orden."""
    vistos, salida = set(), []
    for item in items:
        texto = " ".join(str(item).split())
        if texto and texto.lower() not in vistos:
            vistos.add(texto.lower())
            salida.append(texto)
    return salida


def _texto_no_vacio(valor: str, campo: str) -> str:
    limpio = " ".join(str(valor).split())
    if not limpio:
        raise ValueError(f"{campo} no puede estar vacío")
    return limpio


def _asegurar_ids_unicos(items: list, atributo: str, prefijo: str) -> None:
    """Si el LLM repitió o dejó vacíos los ids, se reasignan todos: prefijo1, prefijo2..."""
    ids = [getattr(i, atributo) for i in items]
    if len(set(ids)) != len(ids) or any(not str(x).strip() for x in ids):
        for n, item in enumerate(items, start=1):
            setattr(item, atributo, f"{prefijo}{n}")


# ======================================================================
# PARTE 1. CONTENIDO PEDAGÓGICO (Data/IA). Estos modelos SÍ viajan a Gemini.
# ======================================================================
class LearningMetadata(BaseModel):
    key_concepts: List[str] = Field(..., description="Lista de 3 a 5 conceptos clave abordados en el contenido.")
    prerequisites: List[str] = Field(..., description="Lista de 1 a 3 conocimientos previos recomendados.")
    estimated_time_minutes: int = Field(..., description="Tiempo estimado de estudio o lectura, en minutos enteros (mínimo 1).")

    @field_validator("key_concepts")
    @classmethod
    def _conceptos(cls, v: List[str]) -> List[str]:
        v = _limpiar_lista(v)[:MAX_KEY_CONCEPTS]  # más de 5 se recorta; menos de 3 se acepta
        if not v:
            raise ValueError("key_concepts no puede estar vacío")
        return v

    @field_validator("prerequisites")
    @classmethod
    def _prerrequisitos(cls, v: List[str]) -> List[str]:
        return _limpiar_lista(v)[:MAX_PREREQUISITES]

    @field_validator("estimated_time_minutes")
    @classmethod
    def _tiempo(cls, v: int) -> int:
        return max(1, int(v))


class CardItem(BaseModel):
    card_id: str = Field(..., description="Identificador único de la tarjeta.")
    front: str = Field(..., description="Concepto o pregunta (anverso de la tarjeta).")
    back: str = Field(..., description="Definición o respuesta (reverso de la tarjeta).")

    @field_validator("front")
    @classmethod
    def _front(cls, v: str) -> str:
        return _texto_no_vacio(v, "front")

    @field_validator("back")
    @classmethod
    def _back(cls, v: str) -> str:
        return _texto_no_vacio(v, "back")


class FlashcardsContent(BaseModel):
    title: str = Field(..., description="Título del conjunto de flashcards.")
    instructions: str = Field(..., description="Instrucciones de uso pedagógico.")
    cards: List[CardItem] = Field(..., description="Lista de flashcards generadas.")

    @model_validator(mode="after")
    def _coherente(self):
        if not self.cards:
            raise ValueError("Debe haber al menos una flashcard.")
        _asegurar_ids_unicos(self.cards, "card_id", "c")
        return self


class QuizItem(BaseModel):
    question_id: str = Field(..., description="Identificador único de la pregunta.")
    question: str = Field(..., description="La pregunta de opción múltiple.")
    options: List[str] = Field(..., description="Lista de opciones posibles (mínimo 2, sin repetidas).")
    correct_answer: str = Field(..., description="El texto exacto de la respuesta correcta; debe ser una de las options.")
    explanation: str = Field(..., description="Explicación pedagógica de por qué es correcta.")

    @model_validator(mode="after")
    def _coherente(self):
        self.question = _texto_no_vacio(self.question, "question")
        self.options = _limpiar_lista(self.options)
        if len(self.options) < 2:
            raise ValueError("Cada pregunta necesita al menos 2 opciones distintas.")
        buscada = " ".join(self.correct_answer.split()).lower()
        coincidencia = next((o for o in self.options if o.lower() == buscada), None)
        if coincidencia is None:
            raise ValueError("correct_answer debe coincidir exactamente con una de las options.")
        self.correct_answer = coincidencia
        return self


class QuizContent(BaseModel):
    title: str = Field(..., description="Título del cuestionario.")
    instructions: str = Field(..., description="Instrucciones para resolver el cuestionario.")
    questions: List[QuizItem] = Field(..., description="Lista de preguntas del quiz.")

    @model_validator(mode="after")
    def _coherente(self):
        if not self.questions:
            raise ValueError("Debe haber al menos una pregunta.")
        _asegurar_ids_unicos(self.questions, "question_id", "q")
        return self


class TLDRContent(BaseModel):
    title: str = Field(..., description="Título breve del contenido.")
    summary: str = Field(..., description="Resumen ejecutivo conciso del contexto recuperado.")
    key_points: List[str] = Field(..., description="Lista de los puntos esenciales (3 a 7 cuando el contexto lo permita).")
    conclusion: str = Field(..., description="Idea final o takeaway principal.")

    @model_validator(mode="after")
    def _coherente(self):
        self.summary = _texto_no_vacio(self.summary, "summary")
        self.key_points = _limpiar_lista(self.key_points)
        if not self.key_points:
            raise ValueError("key_points no puede estar vacío")
        return self


class VideoScene(BaseModel):
    scene_id: str = Field(..., description="Identificador corto de la escena.")
    title: str = Field(..., description="Título de la escena.")
    narration: str = Field(..., description="Texto que pronunciaría el docente o narrador.")
    visual_description: str = Field(..., description="Qué debería verse en pantalla.")
    duration_seconds: int = Field(..., description="Duración estimada de la escena en segundos (mínimo 1).")

    @field_validator("narration")
    @classmethod
    def _narracion(cls, v: str) -> str:
        return _texto_no_vacio(v, "narration")

    @field_validator("duration_seconds")
    @classmethod
    def _duracion(cls, v: int) -> int:
        return max(1, int(v))


class VideoScriptContent(BaseModel):
    title: str = Field(..., description="Título general.")
    estimated_duration_minutes: int = Field(..., description="Duración total estimada en minutos (se recalcula a partir de las escenas).")
    scenes: List[VideoScene] = Field(..., description="Secuencia ordenada del guion.")

    @model_validator(mode="after")
    def _coherente(self):
        if not self.scenes:
            raise ValueError("Debe haber al menos una escena.")
        _asegurar_ids_unicos(self.scenes, "scene_id", "s")
        # La aritmética no se le confía al LLM: la duración total se deriva de las escenas.
        total = sum(s.duration_seconds for s in self.scenes)
        self.estimated_duration_minutes = max(1, round(total / 60))
        return self


# ======================================================================
# PARTE 2. ERRORES Y FUENTES (compartidos por todos los endpoints)
# ======================================================================
# Debe coincidir con las claves de CATALOGO en agentes/errors.py
ErrorCode = Literal[
    "RESOURCE_EXHAUSTED",
    "PROVIDER_UNAVAILABLE",
    "PROVIDER_TIMEOUT",
    "PROVIDER_ERROR",
    "INVALID_MODEL_OUTPUT",
    "PROVIDER_REJECTED_REQUEST",
    "PROVIDER_AUTH_ERROR",
    "MODEL_NOT_FOUND",
    "NO_CONTEXT",
    "UNSUPPORTED_FORMAT",
    "INTERNAL_ERROR",
]


class ErrorDetail(BaseModel):
    code: ErrorCode = Field(..., description="Causa normalizada del fallo.")
    message: str = Field(..., description="Detalle corto y legible.")
    retryable: bool = Field(..., description="True si tiene sentido reintentar más tarde.")
    http_status: int = Field(..., description="HTTP que la API emite si TODO falla por esta causa.")
    upstream_status: Optional[int] = Field(None, description="HTTP devuelto por Gemini (None si no aplica).")
    provider: Literal["gemini", "internal"]


class SourceChunk(BaseModel):
    """Fragmento usado como evidencia. Es la entrada del agente evaluador para medir fidelidad a la fuente."""
    rank: int = Field(..., ge=1)
    chunk_id: str
    document_id: str
    score: float = Field(..., description="Logit del Cross-Encoder (ms-marco-MiniLM-L-6-v2): mayor = más relevante, sin cota (puede ser negativo) y no comparable entre queries distintas.")
    text: str


# ======================================================================
# PARTE 3. ENDPOINTS PARA BACKEND
# ======================================================================
DOCUMENT_ID_PATTERN = r"^[A-Za-z0-9._\-]{1,128}$"


class IndexResponse(BaseModel):
    document_id: str
    status: Literal["indexed"]
    document_title: str = Field(..., description="Nombre del archivo recibido.")
    chunks_indexed: int = Field(..., ge=0, description="Cantidad de fragmentos guardados.")


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # un typo ("format" en vez de "formats") falla con 422 en vez de ignorarse

    document_id: str = Field(..., pattern=DOCUMENT_ID_PATTERN)
    formats: List[str] = Field(..., description="quiz | flashcards | tldr | video_script. Un formato desconocido NO falla el request: se reporta como fallo controlado de ese formato.")
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str] = None
    query: Optional[str] = Field(None, description="Consulta directa (benchmarks y búsquedas exactas).")


class FormatResult(BaseModel):
    format: str
    status: Literal["success", "failed", "no_results"]
    content: Optional[Dict[str, Any]] = Field(None, description="QuizContent | FlashcardsContent | TLDRContent | VideoScriptContent según format.")
    sources_used: List[SourceChunk] = Field(default_factory=list)
    error_message: Optional[str] = Field(None, description="Compatibilidad con el contrato del Sprint 3.")
    error: Optional[ErrorDetail] = Field(None, description="null si status=success.")
    execution_time_seconds: float


class GenerateResponse(BaseModel):
    document_id: str
    overall_status: Literal["success", "partial", "failed"]
    document_title: Optional[str] = None
    document_description: Optional[str] = Field(None, description="Una sola oración, máximo 30 palabras. null si Gemini falló.")
    execution_time_seconds: float
    # PROPUESTA v1.1: null cuando falla, en lugar del centinela "Error al extraer conceptos",
    # ahora que learning_metadata_error ya explica el fallo. Requiere acuerdo con backend.
    learning_metadata: Optional[LearningMetadata] = None
    learning_metadata_status: Literal["success", "failed", "no_results"]
    learning_metadata_error: Optional[ErrorDetail] = None
    results: List[FormatResult]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model: str = Field(..., description="Valor de GEMINI_MODEL (no la key).")
    gemini_key_configured: bool
    vector_store_ok: bool


# ======================================================================
# PARTE 4. AGENTE EVALUADOR (Data): evaluación de retrieval, contrato v2.0
# ======================================================================
# Refleja EXACTAMENTE lo que arman build_success_response / build_no_results_response /
# build_error_response en rag/contract.py (CONTRACT_VERSION = "2.0"). No se renombra nada:
#
#     retrieval v2.0:  status = success | no_results | error
#                      error  = {code: INVALID_INPUT | RETRIEVAL_FAILED, message}   (null si no aplica)
#     /generate:       status = success | failed | no_results
#                      error  = ErrorDetail (catálogo de la parte 2)
#
# Las respuestas usan extra="allow" para tolerar campos que Data agregue en el futuro.
class RetrievalEvalCase(BaseModel):
    """Refleja los argumentos de retrieve_for_evaluation(case_id, query, top_k, metadata_filters)."""
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=128, description="Id del caso del Ground Truth; se devuelve igual.")
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description='Ej.: {"document_id": "doc_1"} o {"categoria": "..."}')


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(extra="allow")

    rank: int = Field(..., ge=1, description="1 = el más relevante.")
    chunk_id: str
    document_id: str
    score: float = Field(..., description="Logit del Cross-Encoder (score_type='cross_encoder'): mayor = más relevante, sin cota (puede ser negativo) y no comparable entre queries distintas.")
    text: str
    metadata: Dict[str, Any]


class RetrievalError(BaseModel):
    code: str = Field(..., description="INVALID_INPUT | RETRIEVAL_FAILED.")
    message: str


class RetrievalEvalResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    contract_version: str
    case_id: str
    query: str
    top_k: int
    score_type: str
    status: Literal["success", "no_results", "error"]
    results: List[RetrievedChunk]
    error: Optional[RetrievalError] = Field(None, description="Siempre presente como clave; null salvo status=error.")


class RetrievalEvalBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: List[RetrievalEvalCase] = Field(..., min_length=1, max_length=100)


class RetrievalEvalBatchResponse(BaseModel):
    overall_status: Literal["success", "partial", "failed"]
    total: int
    succeeded: int = Field(..., description="Casos con status success o no_results.")
    failed: int = Field(..., description="Casos con status error.")
    execution_time_seconds: float
    results: List[RetrievalEvalResult] = Field(..., description="Payloads v2.0 en el orden de cases, listos para evaluate_retrieval_batch.")
