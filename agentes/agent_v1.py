import os
import time
import random
import logging
from pathlib import Path, PureWindowsPath
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import Field, ValidationError

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

# override=True: el .env del proyecto siempre gana sobre variables ya definidas
# (por ejemplo, la key falsa que conftest.py pone para que los módulos importen).
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL_NAME = os.environ["GEMINI_MODEL"]

# Opcionales (definibles en el .env)
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "").strip()
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

# Errores temporales: vale la pena reintentar. 400/401/403/404 fallan de inmediato.
RETRYABLE_CODES = {429, 500, 502, 503, 504}

client = genai.Client(api_key=API_KEY)

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


class _MetadataConDescripcion(LearningMetadata):
    """
    Extiende el contrato LearningMetadata SOLO para la llamada a Gemini: así la
    descripción del documento sale en la misma llamada (sin gastar una request extra).
    Antes de devolver el contenido, 'short_description' se separa y el resto queda
    idéntico al contrato LearningMetadata.
    """
    short_description: str = Field(
        ...,
        description="Descripción del documento en UNA sola oración (máximo 30 palabras)."
    )


def _titulo_desde_resultados(resultados) -> Optional[str]:
    """Nombre del archivo indexado (metadata 'source' que guarda /index). None si no está."""
    for res in resultados or []:
        meta = getattr(res, "metadata", None)
        if isinstance(meta, dict):
            for clave in ("source", "filename", "file_name", "title"):
                valor = meta.get(clave)
                if valor:
                    return PureWindowsPath(str(valor)).name
    return None


def _generate_with_retry(prompt: str, config):
    """
    Llama a Gemini con reintentos y espera creciente (1, 2, 4... s + jitter) ante errores
    temporales. Si se agotan con el modelo principal, prueba GEMINI_FALLBACK_MODEL (si
    está definido). Los errores no temporales se lanzan de inmediato.
    """
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
            except genai_errors.APIError as e:
                if getattr(e, "code", None) not in RETRYABLE_CODES:
                    raise
                ultimo_error = e
                if intento < MAX_RETRIES - 1:
                    espera = min(2 ** intento, 30) + random.uniform(0, 1)
                    logger.warning(
                        "Gemini %s con %s (intento %d/%d). Reintentando en %.1fs",
                        e.code, modelo, intento + 1, MAX_RETRIES, espera
                    )
                    time.sleep(espera)

        logger.warning("Se agotaron los reintentos con el modelo %s", modelo)

    raise ultimo_error


def _generate_and_parse(prompt: str, schema: type, temperature: float = 0.2) -> dict:
    """Función interna extraída para la suite de pruebas y generación LLM."""
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature
    )
    response = _generate_with_retry(prompt, config)

    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        return parsed.model_dump()

    # Respaldo: el SDK no pudo validar contra el schema; parseamos el texto crudo
    raw = (getattr(response, "text", None) or "").strip()
    if not raw:
        raise InvalidModelOutputError("Gemini devolvió una respuesta vacía (parsed=None y text vacío).")
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        return schema.model_validate_json(raw).model_dump()
    except ValidationError as e:
        raise InvalidModelOutputError(f"La respuesta de Gemini no cumple el schema: {e}") from e


class AgentV1:
    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def extract_learning_metadata(self, query: str, document_id: str, niche: str = "", top_k: int = 5) -> dict:
        """
        Devuelve status/content/error_message (contrato previo) más:
          - error: objeto de error estructurado (None si salió bien)
          - document_title: nombre del archivo indexado (disponible aunque Gemini falle)
          - document_description: descripción de una oración (solo si Gemini respondió)
        """
        titulo = None
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
            contexto_unificado = "\n\n".join([res.text for res in resultados])

            prompt_metadata = f"""
            Analiza el siguiente contexto enfocado estrictamente en el nicho temático: '{niche}'.
            Extrae OBLIGATORIAMENTE los metadatos pedagógicos adaptados a este nicho:
            1. "key_concepts": Lista exacta de 3 a 5 conceptos técnicos o ideas principales específicos de {niche}.
            2. "prerequisites": Lista de 1 a 3 conocimientos previos recomendados para este dominio.
            3. "estimated_time_minutes": Calcula el tiempo estimado de estudio (en minutos enteros).
            4. "short_description": UNA sola oración (máximo 30 palabras) que describa de qué trata el documento en general, sin limitarse al nicho.

            CONTEXTO RECUPERADO:
            {contexto_unificado}
            """

            parsed_content = _generate_and_parse(
                prompt=prompt_metadata,
                schema=_MetadataConDescripcion,
                temperature=0.1
            )

            descripcion = (parsed_content.pop("short_description", None) or "").strip() or None

            return {
                "status": "success",
                "content": parsed_content,
                "error_message": None,
                "error": None,
                "document_title": titulo,
                "document_description": descripcion,
            }

        except Exception as e:
            logger.exception("extract_learning_metadata falló")
            # Contrato pasivo estricto: siempre incluye error_message
            return {
                "status": "failed",
                "content": {
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
        """
        Genera UN formato a partir de un contexto ya recuperado (no vuelve a buscar en el RAG).
        Lo usa el Redactor del grafo: el Investigador recupera una vez y cada reescritura reutiliza
        ese contexto. NUNCA lanza: devuelve status/content/sources_used/error_message/error.
        """
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
                "error_message": f"Error crítico en el pipeline o generación con Gemini: {str(e)}",
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

            contexto_unificado = "\n\n".join([res.text for res in resultados])

            for index, res in enumerate(resultados):
                chunks_usados.append({
                    "rank": index + 1,
                    "chunk_id": res.chunk_id,
                    "document_id": getattr(res, "document_id", document_id),
                    "score": getattr(res, "score", 0.0),
                    "text": res.text
                })
        except Exception as e:
            logger.exception("answer falló en la recuperación (formato=%s)", formato)
            return {
                "status": "failed",
                "content": None,
                "sources_used": chunks_usados,
                "error_message": f"Error crítico en el pipeline o generación con Gemini: {str(e)}",
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
