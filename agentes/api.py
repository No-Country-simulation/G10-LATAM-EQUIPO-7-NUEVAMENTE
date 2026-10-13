import os
import time
import logging
import tempfile
from typing import Any, Dict, List, Literal, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .rag.models import Document
from .rag.cleaner import clean_text
from .rag.chunker import create_chunks
from .rag.embeddings import MultilingualEmbedding
from .rag.vector_store import VectorStore
from .agent_v1 import AgentV1, MODEL_NAME, API_KEY
from .rag.extractor import extract_document
from .rag.contract import build_error_response
from .errors import (
    build_error,
    classify_exception,
    evaluar_resultado_global,
    http_evaluacion_caso,
    evaluar_lote_evaluacion,
)

# ==========================================
# ÚNICA FUENTE DE VERDAD (Sprint 3)
# ==========================================
from .generated_schemas import (
    LearningMetadata,
    CardItem,
    FlashcardsContent,
    QuizItem,
    QuizContent,
    TLDRContent,
    VideoScene,
    VideoScriptContent
)

logger = logging.getLogger(__name__)

embedding_service = MultilingualEmbedding()
vector_store = VectorStore(embedding_service=embedding_service)
agent = AgentV1(vector_store=vector_store)

app = FastAPI(title="NuevaMente - API de Agentes")

FORMATOS_SOPORTADOS = ["quiz", "flashcards", "tldr", "video_script"]


def _metadata_fallback() -> Dict[str, Any]:
    return {
        "key_concepts": ["Error al extraer conceptos"],
        "prerequisites": ["No se pudieron determinar"],
        "estimated_time_minutes": 0
    }


# ==========================================
# CONTRATOS (entrada y salida documentados en Swagger)
# ==========================================
class GenerateRequest(BaseModel):
    document_id: str
    formats: List[str]
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str] = None
    query: Optional[str] = Field(None)


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Causa normalizada: RESOURCE_EXHAUSTED, PROVIDER_UNAVAILABLE, PROVIDER_TIMEOUT, PROVIDER_ERROR, INVALID_MODEL_OUTPUT, PROVIDER_REJECTED_REQUEST, PROVIDER_AUTH_ERROR, MODEL_NOT_FOUND, NO_CONTEXT, UNSUPPORTED_FORMAT, INTERNAL_ERROR.")
    message: str = Field(..., description="Detalle corto del fallo.")
    retryable: bool = Field(..., description="True si tiene sentido reintentar más tarde.")
    http_status: int = Field(..., description="HTTP que la API emite si todo falla por esta causa.")
    upstream_status: Optional[int] = Field(None, description="HTTP devuelto por Gemini (si aplica).")
    provider: str = Field(..., description="'gemini' o 'internal'.")


class FormatResult(BaseModel):
    format: str
    status: str = Field(..., description="success | failed | no_results")
    content: Optional[Dict[str, Any]] = None
    sources_used: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = Field(None, description="Compatibilidad con el contrato previo.")
    error: Optional[ErrorDetail] = Field(None, description="Error estructurado; null si status=success.")
    execution_time_seconds: float


class GenerateResponse(BaseModel):
    document_id: str
    overall_status: str = Field(..., description="success | partial | failed")
    document_title: Optional[str] = Field(None, description="Nombre del archivo indexado.")
    document_description: Optional[str] = Field(None, description="Descripción del documento en una oración; null si Gemini falló.")
    execution_time_seconds: float = Field(..., description="Tiempo total de ejecución del request.")
    learning_metadata: Dict[str, Any]
    learning_metadata_status: str = Field(..., description="success | failed | no_results")
    learning_metadata_error: Optional[ErrorDetail] = None
    results: List[FormatResult]


class IndexResponse(BaseModel):
    document_id: str
    status: Literal["indexed"]
    document_title: str = Field(..., description="Nombre del archivo recibido.")
    chunks_indexed: int = Field(..., description="Cantidad de fragmentos guardados.")


class DeleteResponse(BaseModel):
    document_id: str
    status: Literal["deleted", "not_found"]
    chunks_deleted: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model: str = Field(..., description="Valor de GEMINI_MODEL (nunca la key).")
    gemini_key_configured: bool
    vector_store_ok: bool


# ---- Evaluación de retrieval: refleja el contrato v2.0 de rag/contract.py ----
class RetrievalEvalCase(BaseModel):
    """Mismos argumentos que RetrieverService.retrieve_for_evaluation."""
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=128, description="Id del caso del Ground Truth; se devuelve igual.")
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description='Ej.: {"document_id": "doc_1"} o {"categoria": "..."}')


