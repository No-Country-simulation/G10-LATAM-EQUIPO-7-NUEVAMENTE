from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from .rag.models import Document
from .rag.cleaner import clean_text
from .rag.chunker import create_chunks
from .rag.embeddings import MultilingualEmbedding
from .rag.vector_store import VectorStore
from .agent_v1 import AgentV1

# Inicializamos las dependencias centrales del RAG
embedding_service = MultilingualEmbedding()
vector_store = VectorStore(embedding_service=embedding_service)
agent = AgentV1(vector_store=vector_store)

app = FastAPI(title="NuevaMente - API de Agentes")

# ==========================================
# CONTRATOS DE ENTRADA (Validación Pydantic)
# ==========================================
class IndexRequest(BaseModel):
    document_id: str
    nombre: str
    mime_type: str
    contenido: str

class GenerateRequest(BaseModel):
    document_id: str
    formats: List[str]
    profile: str
    niche: str
    detail_level: str

# ==========================================
# ENDPOINTS
# ==========================================
@app.post("/api/v1/index")
def index_document(payload: IndexRequest):
    """
    Recibe el contenido crudo desde Backend y lo indexa en ChromaDB.
    """
    try:
        # Limpieza de texto usando la función existente en cleaner.py
        texto_limpio = clean_text(payload.contenido)
        
        # Creación del documento en memoria fijando explícitamente el document_id
        doc = Document(
            text=texto_limpio,
            metadata={
                "document_id": payload.document_id, 
                "source": payload.nombre
            }
        )
        
        # Segmentación y almacenamiento en la base vectorial
        chunks = create_chunks([doc])
        vector_store.add_chunks(chunks)
        
        return {
            "document_id": payload.document_id,
            "status": "indexed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/generate")
def generate_formats(payload: GenerateRequest):
    """
    Itera sobre los formatos solicitados, aplica capacidad atómica y devuelve los resultados.
    """
    respuestas_generadas = []
    
    # Query dinámico para optimizar el retriever según las necesidades del usuario
    query_dinamico = f"Conceptos principales sobre {payload.niche} para un perfil {payload.profile} con nivel {payload.detail_level}."

    for formato in payload.formats:
        resultado_atomico = agent.answer(
            query=query_dinamico,
            document_id=payload.document_id,
            formato=formato,
            perfil=payload.profile,
            nicho=payload.niche,
            nivel=payload.detail_level
        )
        
        respuestas_generadas.append({
            "format": formato,
            "status": resultado_atomico["status"],
            "content": resultado_atomico["content"],
            "sources_used": resultado_atomico.get("sources_used", [])
        })

    return {
        "document_id": payload.document_id,
        "results": respuestas_generadas
    }