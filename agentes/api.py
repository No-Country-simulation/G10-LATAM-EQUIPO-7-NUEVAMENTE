import os
import time
import logging
import tempfile
import json
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
from .graph import (
    compilar_subgrafo_formato,
    traducir_respuesta_evaluador,
    compilar_grafo_generacion,
    ejecutar_grafo,
)
from .state import new_agent_state

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

_revision_cache: Dict[str, Dict[str, Any]] = {}

def _metadata_fallback() -> Dict[str, Any]:
    return {
        "document_title": "Título no generado",
        "key_concepts": ["Error al extraer conceptos"],
        "prerequisites": ["No se pudieron determinar"],
        "estimated_time_minutes": 0
    }


def _normalizar_feedback_revision(
    evaluacion: Dict[str, Any],
    document_id: str,
    formato: str,
) -> Dict[str, Any]:
    if "semantic_evaluation" in evaluacion:
        return traducir_respuesta_evaluador(
            evaluacion,
            document_id=document_id,
            formato=formato,
        )

    verdict = evaluacion.get("verdict")
    issues: List[str] = []
    for observacion in evaluacion.get("observations") or []:
        if not isinstance(observacion, dict):
            continue
        descripcion = observacion.get("description") or observacion.get("message")
        if not descripcion:
            continue
        tipo = observacion.get("type") or observacion.get("dimension") or "observación"
        severidad = observacion.get("severity")
        prefijo = f"[{tipo} · severidad {severidad}]" if severidad else f"[{tipo}]"
        issues.append(f"{prefijo} {descripcion}")

    suggestions: List[str] = []
    for recomendacion in evaluacion.get("recommendations") or []:
        if not isinstance(recomendacion, dict):
            continue
        descripcion = recomendacion.get("description") or recomendacion.get("message")
        if descripcion:
            accion = recomendacion.get("action")
            prefijo = f"[{accion}] " if accion else ""
            suggestions.append(f"{prefijo}{descripcion}")

    if verdict != "approved" and not issues and not suggestions:
        issues.append("El evaluador solicitó revisión sin detallar observaciones específicas.")

    return {
        "approved": verdict == "approved",
        "verdict": verdict,
        "score": None,
        "scores": None,
        "issues": issues,
        "suggestions": suggestions,
        "reviewed": True,
        "evaluator_error": None,
        "evaluator_version": None,
        "rubric_version": None,
    }


class GenerateRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    formats: List[str] = Field(default_factory=list)
    profile: str = Field(..., min_length=1)
    niche: str = Field(..., min_length=1)
    detail_level: str = Field(..., min_length=1)
    learning_objective: Optional[str] = None
    query: Optional[str] = Field(None)


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Causa normalizada.")
    message: str = Field(..., description="Detalle corto.")
    retryable: bool = Field(..., description="True si reintentable.")
    http_status: int = Field(..., description="Código HTTP.")
    upstream_status: Optional[int] = Field(None)
    provider: str = Field(..., description="gemini o internal.")


class FormatResult(BaseModel):
    format: str
    status: str = Field(..., description="success | failed | no_results")
    content: Optional[Dict[str, Any]] = None
    sources_used: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    error: Optional[ErrorDetail] = None
    execution_time_seconds: float


class GenerateResponse(BaseModel):
    document_id: str
    overall_status: str = Field(..., description="success | partial | failed")
    document_title: Optional[str] = Field(None)
    document_description: Optional[str] = Field(None)
    execution_time_seconds: float
    learning_metadata: Dict[str, Any]
    learning_metadata_status: str = Field(..., description="success | failed | no_results")
    learning_metadata_error: Optional[ErrorDetail] = None
    results: List[FormatResult]


class GenerationContext(BaseModel):
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str] = None


class ReviseRequest(BaseModel):
    revision_id: str
    original_format_id: str
    document_id: str
    format: str
    generation_context: GenerationContext
    previous_content: Dict[str, Any]
    chunks_used: List[Dict[str, Any]]
    evaluator_response: Dict[str, Any]


class ReviseResponse(BaseModel):
    revision_id: str
    original_format_id: str
    document_id: str
    format: str
    status: str = Field(..., description="success | failed")
    content: Optional[Dict[str, Any]] = None
    sources_used: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    error: Optional[ErrorDetail] = None
    execution_time_seconds: float


