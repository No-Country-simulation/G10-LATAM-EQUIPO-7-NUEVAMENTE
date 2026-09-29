import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List

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
# CONTRATOS DE ENTRADA (Validación Pydantic)
# ==========================================
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