import os
import time
import random
import logging
import json
from pathlib import Path, PureWindowsPath
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import ValidationError

from .rag.retriever import RetrieverService
from .errors import InvalidModelOutputError, build_error, classify_exception
from .generated_schemas import (
    LearningMetadata,
    QuizContent,
    FlashcardsContent,
    TLDRContent,
    VideoScriptContent,
)

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "").strip()
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

RETRYABLE_CODES = {429, 500, 502, 503, 504}

client = genai.Client(api_key=API_KEY) if API_KEY and not API_KEY.startswith("fake") else None

PROMPTS_BASE = {
    "quiz": "Genera un cuestionario interactivo de opción múltiple (mínimo 3 preguntas) asegurando incluir la respuesta correcta, opciones de distracción coherentes y una breve justificación pedagógica.",
    "flashcards": "Genera 5 tarjetas de memorización (flashcards). Cada una debe tener un concepto clave en la cara frontal y su definición concisa en la cara trasera.",
    "tldr": "Genera un resumen ejecutivo conciso basado exclusivamente en el contexto recuperado, sin inventar información externa. Identifica entre 3 y 7 puntos clave esenciales cuando el contexto lo permita y cierra con la conclusión o takeaway principal. Adapta el lenguaje a profile, niche y detail_level.",
    "video_script": "Genera un guion educativo de clase o video dividido en una secuencia ordenada de escenas. Usa únicamente el contexto recuperado sin inventar datos técnicos ausentes, adaptando el lenguaje a profile, niche y detail_level, y respetando learning_objective si existe. Cada escena debe incluir un identificador corto (scene_id), título, texto de narración pedagógica que pronunciaría el docente o narrador, descripción visual de lo que debería verse en pantalla y duration_seconds. La duración estimada total (estimated_duration_minutes) debe ser razonablemente coherente con la suma de las duraciones de las escenas."
}

ESQUEMAS_POR_FORMATO = {
    "quiz": QuizContent,
    "flashcards": FlashcardsContent,
    "tldr": TLDRContent,
    "video_script": VideoScriptContent,
}


def _titulo_desde_resultados(resultados) -> Optional[str]:
    for res in resultados or []:
        meta = res.get("metadata", {}) if isinstance(res, dict) else getattr(res, "metadata", {})
        if isinstance(meta, dict):
            for clave in ("source", "filename", "file_name", "title"):
                valor = meta.get(clave)
                if valor:
                    return PureWindowsPath(str(valor)).name
    return None


def _generate_with_retry(prompt: str, config):
    if not client:
        raise RuntimeError("El cliente GenAI no está configurado correctamente (verifica la API KEY).")

    modelos = [MODEL_NAME]
    if FALLBACK_MODEL and FALLBACK_MODEL != MODEL_NAME:
        modelos.append(FALLBACK_MODEL)

    ultimo_error = None

    for modelo in modelos:
        for intento in range(MAX_RETRIES):
            try:
                return client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=config
                )
            except Exception as e:
                ultimo_error = e
                is_retryable = False
                
                if isinstance(e, genai_errors.APIError):
                    code = getattr(e, "code", 500)
                    if code in RETRYABLE_CODES:
                        is_retryable = True
                elif any(str(code) in str(e) for code in RETRYABLE_CODES):
                    is_retryable = True
                    
                if is_retryable and intento < MAX_RETRIES - 1:
                    espera = min(2 ** intento, 30) + random.uniform(0, 1)
                    logger.warning(
                        "Error LLM reintentable (intento %d/%d). Reintentando en %.1fs. Error: %s",
                        intento + 1, MAX_RETRIES, espera, str(e)
                    )
                    time.sleep(espera)
                else:
                    break

        logger.warning("Se agotaron los reintentos o el error es terminal con el modelo %s", modelo)

    raise ultimo_error


def _generate_and_parse(prompt: str, schema: type, temperature: float = 0.2) -> dict:
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=temperature
    )
    
    try:
        esquema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        prompt_final = f"{prompt}\n\nIMPORTANTE: Tu respuesta DEBE ser un JSON válido que cumpla estrictamente con este esquema:\n{esquema_str}"
    except Exception:
        prompt_final = prompt

    response = _generate_with_retry(prompt_final, config)

    raw = ""
    if hasattr(response, "text") and response.text:
        raw = response.text.strip()

    if not raw:
        raise InvalidModelOutputError("Gemini devolvió una respuesta completamente vacía.")

    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
            
    try:
        datos = json.loads(raw)
        return schema(**datos).model_dump()
    except Exception as e:
        raise InvalidModelOutputError(f"La respuesta de Gemini no cumple el contrato JSON esperado: {e}") from e


