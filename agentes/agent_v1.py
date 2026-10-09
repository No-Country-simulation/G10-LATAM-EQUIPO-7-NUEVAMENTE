import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .rag.retriever import RetrieverService

from .generated_schemas import (
    LearningMetadata,
    QuizContent,
    FlashcardsContent,
    TLDRContent,
    VideoScriptContent,
)

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL_NAME = os.environ["GEMINI_MODEL"]

client = genai.Client(api_key=API_KEY)

PROMPTS_BASE = {
    "quiz": "Genera un cuestionario interactivo de opción múltiple (mínimo 3 preguntas) asegurando incluir la respuesta correcta, opciones de distracción coherentes y una breve justificación pedagógica.",
    "flashcards": "Genera 5 tarjetas de memorización (flashcards). Cada una debe tener un concepto clave en la cara frontal y su definición concisa en la cara trasera.",
    "tldr": "Genera un resumen ejecutivo conciso basado exclusivamente en el contexto recuperado, sin inventar información externa. Identifica entre 3 y 7 puntos clave esenciales cuando el contexto lo permita y cierra con la conclusión o takeaway principal. Adapta el lenguaje a profile, niche y detail_level.",
    "video_script": "Genera un guion educativo de clase o video dividido en una secuencia ordenada de escenas. Usa únicamente el contexto recuperado sin inventar datos técnicos ausentes, adaptando el lenguaje a profile, niche y detail_level, y respetando learning_objective si existe. Cada escena debe incluir un identificador corto (scene_id), título, texto de narración pedagógica que pronunciaría el docente o narrador, descripción visual de lo que debería verse en pantalla y duration_seconds. La duración estimada total (estimated_duration_minutes) debe ser razonablemente coherente con la suma de las duraciones de las escenas."
}

def _generate_and_parse(prompt: str, schema: type, temperature: float = 0.2) -> dict:
    """Función interna extraída para la suite de pruebas y generación LLM."""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature
        )
    )
    return response.parsed.model_dump()


class AgentV1:
    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def extract_learning_metadata(self, query: str, document_id: str, niche: str = "", top_k: int = 5) -> dict:
        try:
            resultados = self.retriever.retrieve(query=query, top_k=top_k, metadata_filters={"document_id": document_id})
            
            if not resultados:
                return {"status": "no_results", "content": None, "error_message": "Sin resultados"}

            contexto_unificado = "\n\n".join([res.text for res in resultados])

            prompt_metadata = f"""
            Analiza el siguiente contexto enfocado estrictamente en el nicho temático: '{niche}'.
            Extrae OBLIGATORIAMENTE los metadatos pedagógicos adaptados a este nicho:
            1. "key_concepts": Lista exacta de 3 a 5 conceptos técnicos o ideas principales específicos de {niche}.
            2. "prerequisites": Lista de 1 a 3 conocimientos previos recomendados para este dominio.
            3. "estimated_time_minutes": Calcula el tiempo estimado de estudio (en minutos enteros).

            CONTEXTO RECUPERADO:
            {contexto_unificado}
            """

            parsed_content = _generate_and_parse(
                prompt=prompt_metadata, 
                schema=LearningMetadata, 
                temperature=0.1
            )

            return {
                "status": "success",
                "content": parsed_content,
                "error_message": None
            }

        except Exception as e:
            # Contrato pasivo estricto: siempre incluye error_message
            return {
                "status": "failed",
                "content": {
                    "key_concepts": ["Error al extraer conceptos"],
                    "prerequisites": ["N/A"],
                    "estimated_time_minutes": 0
                },
                "error_message": f"Error Gemini/Parse en metadatos: {str(e)}"
            }

    def answer(self, query: str, document_id: str, formato: str, perfil: str, nicho: str, nivel: str, learning_objective: str = None, top_k: int = 5) -> dict:
        chunks_usados = []
        
        try:
            resultados = self.retriever.retrieve(query=query, top_k=top_k, metadata_filters={"document_id": document_id})
            
            if not resultados:
                return {
                    "status": "no_results", 
                    "content": None, 
                    "sources_used": [],
                    "error_message": "No se encontró contexto suficiente en el documento."
                }

            contexto_unificado = "\n\n".join([res.text for res in resultados])
            
            for index, res in enumerate(resultados):
                chunks_usados.append({
                    "rank": index + 1,
                    "chunk_id": res.chunk_id,
                    "document_id": getattr(res, "document_id", document_id),
                    "score": getattr(res, "score", 0.0),
                    "text": res.text
                })

            instruccion_base = PROMPTS_BASE.get(formato.lower(), "Genera un resumen estructurado.")
            
            prompt_final = f"""
            INSTRUCCIÓN PRINCIPAL:
            {instruccion_base}
            
            REGLAS DE ADAPTACIÓN:
            - Perfil objetivo: {perfil}
            - Nicho temático: {nicho}
            - Nivel de detalle: {nivel}
            """
            if learning_objective:
                prompt_final += f"- Objetivo de aprendizaje: {learning_objective}\n"
                
            prompt_final += f"""
            Adapta el lenguaje y la complejidad estrictamente a este perfil.
            Genera identificadores únicos (IDs) cortos y alfanuméricos para cada elemento cuando aplique (preguntas, tarjetas, escenas).

            CONTEXTO RECUPERADO (Usa ÚNICA Y ESTRICTAMENTE esta información, no inventes datos externos):
            {contexto_unificado}
            """

            if formato.lower() == "quiz":
                esquema_salida = QuizContent
            elif formato.lower() == "flashcards":
                esquema_salida = FlashcardsContent
            elif formato.lower() == "tldr":
                esquema_salida = TLDRContent
            elif formato.lower() == "video_script":
                esquema_salida = VideoScriptContent
            else:
                raise ValueError(f"Formato '{formato}' no soportado para generación.")

            texto_generado = _generate_and_parse(
                prompt=prompt_final, 
                schema=esquema_salida, 
                temperature=0.2
            )

            return {
                "status": "success",
                "content": texto_generado,
                "sources_used": chunks_usados,
                "error_message": None
            }

        except Exception as e:
            return {
                "status": "failed",
                "content": None,
                "sources_used": chunks_usados,
                "error_message": f"Error crítico en el pipeline o generación con Gemini: {str(e)}"
            }

    def answer_for_evaluation(self, case_id: str, query: str, top_k: int = 5, metadata_filters: dict = None) -> dict:
        return self.retriever.retrieve_for_evaluation(case_id=case_id, query=query, top_k=top_k, metadata_filters=metadata_filters)