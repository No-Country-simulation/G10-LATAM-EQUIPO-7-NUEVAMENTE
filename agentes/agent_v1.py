import os
import json
import uuid
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from .rag.retriever import RetrieverService

# Carga del archivo .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# DIAGNÓSTICO: Imprimirá en la terminal el valor exacto que detecta Python
print(">>> RUTA DEL .ENV BUSCADA:", env_path)
print(">>> VALOR DE LA API KEY:", repr(os.getenv("GEMINI_API_KEY")))

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("¡ALERTA: La API Key de Gemini es None o no se encontró!")


# Configuración explícita de la API Key de Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    # Intento secundario de respaldo si se ejecuta desde la raíz
    load_dotenv()
    if os.getenv("GEMINI_API_KEY"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        

PROMPTS_BASE = {
    "quiz": "Genera un cuestionario interactivo de opción múltiple (mínimo 3 preguntas) asegurando incluir la respuesta correcta, opciones de distracción coherentes y una breve justificación pedagógica.",
    "flashcards": "Genera 5 tarjetas de memorización (flashcards). Cada una debe tener un concepto clave en la cara frontal y su definición concisa en la cara trasera."
}

class AgentV1:
    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def answer(self, query: str, document_id: str, formato: str, perfil: str, nicho: str, nivel: str, learning_objective: str = None, top_k: int = 5) -> dict:
        # 1. Recuperación
        resultados = self.retriever.retrieve(query=query, top_k=top_k, document_id=document_id)
        
        if not resultados:
            return {
                "status": "no_results", 
                "content": None, 
                "sources_used": [],
                "error_message": "No se encontró contexto suficiente en el documento."
            }

        contexto_unificado = "\n\n".join([res.text for res in resultados])
        
        # 2. Construcción de evidencia completa
        chunks_usados = []
        for index, res in enumerate(resultados):
            chunks_usados.append({
                "rank": index + 1,
                "chunk_id": res.chunk_id,
                "document_id": getattr(res, "document_id", document_id),
                "score": getattr(res, "score", 0.0),
                "text": res.text
            })

        # 3. Ensamblar Prompt Dinámico
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

        CONTEXTO RECUPERADO (Usa ÚNICA Y ESTRICTAMENTE esta información, no inventes datos):
        {contexto_unificado}
        """

        # 4. LLM Gen (Llamada Real a Google AI Studio)
        try:
            texto_generado = self._llamar_llm(prompt_final, formato)
            error_msg = None
            status = "success"
        except Exception as e:
            texto_generado = None
            error_msg = f"Error en la generación con Gemini: {str(e)}"
            status = "error"

        # 5. Salida atómica
        return {
            "status": status,
            "content": texto_generado,
            "sources_used": chunks_usados,
            "error_message": error_msg
        }

    def _llamar_llm(self, prompt: str, formato: str) -> dict:
        """Llamada real a Gemini usando Structured Outputs y validación estricta Pydantic."""
        from .api import QuizContent, FlashcardsContent 

        # Usamos el modelo estándar con la librería google-generativeai
        model = genai.GenerativeModel('gemini-3.5-flash')
        
        # Mapeamos el formato al contrato Pydantic correcto
        if formato.lower() == "quiz":
            esquema_salida = QuizContent
        elif formato.lower() == "flashcards":
            esquema_salida = FlashcardsContent
        else:
            raise ValueError(f"Formato '{formato}' no soportado para generación.")

        # Generación exigiendo la estructura JSON estricta en Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=esquema_salida,
                temperature=0.2
            )
        )
        
        # Validación Pydantic Estricta sobre el resultado del LLM
        try:
            raw_json = json.loads(response.text)
            validated_model = esquema_salida.model_validate(raw_json)
            return validated_model.model_dump()
        except Exception as e:
            raise ValueError(f"Fallo en la validación Pydantic del JSON de la IA: {str(e)}")

    def answer_for_evaluation(self, case_id: str, query: str, top_k: int = 5) -> dict:
        return self.retriever.retrieve_for_evaluation(case_id=case_id, query=query, top_k=top_k)