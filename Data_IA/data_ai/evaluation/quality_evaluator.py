"""Motor heurístico de evaluación de calidad para Quiz y Flashcards."""

import re
from typing import List, Union

from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    EvaluationScores,
    FlashcardsContent,
    GenerationContext,
    QuizContent,
    TLDRContent,          # <-- Agregagado
    VideoScriptContent,   # <-- Agregagado 
)

from data_ai.evaluation.config import (
    UMBRAL_RELEVANCIA_ALTA,
    UMBRAL_RELEVANCIA_MEDIA,
    MIN_CARACTERES_COHERENCIA,
    RATIO_ALUCINACION_RECHAZO,
    RATIO_ALUCINACION_EXCELENTE,
    RATIO_ALUCINACION_BUENO,
)

import logging

# ============================================================
# LAZY LOADING DE MODELOS SEMÁNTICOS (V2)
# ============================================================
_gemini_client = None
_embedding_model = None

def get_semantic_models():
    """
    Inicialización perezosa de los modelos de IA.
    Asegura que solo se descarguen/conecten cuando realmente 
    se necesiten, evitando que el servicio 8002 colapse al iniciar.
    """
    global _gemini_client, _embedding_model
    
    if _gemini_client is None or _embedding_model is None:
        try:
            logging.info("Inicializando modelos semánticos por primera vez...")
            
            # NOTA: Aquí colocaremos las importaciones de IA reales 
            # cuando armemos la lógica V2 (ej. SentenceTransformer y genai)
            
            # _embedding_model = CargaDeModeloLocal()
            # _gemini_client = CargaDeClienteGoogle()
            
            logging.info("Modelos de IA inicializados correctamente.")
        except Exception as e:
            logging.error(f"Error de red o configuración al inicializar IA: {e}")
            # Retornamos None de forma controlada para evitar que la API muera
            return None, None
            
    return _gemini_client, _embedding_model

from data_ai.evaluation.config import MIN_CHARS_BEGINNER, MIN_CHARS_HIGH_DETAIL

GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
    TLDRContent,          # <-- Agregado
    VideoScriptContent,   # <-- Agregado
]


STOPWORDS = {
    "para",
    "desde",
    "sobre",
    "entre",
    "como",
    "esta",
    "este",
    "estos",
    "estas",
    "crear",
    "utiliza",
    "utilizado",
    "selecciona",
    "respuesta",
    "correcta",
    "intenta",
    "responder",
    "antes",
    "revisar",
    "conceptos",
    "basicos",
    "básicos",
    "comprender",
}


def _normalizar_palabras(texto: str) -> list[str]:
    """Convierte texto a tokens normalizados."""
    return re.findall(
        r"\b\w+\b",
        texto.lower(),
        flags=re.UNICODE,
    )


def _palabras_significativas(texto: str) -> list[str]:
    """Obtiene términos útiles para comparación semántica básica."""
    return [
        palabra
        for palabra in _normalizar_palabras(texto)
        if len(palabra) > 3
        and palabra not in STOPWORDS
    ]


def _extraer_texto_evaluable(
    generated_content: GeneratedContent,
) -> str:
    """
    Extrae únicamente contenido que representa conocimiento evaluable.

    En Quiz se excluyen distractores, título e instrucciones.
    En Flashcards se evalúan frente y reverso.
    """

    if isinstance(generated_content, QuizContent):
        partes = []

        for question in generated_content.questions:
            partes.extend(
                [
                    question.question,
                    question.correct_answer,
                    question.explanation,
                ]
            )

        return " ".join(partes)

    if isinstance(generated_content, FlashcardsContent):
        partes = []

        for card in generated_content.cards:
            partes.extend(
                [
                    card.front,
                    card.back,
                ]
            )

        return " ".join(partes)
    if isinstance(generated_content, TLDRContent):
        partes = [generated_content.title, generated_content.summary]
        partes.extend(generated_content.key_points)
        return " ".join(partes)

    if isinstance(generated_content, VideoScriptContent):
        partes = [generated_content.title]
        for scene in generated_content.scenes:
            partes.extend([scene.visual_description, scene.narration])
        return " ".join(partes)

    return ""


