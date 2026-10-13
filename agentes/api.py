import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path

from .rag.models import Document
from .rag.cleaner import clean_text
from .rag.chunker import create_chunks
from .rag.embeddings import MultilingualEmbedding
from .rag.vector_store import VectorStore
from .agent_v1 import AgentV1
from .rag.extractor import extract_document

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

embedding_service = MultilingualEmbedding()
vector_store = VectorStore(embedding_service=embedding_service)
agent = AgentV1(vector_store=vector_store)

app = FastAPI(title="NuevaMente - API de Agentes")

class GenerateRequest(BaseModel):
    document_id: str
    formats: List[str]
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str] = None
    query: Optional[str] = Field(None)

@app.post("/api/v1/index")
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
            
        return {"document_id": document_id, "status": "indexed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al indexar: {str(e)}")

@app.post("/api/v1/generate")
def generate_formats(payload: GenerateRequest):
    try:
        respuestas_generadas = []
        
        query_rag = payload.query or f"Conceptos principales sobre {payload.niche} para un perfil {payload.profile} con nivel {payload.detail_level}."
        if not payload.query and payload.learning_objective:
            query_rag += f" Objetivo: {payload.learning_objective}"

        # 1. EXTRACCIÓN CON FALLBACK (Comportamiento Sprint 3)
        metadata_response = agent.extract_learning_metadata(
            query=query_rag, document_id=payload.document_id, niche=payload.niche
        )
        
        learning_metadata = metadata_response.get("content") or {
            "key_concepts": ["Error al extraer conceptos"],
            "prerequisites": ["No se pudieron determinar"],
            "estimated_time_minutes": 0
        }

        # 2. GENERACIÓN DE FORMATOS (Sin Fail Fast)
        for formato in payload.formats:
            if formato not in ["quiz", "flashcards", "tldr", "video_script"]:
                respuestas_generadas.append({
                    "format": formato,
                    "status": "failed",
                    "error_message": f"Formato '{formato}' no soportado"
                })
                continue

            resultado_atomico = agent.answer(
                query=query_rag, document_id=payload.document_id,
                formato=formato, perfil=payload.profile,
                nicho=payload.niche, nivel=payload.detail_level,
                learning_objective=payload.learning_objective
            )
            
            respuestas_generadas.append({
                "format": formato,
                "status": resultado_atomico["status"],
                "content": resultado_atomico.get("content"),
                "sources_used": resultado_atomico.get("sources_used", []),
                "error_message": resultado_atomico.get("error_message")
            })

        return {
            "document_id": payload.document_id,
            "learning_metadata": learning_metadata,
            "results": respuestas_generadas
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del servidor: {str(e)}")