class IndexResponse(BaseModel):
    document_id: str
    status: Literal["indexed"]
    document_title: str = Field(..., description="Nombre del archivo recibido.")
    chunks_indexed: int = Field(..., description="Cantidad de fragmentos.")


class DeleteResponse(BaseModel):
    document_id: str
    status: Literal["deleted", "not_found"]
    chunks_deleted: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model: str
    gemini_key_configured: bool
    vector_store_ok: bool


class RetrievalEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(..., min_length=1, max_length=128)
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    metadata_filters: Optional[Dict[str, Any]] = None


class RetrievedChunk(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    score: float
    text: str
    metadata: Dict[str, Any]


class RetrievalError(BaseModel):
    code: str
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
    succeeded: int
    failed: int
    execution_time_seconds: float
    results: List[RetrievalEvalResult]


_DESCRIPCION_EVAL = {
    207: "Lote con casos exitosos y casos con status=error.",
    422: "INVALID_INPUT en el caso.",
    500: "RETRIEVAL_FAILED en el caso.",
}
RESPUESTAS_EVAL_CASO = {c: {"model": RetrievalEvalResult, "description": d} for c, d in _DESCRIPCION_EVAL.items() if c != 207}
RESPUESTAS_EVAL_LOTE = {c: {"model": RetrievalEvalBatchResponse, "description": d} for c, d in _DESCRIPCION_EVAL.items()}

_DESCRIPCION_HTTP = {
    207: "Fallo parcial controlado.",
    404: "Todo falló: NO_CONTEXT.",
    422: "Todo falló: UNSUPPORTED_FORMAT.",
    429: "Todo falló: RESOURCE_EXHAUSTED.",
    500: "Todo falló por configuración interna.",
    502: "Todo falló: respuesta inválida.",
    503: "Todo falló: saturado.",
    504: "Todo falló: timeout.",
}
RESPUESTAS_DOC = {
    codigo: {"model": GenerateResponse, "description": texto}
    for codigo, texto in _DESCRIPCION_HTTP.items()
}


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
            
            titulo_generado = file.filename or document_id

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return {
            "document_id": document_id,
            "status": "indexed",
            "document_title": titulo_generado,
            "chunks_indexed": len(chunks)
        }
    except Exception as e:
        logger.exception("Error interno al indexar")
        raise HTTPException(status_code=500, detail="Error interno al indexar el documento.")


@app.post(
    "/api/v1/generate",
    response_model=GenerateResponse,
    responses=RESPUESTAS_DOC,
    summary="Genera formatos de estudio utilizando LangGraph",
)
def generate_formats(payload: GenerateRequest):
    inicio = time.perf_counter()
    try:
        query_rag = payload.query or f"Conceptos principales sobre {payload.niche} para un perfil {payload.profile} con nivel {payload.detail_level}."
        if not payload.query and payload.learning_objective:
            query_rag += f" Objetivo: {payload.learning_objective}"

        initial_state = new_agent_state(
            document_id=payload.document_id,
            formats=payload.formats,
            profile=payload.profile,
            niche=payload.niche,
            detail_level=payload.detail_level,
            learning_objective=payload.learning_objective,
            query=query_rag
        )

        grafo = compilar_grafo_generacion(agent)
        final_state = ejecutar_grafo(grafo, initial_state)

        meta_status = final_state.get("learning_metadata_status", "failed")
        learning_metadata = final_state.get("learning_metadata") or _metadata_fallback()
        meta_error = final_state.get("learning_metadata_error")

        if meta_status != "success" and not meta_error:
            error_code = "NO_CONTEXT" if meta_status == "no_results" else "INTERNAL_ERROR"
            meta_error = build_error(error_code, "No se pudieron extraer los metadatos del documento.")

        exitosas = 0
        if meta_status == "success":
            exitosas += 1

        format_results_raw = final_state.get("final_results", [])
        respuestas_generadas = []
        errores = []
        if meta_status != "success" and meta_error:
            errores.append(meta_error)

        for item_res in format_results_raw:
            fmt = item_res.get("format", "desconocido")
            st = item_res.get("status", "failed")
            
            normalized = {
                "format": fmt,
                "status": st,
                "content": item_res.get("content"),
                "sources_used": item_res.get("sources_used", []),
                "error_message": item_res.get("error_message"),
                "error": item_res.get("error"),
                "execution_time_seconds": round(item_res.get("execution_time_seconds", 0.1), 3)
            }
            if st == "success":
                exitosas += 1
                normalized["error"] = None
            else:
                if normalized["error"] is None:
                    causa = "NO_CONTEXT" if st == "no_results" else "INTERNAL_ERROR"
                    normalized["error"] = build_error(causa, normalized.get("error_message") or "Fallo en generación.")
                errores.append(normalized["error"])
                
            respuestas_generadas.append(normalized)

        overall_status, http_status = evaluar_resultado_global(exitosas, errores)
        
        # Selección robusta del título con respaldo inteligente solicitada por QA
        titulo_semantico = learning_metadata.get("document_title")
        titulo_original = final_state.get("document_title")
        if meta_status == "success" and titulo_semantico and titulo_semantico != "Título no generado":
            titulo_crudo = titulo_semantico
        else:
            titulo_crudo = titulo_original or titulo_semantico or "Título no generado"

        cuerpo = {
            "document_id": payload.document_id,
            "overall_status": overall_status,
            "document_title": titulo_crudo,
            "document_description": final_state.get("document_description"),
            "execution_time_seconds": round(time.perf_counter() - inicio, 3),
            "learning_metadata": learning_metadata,
            "learning_metadata_status": meta_status,
            "learning_metadata_error": meta_error,
            "results": respuestas_generadas,
        }
        
        respuesta_validada = GenerateResponse.model_validate(cuerpo)
        return JSONResponse(
            status_code=http_status, 
            content=respuesta_validada.model_dump(mode="json")
        )

    except Exception as e:
        logger.exception("Error inesperado en /generate con LangGraph")
        raise HTTPException(status_code=500, detail="Error interno del servidor en el motor de agentes.")


@app.post(
    "/api/v1/revise",
    response_model=ReviseResponse,
    summary="Aplica correcciones pedagógicas"
)
def revise_format(payload: ReviseRequest):
    inicio = time.perf_counter()
    
    if payload.revision_id in _revision_cache:
        cached = _revision_cache[payload.revision_id]
        return JSONResponse(status_code=cached["status_code"], content=cached["content"])

    def _cache_and_return(status_code: int, content: dict):
        _revision_cache[payload.revision_id] = {"status_code": status_code, "content": content}
        return JSONResponse(status_code=status_code, content=content)

    try:
        if payload.format not in FORMATOS_SOPORTADOS:
            raise ValueError(f"El formato '{payload.format}' no está soportado.")

        textos_chunks = [c.get("text", "") for c in payload.chunks_used if isinstance(c, dict) and c.get("text")]
        retrieved_context = "\n\n".join(textos_chunks).strip()
        fuentes_usadas = payload.chunks_used

        if not retrieved_context:
            query = f"Conceptos principales de {payload.generation_context.niche}"
            retrieval_res = agent.retriever.retrieve(
                query=query,
                top_k=5,
                metadata_filters={"document_id": payload.document_id}
            )
            
            textos = []
            fuentes_usadas = []
            for r in retrieval_res:
                if hasattr(r, "text"):
                    textos.append(r.text)
                    fuentes_usadas.append(r.model_dump() if hasattr(r, "model_dump") else r.__dict__)
                elif isinstance(r, dict):
                    textos.append(r.get("text", ""))
                    fuentes_usadas.append(r)
                    
            retrieved_context = "\n\n".join(textos).strip()

        if not retrieved_context:
            raise ValueError(f"No se encontró contexto indexado para el documento '{payload.document_id}'.")

        feedback_normalizado = _normalizar_feedback_revision(
            payload.evaluator_response,
            document_id=payload.document_id,
            formato=payload.format,
        )

        initial_format_state = {
            "format": payload.format,
            "document_id": payload.document_id,
            "profile": payload.generation_context.profile,
            "niche": payload.generation_context.niche,
            "detail_level": payload.generation_context.detail_level,
            "learning_objective": payload.generation_context.learning_objective,
            "retrieved_context": retrieved_context,
            "sources_used": fuentes_usadas,
            "retrieval_error": None,
            "max_revisions": 2,
            "started_at": time.time(),
            "current_content": payload.previous_content,
            "current_error": None,
            "feedback": feedback_normalizado,
            "feedback_history": [feedback_normalizado],
            "revision_count": 1,
            "outcome": None,
        }

        subgrafo = compilar_subgrafo_formato(agent)
        final_state = subgrafo.invoke(initial_format_state)

        outcome: Optional[Dict[str, Any]] = final_state.get("outcome")
        if not isinstance(outcome, dict):
            raise RuntimeError("El subgrafo no devolvió un outcome válido.")

        fuentes_finales = (
            outcome.get("sources_used")
            or final_state.get("sources_used")
            or fuentes_usadas
        )

        if outcome.get("status") != "success":
            error_outcome = outcome.get("error") or build_error(
                "INTERNAL_ERROR",
                outcome.get("error_message") or "La revisión no produjo un resultado exitoso.",
            )
            cuerpo_error = {
                "revision_id": payload.revision_id,
                "original_format_id": payload.original_format_id,
                "document_id": payload.document_id,
                "format": payload.format,
                "status": "failed",
                "content": None,
                "sources_used": [], 
                "error_message": error_outcome["message"],
                "error": error_outcome,
                "execution_time_seconds": round(time.perf_counter() - inicio, 3),
            }
            respuesta_validada = ReviseResponse.model_validate(cuerpo_error)
            http_code = error_outcome.get("http_status", 500)
            return _cache_and_return(http_code, respuesta_validada.model_dump(mode="json"))

        corrected_content = outcome.get("content") or final_state.get("current_content")
        if not corrected_content:
            raise ValueError("El agente revisor devolvió un contenido vacío tras la corrección.")

        tiempo_ejecucion = round(time.perf_counter() - inicio, 3)
        cuerpo_exito = {
            "revision_id": payload.revision_id,
            "original_format_id": payload.original_format_id,
            "document_id": payload.document_id,
            "format": payload.format,
            "status": "success",
            "content": corrected_content,
            "sources_used": fuentes_finales,
            "error_message": None,
            "error": None,
            "execution_time_seconds": tiempo_ejecucion
        }
        
        respuesta_validada = ReviseResponse.model_validate(cuerpo_exito)
        return _cache_and_return(200, respuesta_validada.model_dump(mode="json"))

    except Exception as e:
        logger.exception("Error en /revise (revision_id=%s)", payload.revision_id)
        tiempo_ejecucion = round(time.perf_counter() - inicio, 3)
        error_detail = classify_exception(e)
        
        cuerpo_error = {
            "revision_id": payload.revision_id,
            "original_format_id": payload.original_format_id,
            "document_id": payload.document_id,
            "format": payload.format,
            "status": "failed",
            "content": None,
            "sources_used": [],
            "error_message": str(e),
            "error": error_detail,
            "execution_time_seconds": tiempo_ejecucion
        }
        
        respuesta_validada = ReviseResponse.model_validate(cuerpo_error)
        http_code = error_detail.get("http_status", 500) if isinstance(error_detail, dict) else 500
        return _cache_and_return(http_code, respuesta_validada.model_dump(mode="json"))


def _evaluar_caso(caso: RetrievalEvalCase) -> Dict[str, Any]:
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
    summary="Evalúa un caso de retrieval",
)
def evaluate_retrieval(caso: RetrievalEvalCase):
    payload = _evaluar_caso(caso)
    return JSONResponse(status_code=http_evaluacion_caso(payload), content=jsonable_encoder(payload))


@app.post(
    "/api/v1/evaluate/retrieval/batch",
    response_model=RetrievalEvalBatchResponse,
    responses=RESPUESTAS_EVAL_LOTE,
    summary="Evalúa un lote de casos",
)
def evaluate_retrieval_batch_endpoint(lote: RetrievalEvalBatchRequest):
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


@app.get("/api/v1/health", response_model=HealthResponse, summary="Estado del servicio")
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
        raise HTTPException(status_code=500, detail="Error interno al borrar el documento.")