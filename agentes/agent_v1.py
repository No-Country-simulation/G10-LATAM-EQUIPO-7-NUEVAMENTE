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

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL_NAME = os.environ["GEMINI_MODEL"]

client = genai.Client(api_key=API_KEY)

# ==========================================
# PROMPTS BASE (Limpios de metadatos)
# ==========================================
PROMPTS_BASE = {
    "quiz": "Genera un cuestionario interactivo de opción múltiple (mínimo 3 preguntas) asegurando incluir la respuesta correcta, opciones de distracción coherentes y una breve justificación pedagógica.",
    "flashcards": "Genera 5 tarjetas de memorización (flashcards). Cada una debe tener un concepto clave en la cara frontal y su definición concisa en la cara trasera."
}

class AgentV1:
    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def extract_learning_metadata(self, query: str, document_id: str, niche: str = "", top_k: int = 5) -> dict:
        """
        Llamada exclusiva (Llamada 1) adaptada al nicho para extraer metadatos pedagógicos a nivel raíz.
        """
        try:
            resultados = self.retriever.retrieve(query=query, top_k=top_k, metadata_filters={"document_id": document_id})
            
            if not resultados:
                return {"status": "no_results", "content": None}

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

            # Importación local para prevenir dependencias circulares
            from .api import LearningMetadata

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_metadata,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LearningMetadata,
                    temperature=0.1
                )
            )

            return {
                "status": "success",
                "content": response.parsed.model_dump()
            }

        except Exception as e:
            # Fallback seguro para no romper la API si esto falla
            return {
                "status": "failed",
                "content": {
                    "key_concepts": ["Error al extraer conceptos"],
                    "prerequisites": ["N/A"],
                    "estimated_time_minutes": 0
                }
            }

    def answer(self, query: str, document_id: str, formato: str, perfil: str, nicho: str, nivel: str, learning_objective: str = None, top_k: int = 5) -> dict:
        chunks_usados = []
        
        try:
            # 1. Recuperación Híbrida en ChromaDB
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

            # 3. Ensamblar Prompt Dinámico Adaptativo (Limpio)
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
            Genera identificadores únicos (IDs) cortos y alfanuméricos para cada pregunta o tarjeta.

            CONTEXTO RECUPERADO (Usa ÚNICA Y ESTRICTAMENTE esta información, no inventes datos externos):
            {contexto_unificado}
            """

            # 4. Importación local 
            # NOTA: Si haces merge con el PR de Oscar, asegúrate de mantener sus importaciones de TldrContent aquí.
            from .api import QuizContent, FlashcardsContent 

            # Mapeamos el formato al contrato Pydantic correcto
            if formato.lower() == "quiz":
                esquema_salida = QuizContent
            elif formato.lower() == "flashcards":
                esquema_salida = FlashcardsContent
            else:
                raise ValueError(f"Formato '{formato}' no soportado para generación.")

            # 5. Llamada al LLM
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=esquema_salida,
                    temperature=0.2
                )
            )
            
            parsed_content = response.parsed
            texto_generado = parsed_content.model_dump()

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