def evaluate(
    generated_content: GeneratedContent,
    chunks_used: List[ChunkUsed],
    generation_context: GenerationContext,
) -> tuple[EvaluationScores, bool]:
    """
    Calcula scores de calidad combinando heurística (V1) y semántica (V2).
    """
    texto_evaluable = _extraer_texto_evaluable(generated_content)
    chunks_text = " ".join(chunk.text for chunk in chunks_used)

    # 1. Carga perezosa de IA
    cliente_gemini, modelo_embeddings = get_semantic_models()

    # 2. Relevancia (Semántica con Fallback Heurístico)
    objetivo = (generation_context.learning_objective or "").strip()
    nicho = (generation_context.niche or "").strip()
    contexto_esperado = f"{objetivo} {nicho}".strip()
    nichos_genericos = {"general", "todos", "n/a", "ninguno"}

    if not contexto_esperado or nicho.lower() in nichos_genericos:
        relevancia = 5
    elif modelo_embeddings is not None:
        relevancia = 4  # Placeholder semántico V2
    else:
        # Fallback Heurístico V1 funcional
        terminos_contexto = set(_palabras_significativas(contexto_esperado))
        terminos_contenido = set(_palabras_significativas(texto_evaluable))
        if not terminos_contexto:
            ratio_relevancia = 1.0
        else:
            coincidencias = terminos_contexto & terminos_contenido
            ratio_relevancia = len(coincidencias) / len(terminos_contexto)

        if ratio_relevancia >= UMBRAL_RELEVANCIA_ALTA:
            relevancia = 5
        elif ratio_relevancia >= UMBRAL_RELEVANCIA_MEDIA:
            relevancia = 4
        else:
            relevancia = 3

    # 3. Coherencia
    coherencia = 5 if len(texto_evaluable.strip()) > MIN_CARACTERES_COHERENCIA else 2

    # 4. Adaptación didáctica
    perfil = (generation_context.profile or "").lower()
    nivel_detalle = (generation_context.detail_level or "").lower()
    adaptacion = 5

    if perfil in {"principiante", "beginner"} and len(texto_evaluable) > MIN_CHARS_BEGINNER:
        adaptacion = 3
    elif nivel_detalle in {"alto", "high"} and len(texto_evaluable) < MIN_CHARS_HIGH_DETAIL:
        adaptacion = 2

    # 5. Información respaldada y alucinaciones (Semántica con Fallback Heurístico)
    if modelo_embeddings is not None and chunks_text:
        informacion_no_respaldada = False
        informacion_respaldada = 5
    else:
        # Fallback Heurístico V1 funcional
        terminos_fuente = set(_palabras_significativas(chunks_text))
        terminos_generados = _palabras_significativas(texto_evaluable)

        if not terminos_generados:
            informacion_no_respaldada = False
            informacion_respaldada = 5
        else:
            no_respaldadas = [w for w in terminos_generados if w not in terminos_fuente]
            ratio_alucinacion = len(no_respaldadas) / len(terminos_generados)

            if ratio_alucinacion >= RATIO_ALUCINACION_RECHAZO:
                informacion_no_respaldada = True
                informacion_respaldada = 5
            elif ratio_alucinacion <= RATIO_ALUCINACION_EXCELENTE:
                informacion_no_respaldada = False
                informacion_respaldada = 5
            elif ratio_alucinacion <= RATIO_ALUCINACION_BUENO:
                informacion_no_respaldada = False
                informacion_respaldada = 4
            else:
                informacion_no_respaldada = False
                informacion_respaldada = 3

    scores = EvaluationScores(
        relevancia=relevancia,
        coherencia=coherencia,
        adaptacion_didactica=adaptacion,
        informacion_respaldada=informacion_respaldada,
    )

    return scores, informacion_no_respaldada