class RetrievedChunk(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    score: float = Field(..., description="Logit del Cross-Encoder: mayor = más relevante, sin cota, no comparable entre queries.")
    text: str
    metadata: Dict[str, Any]


class RetrievalError(BaseModel):
    code: str = Field(..., description="INVALID_INPUT | RETRIEVAL_FAILED")
    message: str


class RetrievalEvalResult(BaseModel):
    contract_version: str
    case_id: str
    query: str
    top_k: int
    score_type: str
    status: Literal["success", "no_results", "error"]
    results: List[RetrievedChunk]
    error: Optional[RetrievalError] = None


class RetrievalEvalBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: List[RetrievalEvalCase] = Field(..., min_length=1, max_length=100)


class RetrievalEvalBatchResponse(BaseModel):
    overall_status: Literal["success", "partial", "failed"]
    total: int
    succeeded: int = Field(..., description="Casos con status success o no_results.")
    failed: int = Field(..., description="Casos con status error.")
    execution_time_seconds: float
    results: List[RetrievalEvalResult] = Field(..., description="Payloads del contrato v2.0, listos para evaluate_retrieval_batch.")


_DESCRIPCION_EVAL = {
    207: "Lote con casos exitosos y casos con status=error.",
    422: "INVALID_INPUT en el caso (o todos los casos del lote).",
    500: "RETRIEVAL_FAILED en el caso (o en algún caso del lote cuando todos fallaron).",
}
RESPUESTAS_EVAL_CASO = {c: {"model": RetrievalEvalResult, "description": d} for c, d in _DESCRIPCION_EVAL.items() if c != 207}
RESPUESTAS_EVAL_LOTE = {c: {"model": RetrievalEvalBatchResponse, "description": d} for c, d in _DESCRIPCION_EVAL.items()}


_DESCRIPCION_HTTP = {
    207: "Fallo parcial controlado: al menos una unidad (metadatos o formato) salió bien y otra falló. Revisar results[].error.",
    404: "Todo falló: el document_id no tiene contenido indexado (NO_CONTEXT).",
    422: "Todo falló: ningún formato solicitado está soportado (UNSUPPORTED_FORMAT).",
    429: "Todo falló: cuota o rate limit de Gemini agotado (RESOURCE_EXHAUSTED).",
    500: "Todo falló por configuración del servidor (key/modelo de Gemini) o error interno.",
    502: "Todo falló: Gemini respondió con error o con una salida inválida.",
    503: "Todo falló: Gemini no disponible o saturado.",
    504: "Todo falló: timeout de Gemini.",
}
RESPUESTAS_DOC = {
    codigo: {"model": GenerateResponse, "description": texto}
    for codigo, texto in _DESCRIPCION_HTTP.items()
}


# ==========================================
# ENDPOINTS
# ==========================================
@app.post("/api/v1/index", response_model=IndexResponse)
async def index_document(document_id: str = Form(...), file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contenido = await file.read()
            tmp.write(contenido)
            tmp_path = tmp.name

        try:
            documents = extract_document(tmp_path)
            for doc in documents:
                doc.metadata["document_id"] = document_id
                doc.metadata["source"] = file.filename
                doc.text = clean_text(doc.text)

            chunks = create_chunks(documents)
            vector_store.add_chunks(chunks)
        finally:
            os.remove(tmp_path)

        return {
            "document_id": document_id,
            "status": "indexed",
            "document_title": file.filename or document_id,
            "chunks_indexed": len(chunks),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al indexar: {str(e)}")


def _normalizar_resultado(formato: str, resultado: Dict[str, Any], segundos: float) -> Dict[str, Any]:
    """Garantiza que todo resultado por formato tenga la misma forma, con error estructurado si falló."""
    status = resultado.get("status", "failed")
    error = resultado.get("error")

    if status == "success":
        error = None
    elif not error:
        causa = "NO_CONTEXT" if status == "no_results" else "INTERNAL_ERROR"
        error = build_error(causa, resultado.get("error_message") or "Fallo sin detalle.")

    return {
        "format": formato,
        "status": status,
        "content": resultado.get("content"),
        "sources_used": resultado.get("sources_used", []),
        "error_message": resultado.get("error_message") or (error["message"] if error else None),
        "error": error,
        "execution_time_seconds": round(segundos, 3),
    }


@app.post(
    "/api/v1/generate",
    response_model=GenerateResponse,
    responses=RESPUESTAS_DOC,
    summary="Genera formatos de estudio con errores estructurados por formato",
)
def generate_formats(payload: GenerateRequest):
    """
    Política HTTP:

    - **200**: metadatos y todos los formatos solicitados salieron bien.
    - **207**: fallo parcial controlado. Cada formato es atómico: si uno falla, los demás
      se generan igual. El detalle de cada fallo va en `results[].error`.
    - **Error global (429, 503, 504, 502, 404, 422, 500)**: TODAS las unidades fallaron.
      El código HTTP corresponde a la causa dominante y el cuerpo conserva el detalle por formato.
    """
    inicio = time.perf_counter()
    try:
        query_rag = payload.query or f"Conceptos principales sobre {payload.niche} para un perfil {payload.profile} con nivel {payload.detail_level}."
        if not payload.query and payload.learning_objective:
            query_rag += f" Objetivo: {payload.learning_objective}"

        exitosas = 0
        errores: List[Dict[str, Any]] = []

        # 1. METADATOS (una unidad más; su fallo no impide generar los formatos)
        try:
            meta = agent.extract_learning_metadata(
                query=query_rag, document_id=payload.document_id, niche=payload.niche
            )
        except Exception as e:
            logger.exception("extract_learning_metadata lanzó una excepción inesperada")
            meta = {"status": "failed", "content": None, "error_message": str(e), "error": classify_exception(e)}

        meta_status = meta.get("status", "failed")
        if meta_status == "success":
            meta_error = None
            exitosas += 1
        else:
            causa = "NO_CONTEXT" if meta_status == "no_results" else "INTERNAL_ERROR"
            meta_error = meta.get("error") or build_error(causa, meta.get("error_message") or "Fallo sin detalle.")
            errores.append(meta_error)

        learning_metadata = meta.get("content") or _metadata_fallback()

        # 2. FORMATOS (atómicos: cada uno en su propio try, ninguno interrumpe a los demás)
        respuestas_generadas = []
        for formato in payload.formats:
            t0 = time.perf_counter()

            if formato not in FORMATOS_SOPORTADOS:
                mensaje = f"El formato '{formato}' no está soportado en esta versión."
                resultado = {
                    "status": "failed",
                    "content": None,
                    "sources_used": [],
                    "error_message": mensaje,
                    "error": build_error("UNSUPPORTED_FORMAT", mensaje),
                }
            else:
                try:
                    resultado = agent.answer(
                        query=query_rag, document_id=payload.document_id,
                        formato=formato, perfil=payload.profile,
                        nicho=payload.niche, nivel=payload.detail_level,
                        learning_objective=payload.learning_objective
                    )
                except Exception as e:
                    logger.exception("agent.answer lanzó una excepción inesperada (formato=%s)", formato)
                    resultado = {
                        "status": "failed",
                        "content": None,
                        "sources_used": [],
                        "error_message": str(e),
                        "error": classify_exception(e),
                    }

            item = _normalizar_resultado(formato, resultado, time.perf_counter() - t0)
            respuestas_generadas.append(item)
            if item["status"] == "success":
                exitosas += 1
            else:
                errores.append(item["error"])

        # 3. ESTADO GLOBAL Y CÓDIGO HTTP
        overall_status, http_status = evaluar_resultado_global(exitosas, errores)

        cuerpo = {
            "document_id": payload.document_id,
            "overall_status": overall_status,
            "document_title": meta.get("document_title"),
            "document_description": meta.get("document_description"),
            "execution_time_seconds": round(time.perf_counter() - inicio, 3),
            "learning_metadata": learning_metadata,
            "learning_metadata_status": meta_status,
            "learning_metadata_error": meta_error,
            "results": respuestas_generadas,
        }
        return JSONResponse(status_code=http_status, content=jsonable_encoder(cuerpo))

    except Exception as e:
        logger.exception("Error inesperado en /generate")
        raise HTTPException(status_code=500, detail=f"Error del servidor: {str(e)}")


# ==========================================
# EVALUACIÓN DE RETRIEVAL (agente evaluador / Data)
# ==========================================
def _evaluar_caso(caso: RetrievalEvalCase) -> Dict[str, Any]:
    """
    Devuelve SIEMPRE un payload del contrato v2.0 de rag/contract.py (nunca lanza).

    retrieve_for_evaluation lanza ValueError con un case_id vacío y arma la respuesta de éxito
    FUERA de su try, así que un chunk sin document_id escaparía como excepción. Aquí ambos casos
    se convierten en payloads status="error".
    """
    if not caso.case_id.strip():
        return build_error_response(
            caso.case_id, caso.query, caso.top_k,
            "INVALID_INPUT", "case_id es obligatorio para evaluación y no puede estar vacío."
        )
    try:
        return agent.answer_for_evaluation(
            case_id=caso.case_id, query=caso.query,
            top_k=caso.top_k, metadata_filters=caso.metadata_filters
        )
    except Exception as e:
        logger.exception("answer_for_evaluation lanzó una excepción (case_id=%s)", caso.case_id)
        return build_error_response(
            caso.case_id, caso.query, caso.top_k,
            "RETRIEVAL_FAILED", f"{type(e).__name__}: {e}"
        )


@app.post(
    "/api/v1/evaluate/retrieval",
    response_model=RetrievalEvalResult,
    responses=RESPUESTAS_EVAL_CASO,
    summary="Evalúa un caso de retrieval (contrato v2.0)",
)
def evaluate_retrieval(caso: RetrievalEvalCase):
    """
    Devuelve el payload del contrato v2.0 SIN modificarlo (el mismo que valida data_ai).

    - **200**: `success` y `no_results` (un caso sin resultados es un dato: recall 0).
    - **422 / 500**: `status="error"` con `INVALID_INPUT` / `RETRIEVAL_FAILED`; el body sigue siendo el contrato.
    """
    payload = _evaluar_caso(caso)
    return JSONResponse(status_code=http_evaluacion_caso(payload), content=jsonable_encoder(payload))


@app.post(
    "/api/v1/evaluate/retrieval/batch",
    response_model=RetrievalEvalBatchResponse,
    responses=RESPUESTAS_EVAL_LOTE,
    summary="Evalúa un lote de casos de retrieval (cada caso es atómico)",
)
def evaluate_retrieval_batch_endpoint(lote: RetrievalEvalBatchRequest):
    """
    Cada caso se procesa de forma independiente: un error en uno no interrumpe los demás.
    `results` contiene los payloads v2.0 en el mismo orden de `cases`, listos para `evaluate_retrieval_batch`.

    - **200**: ningún error. **207**: mezcla de casos con y sin error.
    - **422 / 500**: todos los casos fallaron (500 si hay algún RETRIEVAL_FAILED).
    """
    inicio = time.perf_counter()
    payloads = [_evaluar_caso(caso) for caso in lote.cases]
    overall_status, http_status = evaluar_lote_evaluacion(payloads)
    fallidos = sum(1 for p in payloads if p.get("status") == "error")
    cuerpo = {
        "overall_status": overall_status,
        "total": len(payloads),
        "succeeded": len(payloads) - fallidos,
        "failed": fallidos,
        "execution_time_seconds": round(time.perf_counter() - inicio, 3),
        "results": payloads,
    }
    return JSONResponse(status_code=http_status, content=jsonable_encoder(cuerpo))


# ==========================================
# OPERACIÓN
# ==========================================
@app.get("/api/v1/health", response_model=HealthResponse, summary="Estado del servicio (no llama a Gemini)")
def health():
    vector_ok = True
    try:
        vector_store.collection.count()
    except Exception:
        logger.exception("health: el vector store no responde")
        vector_ok = False
    key_ok = bool(API_KEY) and not API_KEY.startswith("fake")
    return {
        "status": "ok" if (vector_ok and key_ok) else "degraded",
        "model": MODEL_NAME,
        "gemini_key_configured": key_ok,
        "vector_store_ok": vector_ok,
    }


@app.delete(
    "/api/v1/documents/{document_id}",
    response_model=DeleteResponse,
    responses={404: {"model": DeleteResponse, "description": "El document_id no tiene chunks indexados."}},
    summary="Borra todos los chunks de un documento",
)
def delete_document(document_id: str):
    try:
        existentes = vector_store.collection.get(where={"document_id": document_id}, include=["metadatas"])
        ids = existentes.get("ids") or []
        if not ids:
            return JSONResponse(
                status_code=404,
                content={"document_id": document_id, "status": "not_found", "chunks_deleted": 0},
            )
        vector_store.collection.delete(ids=ids)
        return {"document_id": document_id, "status": "deleted", "chunks_deleted": len(ids)}
    except Exception as e:
        logger.exception("Error al borrar el documento %s", document_id)
        raise HTTPException(status_code=500, detail=f"Error interno al borrar: {str(e)}")