class AgentV1:
    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def extract_learning_metadata(self, query: str, document_id: str, niche: str = "", top_k: int = 5) -> dict:
        try:
            resultados = self.retriever.retrieve(query=query, top_k=top_k, metadata_filters={"document_id": document_id})

            if not resultados:
                return {
                    "status": "no_results",
                    "content": None,
                    "error_message": "Sin resultados",
                    "error": build_error("NO_CONTEXT", "No hay contenido indexado para el document_id solicitado."),
                    "document_title": None,
                    "document_description": None,
                }

            titulo = _titulo_desde_resultados(resultados)
            textos = [res.get("text", "") if isinstance(res, dict) else getattr(res, "text", "") for res in resultados]
            contexto_unificado = "\n\n".join(textos)
            
        except Exception as e:
            logger.exception("extract_learning_metadata falló en la recuperación")
            return self._metadatos_fallidos(e, None)

        return self.extract_metadata_from_context(contexto_unificado, niche, titulo)

    def extract_metadata_from_context(self, contexto: str, niche: str = "", titulo: Optional[str] = None) -> dict:
        if not (contexto or "").strip():
            return {
                "status": "no_results",
                "content": None,
                "error_message": "Sin resultados",
                "error": build_error("NO_CONTEXT", "No hay contenido indexado para el document_id solicitado."),
                "document_title": titulo,
                "document_description": None,
            }

        try:
            prompt_metadata = f"""
            Analiza el siguiente contexto enfocado estrictamente en el nicho temático: '{niche}'.
            Extrae OBLIGATORIAMENTE los metadatos pedagógicos adaptados a este nicho utilizando estrictamente el esquema LearningMetadata:
            - document_title: Genera un título descriptivo y profesional que identifique claramente el tema principal (con ortografía, tildes y uso natural de mayúsculas). No uses el nombre del archivo.
            - key_concepts: Lista exacta de 3 a 5 conceptos técnicos o ideas principales específicos de {niche}.
            - prerequisites: Lista de 1 a 3 conocimientos previos recomendados.
            - estimated_time_minutes: Tiempo estimado de estudio en minutos enteros.
            - short_description: Una sola oración (máximo 30 palabras) que describa de qué trata el documento en general.

            CONTEXTO RECUPERADO:
            {contexto}
            """

            # Única fuente de verdad reutilizando LearningMetadata
            parsed_content = _generate_and_parse(
                prompt=prompt_metadata,
                schema=LearningMetadata,
                temperature=0.1
            )

            # Fallback robusto para asegurar que document_description nunca sea None
            descripcion = (parsed_content.pop("short_description", None) or "").strip()
            if not descripcion and parsed_content.get("key_concepts"):
                conceptos = parsed_content["key_concepts"][:3]
                descripcion = f"Documento enfocado en: {', '.join(conceptos)}."
            if not descripcion:
                descripcion = "Documento analizado y estructurado pedagógicamente."

            titulo_generado = parsed_content.get("document_title") or titulo or "Título no generado"
            parsed_content["document_title"] = titulo_generado

            return {
                "status": "success",
                "content": parsed_content,
                "error_message": None,
                "error": None,
                "document_title": titulo_generado,
                "document_description": descripcion,
            }

        except Exception as e:
            logger.exception("extract_metadata_from_context falló")
            return self._metadatos_fallidos(e, titulo)

    @staticmethod
    def _metadatos_fallidos(e: Exception, titulo: Optional[str]) -> dict:
        return {
            "status": "failed",
            "content": {
                "document_title": titulo or "Título no generado",
                "key_concepts": ["Error al extraer conceptos"],
                "prerequisites": ["No se pudieron determinar"],
                "estimated_time_minutes": 0
            },
            "error_message": f"Error Gemini/Parse en metadatos: {str(e)}",
            "error": classify_exception(e),
            "document_title": titulo,
            "document_description": None,
        }

    def _armar_prompt(self, formato: str, perfil: str, nicho: str, nivel: str,
                      learning_objective: Optional[str], contexto: str, extra_instructions: str = "") -> str:
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

        if extra_instructions:
            prompt_final += f"""
            INSTRUCCIONES DE REVISIÓN (prioritarias):
            {extra_instructions}
            """

        prompt_final += f"""
            Adapta el lenguaje y la complejidad estrictamente a este perfil.
            Genera identificadores únicos (IDs) cortos y alfanuméricos para cada elemento cuando aplique (preguntas, tarjetas, escenas).

            CONTEXTO RECUPERADO (Usa ÚNICA Y ESTRICTAMENTE esta información, no inventes datos externos):
            {contexto}
            """
        return prompt_final

    def generate_from_context(self, contexto: str, sources_used: list, formato: str, perfil: str,
                              nicho: str, nivel: str, learning_objective: str = None,
                              extra_instructions: str = "") -> dict:
        esquema_salida = ESQUEMAS_POR_FORMATO.get((formato or "").lower())
        if esquema_salida is None:
            mensaje = f"Formato '{formato}' no soportado para generación."
            return {
                "status": "failed",
                "content": None,
                "sources_used": [],
                "error_message": mensaje,
                "error": build_error("UNSUPPORTED_FORMAT", mensaje),
            }

        if not (contexto or "").strip():
            mensaje = "No se encontró contexto suficiente en el documento."
            return {
                "status": "no_results",
                "content": None,
                "sources_used": [],
                "error_message": mensaje,
                "error": build_error("NO_CONTEXT", mensaje),
            }

        fuentes = list(sources_used or [])
        try:
            prompt_final = self._armar_prompt(
                formato, perfil, nicho, nivel, learning_objective, contexto, extra_instructions
            )
            texto_generado = _generate_and_parse(
                prompt=prompt_final,
                schema=esquema_salida,
                temperature=0.2
            )
            return {
                "status": "success",
                "content": texto_generado,
                "sources_used": fuentes,
                "error_message": None,
                "error": None,
            }
        except Exception as e:
            logger.exception("generate_from_context falló (formato=%s)", formato)
            return {
                "status": "failed",
                "content": None,
                "sources_used": fuentes,
                "error_message": f"Error crítico en la generación con Gemini: {str(e)}",
                "error": classify_exception(e),
            }

    def answer(self, query: str, document_id: str, formato: str, perfil: str, nicho: str, nivel: str,
               learning_objective: str = None, top_k: int = 5, extra_instructions: str = "") -> dict:
        if ESQUEMAS_POR_FORMATO.get(formato.lower()) is None:
            mensaje = f"Formato '{formato}' no soportado para generación."
            return {
                "status": "failed",
                "content": None,
                "sources_used": [],
                "error_message": mensaje,
                "error": build_error("UNSUPPORTED_FORMAT", mensaje),
            }

        chunks_usados = []
        try:
            resultados = self.retriever.retrieve(query=query, top_k=top_k, metadata_filters={"document_id": document_id})

            if not resultados:
                return {
                    "status": "no_results",
                    "content": None,
                    "sources_used": [],
                    "error_message": "No se encontró contexto suficiente en el documento.",
                    "error": build_error("NO_CONTEXT", "No se encontró contexto suficiente en el documento."),
                }

            textos = []
            for index, res in enumerate(resultados):
                if isinstance(res, dict):
                    textos.append(res.get("text", ""))
                    chunks_usados.append({
                        "rank": index + 1,
                        "chunk_id": res.get("chunk_id", str(index)),
                        "document_id": res.get("document_id", document_id),
                        "score": res.get("score", 0.0),
                        "text": res.get("text", "")
                    })
                else:
                    textos.append(getattr(res, "text", ""))
                    chunks_usados.append({
                        "rank": index + 1,
                        "chunk_id": getattr(res, "chunk_id", str(index)),
                        "document_id": getattr(res, "document_id", document_id),
                        "score": getattr(res, "score", 0.0),
                        "text": getattr(res, "text", "")
                    })
                    
            contexto_unificado = "\n\n".join(textos)

        except Exception as e:
            logger.exception("answer falló en la recuperación (formato=%s)", formato)
            return {
                "status": "failed",
                "content": None,
                "sources_used": chunks_usados,
                "error_message": f"Error crítico en la recuperación de RAG: {str(e)}",
                "error": classify_exception(e),
            }

        return self.generate_from_context(
            contexto=contexto_unificado,
            sources_used=chunks_usados,
            formato=formato,
            perfil=perfil,
            nicho=nicho,
            nivel=nivel,
            learning_objective=learning_objective,
            extra_instructions=extra_instructions,
        )

    def answer_for_evaluation(self, case_id: str, query: str, top_k: int = 5, metadata_filters: dict = None) -> dict:
        return self.retriever.retrieve_for_evaluation(case_id=case_id, query=query, top_k=top_k, metadata_filters=metadata_filters)