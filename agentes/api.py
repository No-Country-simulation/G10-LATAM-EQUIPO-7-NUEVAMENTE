import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from pathlib import Path

from .rag.models import Document
from .rag.cleaner import clean_text
from .rag.chunker import create_chunks
from .rag.embeddings import MultilingualEmbedding
from .rag.vector_store import VectorStore
from .agent_v1 import AgentV1
from .rag.extractor import extract_document  # Importamos el extractor original

# Inicializamos las dependencias centrales del RAG
embedding_service = MultilingualEmbedding()
vector_store = VectorStore(embedding_service=embedding_service)
agent = AgentV1(vector_store=vector_store)

app = FastAPI(title="NuevaMente - API de Agentes")

# ==========================================
# ESQUEMAS ESTRUCTURADOS (Contratos Data/IA)
# ==========================================
class LearningMetadata(BaseModel):
    key_concepts: List[str] = Field(..., description="Lista de 3 a 5 conceptos clave abordados en el contenido.")
    prerequisites: List[str] = Field(..., description="Conocimientos previos recomendados para entender el tema.")
    estimated_time_minutes: int = Field(..., description="Tiempo estimado de estudio o lectura en minutos.")

class CardItem(BaseModel):
    card_id: str = Field(..., description="Identificador único de la tarjeta.")
    front: str = Field(..., description="Concepto o pregunta (anverso de la tarjeta).")
    back: str = Field(..., description="Definición o respuesta (reverso de la tarjeta).")

class FlashcardsContent(BaseModel):
    title: str = Field(..., description="Título del conjunto de flashcards.")
    instructions: str = Field(..., description="Instrucciones de uso pedagógico.")
    cards: List[CardItem] = Field(..., description="Lista de flashcards generadas.")

class QuizItem(BaseModel):
    question_id: str = Field(..., description="Identificador único de la pregunta.")
    question: str = Field(..., description="La pregunta de opción múltiple.")
    options: List[str] = Field(..., description="Lista de opciones posibles (ej. A, B, C, D).")
    correct_answer: str = Field(..., description="El texto exacto de la respuesta correcta.")
    explanation: str = Field(..., description="Explicación pedagógica de por qué es correcta.")

class QuizContent(BaseModel):
    title: str = Field(..., description="Título del cuestionario.")
    instructions: str = Field(..., description="Instrucciones para resolver el cuestionario.")
    questions: List[QuizItem] = Field(..., description="Lista de preguntas del quiz.")

class TLDRContent(BaseModel):
    title: str = Field(..., description="Título breve del contenido.")
    summary: str = Field(..., description="Resumen ejecutivo conciso del contexto recuperado.")
    key_points: List[str] = Field(..., description="Lista de los puntos esenciales.")
    conclusion: str = Field(..., description="Idea final o takeaway principal.")

class VideoScene(BaseModel):
    scene_id: str = Field(..., description="Identificador corto de la escena.")
    title: str = Field(..., description="Título de la escena.")
    narration: str = Field(..., description="Texto que pronunciaría el docente o narrador.")
    visual_description: str = Field(..., description="Qué debería verse en pantalla.")
    duration_seconds: int = Field(..., description="Duración estimada de esa escena en segundos.")

class VideoScriptContent(BaseModel):
    title: str = Field(..., description="Título general.")
    estimated_duration_minutes: int = Field(..., description="Duración estimada total.")
    scenes: List[VideoScene] = Field(..., description="Secuencia ordenada del guion.")

# ==========================================
# CONTRATOS DE ENTRADA (Validación Pydantic)
# ==========================================
class GenerateRequest(BaseModel):
    document_id: str
    formats: List[str]
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str] = None
    query: Optional[str] = Field(None, description="Consulta directa (opcional). Usada prioritariamente para benchmarks y búsquedas exactas.")

# ==========================================
# ENDPOINTS
# ==========================================
@app.post("/api/v1/index")
async def index_document(document_id: str = Form(...), file: UploadFile = File(...)):
    """
    Recibe un archivo binario mediante multipart/form-data, lo guarda temporalmente,
    extrae su contenido (PDF/TXT/MD) y lo indexa en ChromaDB.
    """
    try:
        # 1. Guardar el archivo temporalmente preservando su extensión (ej. .pdf)
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contenido = await file.read()
            tmp.write(contenido)
            tmp_path = tmp.name

        try:
            # 2. Extraer el texto real usando tu extractor existente
            documents = extract_document(tmp_path)
            
            # 3. Inyectar el document_id y limpiar texto
            for doc in documents:
                doc.metadata["document_id"] = document_id
                doc.metadata["source"] = file.filename
                doc.text = clean_text(doc.text)
                
            # 4. Chunking y Vector Store
            chunks = create_chunks(documents)
            vector_store.add_chunks(chunks)
            
        finally:
            # 5. Limpieza vital: eliminar el archivo temporal del disco
            os.remove(tmp_path)
            
        return {
            "document_id": document_id,
            "status": "indexed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/generate")
def generate_formats(payload: GenerateRequest):
    """
    Itera sobre los formatos solicitados, aplica capacidad atómica y devuelve los resultados
    bajo los contratos estrictos de Data/IA y Backend (Metadata en la raíz).
    """
    respuestas_generadas = []
    
    if payload.query:
        query_rag = payload.query
    else:
        query_rag = f"Conceptos principales sobre {payload.niche} para un perfil {payload.profile} con nivel {payload.detail_level}."
        if payload.learning_objective:
            query_rag += f" Objetivo: {payload.learning_objective}"

    # ==========================================
    # 1. EXTRACCIÓN ÚNICA DE LEARNING METADATA
    # ==========================================
    metadata_response = agent.extract_learning_metadata(query=query_rag, document_id=payload.document_id)
    
    # Manejo del fallback: si la IA falla extrayendo metadatos, mandamos un default vacío pero no rompemos la API
    if metadata_response["status"] == "success":
        learning_metadata = metadata_response["content"]
    else:
        learning_metadata = {
            "key_concepts": [],
            "prerequisites": [],
            "estimated_time_minutes": 0
        }

    # ==========================================
    # 2. GENERACIÓN PARALELA DE FORMATOS
    # ==========================================
    for formato in payload.formats:
        
        # ==========================================
        # VALIDACIÓN DE FORMATO ATÓMICA
        # ==========================================
        if formato not in ["quiz", "flashcards", "tldr", "video_script"]:
            respuestas_generadas.append({
                "format": formato,
                "status": "failed",
                "content": None,
                "sources_used": [],
                "error_message": f"El formato '{formato}' no está soportado en esta versión."
            })
            continue 

        resultado_atomico = agent.answer(
            query=query_rag,
            document_id=payload.document_id,
            formato=formato,
            perfil=payload.profile,
            nicho=payload.niche,
            nivel=payload.detail_level,
            learning_objective=payload.learning_objective
        )
        
        respuestas_generadas.append({
            "format": formato,
            "status": resultado_atomico["status"],
            "content": resultado_atomico["content"],
            "sources_used": resultado_atomico.get("sources_used", []),
            "error_message": resultado_atomico.get("error_message")
        })

    # ==========================================
    # 3. ENSAMBLAJE FINAL DEL CONTRATO
    # ==========================================
    return {
        "document_id": payload.document_id,
        "learning_metadata": learning_metadata,  # ¡Inyectado a nivel raíz!
        "results": respuestas_generadas
    }