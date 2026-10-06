import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .rag.retriever import RetrieverService

# Carga única del archivo .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuración única, estricta y segura del cliente GenAI (sin imprimir claves en consola)
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL_NAME = os.environ["GEMINI_MODEL"]

client = genai.Client(api_key=API_KEY)

# ==========================================
# PROMPTS BASE Y METADATOS PEDAGÓGICOS
# ==========================================
# Añadimos una instrucción transversal para forzar la extracción de los LearningMetadata
INSTRUCCION_METADATOS = """
Además del formato solicitado, DEBES extraer obligatoriamente los siguientes metadatos pedagógicos basándote en el contexto:
1. "key_concepts": Lista exacta de 3 a 5 conceptos técnicos o ideas principales abordadas.
2. "prerequisites": Lista de 1 a 3 conocimientos previos recomendados para entender el texto. (Si es un tema básico, deduce conceptos fundamentales genéricos).
3. "estimated_time_minutes": Calcula el tiempo estimado de estudio (en minutos) basándote en la longitud y complejidad del contexto provisto.
"""

PROMPTS_BASE = {
    "quiz": "Genera un cuestionario interactivo de opción múltiple (mínimo 3 preguntas) asegurando incluir la respuesta correcta, opciones de distracción coherentes y una breve justificación pedagógica.",
    "flashcards": "Genera 5 tarjetas de memorización (flashcards). Cada una debe tener un concepto clave en la cara frontal y su definición concisa en la cara trasera."
}

class AgentV1:
    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def answer(self, query: str, document_id: str, formato: str, perfil: str, nicho: str, nivel: str, learning_objective: str = None, top_k: int = 5) -> dict:
        chunks_usados = []
        
        # CAPACIDAD ATÓMICA COMPLETA: El try/except cubre recuperación, prompt, llamada al LLM y validación Pydantic
        try:
            # 1. Recuperación Híbrida en ChromaDB (Fase 1, 2 y 3 ejecutadas desde el backend)
            # Pasamos dict con filter por document_id para que el nuevo Retrieval V2 funcione
            resultados = self.retriever.retrieve(query=query, top_k=top_k, metadata_filters={"document_id": document_id})
            
            if not resultados:
                return {
                    "status": "no_results", 
                    "content": None, 
                    "sources_used": [],
                    "error_message": "No se encontró contexto suficiente en el documento."
                }

            contexto_unificado = "\n\n".join([res.text for res in resultados])
            
            # 2. Construcción de evidencia de fuentes usadas
            for index, res in enumerate(resultados):
                chunks_usados.append({
                    "rank": index + 1,
                    "chunk_id": res.chunk_id,
                    "document_id": getattr(res, "document_id", document_id),
                    "score": getattr(res, "score", 0.0),
                    "text": res.text
                })

            # 3. Ensamblar Prompt Dinámico Adaptativo
            instruccion_base = PROMPTS_BASE.get(formato.lower(), "Genera un resumen estructurado.")
            
            prompt_final = f"""
            INSTRUCCIÓN PRINCIPAL:
            {instruccion_base}
            
            METADATOS PEDAGÓGICOS OBLIGATORIOS (LearningMetadata):
            {INSTRUCCION_METADATOS}
            
            REGLAS DE ADAPTACIÓN:
            - Perfil objetivo: {perfil}
            - Nicho temático: {nicho}
            - Nivel de detalle: {nivel}
            """
            if learning_objective:
                prompt_final += f"- Objetivo de aprendizaje: {learning_objective}\n"
                
            prompt_final += f"""
            Adapta el lenguaje y la complejidad estrictamente a este perfil.
            Genera identificadores únicos (IDs) cortos y alfanuméricos para cada pregunta o tarjeta.

            CONTEXTO RECUPERADO (Usa ÚNICA Y ESTRICTAMENTE esta información, no inventes datos externos):
            {contexto_unificado}
            """

            # 4. Importación local para prevenir dependencias circulares con api.py
            from .api import QuizContent, FlashcardsContent 

            # Mapeamos el formato al contrato Pydantic correcto
            if formato.lower() == "quiz":
                esquema_salida = QuizContent
            elif formato.lower() == "flashcards":
                esquema_salida = FlashcardsContent
            else:
                raise ValueError(f"Formato '{formato}' no soportado para generación.")

            # 5. Llamada al LLM usando el SDK moderno 'google-genai' con Structured Outputs
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=esquema_salida,
                    temperature=0.2
                )
            )
            
            # 6. Extracción validada mediante response.parsed del SDK moderno
            parsed_content = response.parsed
            texto_generado = parsed_content.model_dump()

            return {
                "status": "success",
                "content": texto_generado,
                "sources_used": chunks_usados,
                "error_message": None
            }

        except Exception as e:
            # Respuesta controlada exigida por Backend/Frontend (status "failed", content null)
            return {
                "status": "failed",
                "content": None,
                "sources_used": chunks_usados,
                "error_message": f"Error crítico en el pipeline o generación con Gemini: {str(e)}"
            }

    def answer_for_evaluation(self, case_id: str, query: str, top_k: int = 5) -> dict:
        return self.retriever.retrieve_for_evaluation(case_id=case_id, query=query, top_k=top_k)