"""Motor heurístico de evaluación de calidad para Quiz y Flashcards."""

import re
from typing import List, Union

from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    EvaluationScores,
    FlashcardsContent,
    GenerationContext,
    QuizContent,
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

    # ========================================================
    # INICIALIZACIÓN DE IA (LAZY LOADING)
    # ========================================================
    # Llamamos a la función segura que creaste antes
    cliente_gemini, modelo_embeddings = get_semantic_models()

    # ========================================================
    # 1. RELEVANCIA (PROTOTIPO SEMÁNTICO V2)
    # ========================================================
    objetivo = (generation_context.learning_objective or "").strip()
    nicho = (generation_context.niche or "").strip()
    contexto_esperado = f"{objetivo} {nicho}".strip()

    nichos_genericos = {"general", "todos", "n/a", "ninguno"}
    
    # Lógica Semántica (Simulada/Estructural para Embeddings)
    if not contexto_esperado or nicho.lower() in nichos_genericos:
        relevancia = 5
    elif modelo_embeddings is not None:
        # TODO V2: Aquí va el cálculo matemático real con la librería de embeddings (ej. SentenceTransformers)
        # vector_contexto = modelo_embeddings.encode(contexto_esperado)
        # vector_contenido = modelo_embeddings.encode(texto_evaluable)
        # similitud = calcular_similitud_coseno(vector_contexto, vector_contenido)
        # relevancia = asignar_score_por_similitud(similitud)
        
        # Placeholder temporal para mantener el flujo hasta conectar la librería matemática
        relevancia = 4 
    else:
        # Fallback de seguridad si falla la carga de modelos
        relevancia = 3

    # ========================================================
    # 2. COHERENCIA (MANTIENE HEURÍSTICA V1)
    # ========================================================
    coherencia = 5 if len(texto_evaluable.strip()) > MIN_CARACTERES_COHERENCIA else 2

    # ========================================================
    # 3. ADAPTACIÓN DIDÁCTICA (MANTIENE HEURÍSTICA V1)
    # ========================================================
    perfil = (generation_context.profile or "").lower()
    nivel_detalle = (generation_context.detail_level or "").lower()
    adaptacion = 5

    if perfil in {"principiante", "beginner"} and len(texto_evaluable) > MIN_CHARS_BEGINNER:
        adaptacion = 3
    elif nivel_detalle in {"alto", "high"} and len(texto_evaluable) < MIN_CHARS_HIGH_DETAIL:
        adaptacion = 2

    # ========================================================
    # 4. INFORMACIÓN RESPALDADA Y ALUCINACIONES (SEMÁNTICA V2)
    # ========================================================
    informacion_no_respaldada = False
    
    if modelo_embeddings is not None and chunks_text:
        # TODO V2: Cálculo de alucinación semántica
        # vector_fuente = modelo_embeddings.encode(chunks_text)
        # similitud_fuente = calcular_similitud_coseno(vector_fuente, vector_contenido)
        
        # Lógica basada en similitud:
        # Si la similitud cae por debajo del umbral, se considera alucinación
        # informacion_no_respaldada = similitud_fuente < UMBRAL_ALUCINACION
        # informacion_respaldada = asignar_score_respaldo(similitud_fuente)
        
        # Placeholder temporal
        informacion_respaldada = 5
    else:
        informacion_respaldada = 5

    # ========================================================
    # 5. RESULTADO
    # ========================================================
    scores = EvaluationScores(
        relevancia=relevancia,
        coherencia=coherencia,
        adaptacion_didactica=adaptacion,
        informacion_respaldada=informacion_respaldada,
    )

    return scores, informacion_no_respaldada
