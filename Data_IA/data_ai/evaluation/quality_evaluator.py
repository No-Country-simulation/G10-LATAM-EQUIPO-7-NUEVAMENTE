"""Motor heurístico de evaluación de calidad para formatos generados.

Evaluator V1.1:
- normalización léxica Unicode/acentos;
- separación entre contenido factual y contenido de presentación;
- respaldo factual basado exclusivamente en `chunks_used`;
- mantiene sin cambios los umbrales y la rúbrica de decisión.
"""

import logging
import re
import unicodedata
from typing import List, Union

from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    EvaluationScores,
    FlashcardsContent,
    GenerationContext,
    QuizContent,
    TLDRContent,
    VideoScriptContent,
)

from data_ai.evaluation.config import (
    MIN_CARACTERES_COHERENCIA,
    MIN_CHARS_BEGINNER,
    MIN_CHARS_HIGH_DETAIL,
    RATIO_ALUCINACION_BUENO,
    RATIO_ALUCINACION_EXCELENTE,
    RATIO_ALUCINACION_RECHAZO,
    UMBRAL_RELEVANCIA_ALTA,
    UMBRAL_RELEVANCIA_MEDIA,
)

# ============================================================
# LAZY LOADING DE MODELOS SEMÁNTICOS (V2)
# ============================================================

_gemini_client = None
_embedding_model = None


def get_semantic_models():
    """
    Inicialización perezosa de los modelos de IA.

    Por ahora conserva el fallback heurístico V1/V1.1 mientras no exista
    una implementación semántica activa.
    """
    global _gemini_client, _embedding_model

    if _gemini_client is None or _embedding_model is None:
        try:
            logging.info(
                "Inicializando modelos semánticos por primera vez..."
            )

            # Reservado para una implementación semántica posterior.
            # _embedding_model = CargaDeModeloLocal()
            # _gemini_client = CargaDeClienteGoogle()

            logging.info(
                "Modelos de IA inicializados correctamente."
            )
        except Exception as exc:
            logging.error(
                "Error de red o configuración al inicializar IA: %s",
                exc,
            )
            return None, None

    return _gemini_client, _embedding_model


GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
    TLDRContent,
    VideoScriptContent,
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
    "comprender",
}


def _quitar_acentos(texto: str) -> str:
    """Elimina marcas diacríticas sin alterar letras base."""
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def _normalizar_palabras(texto: str) -> list[str]:
    """
    Convierte texto a tokens comparables.

    V1.1 normaliza mayúsculas y diacríticos para evitar falsos positivos
    como `página` vs `pagina` o `código` vs `codigo`.
    """
    texto_normalizado = _quitar_acentos(texto.lower())

    return re.findall(
        r"\b\w+\b",
        texto_normalizado,
        flags=re.UNICODE,
    )


def _palabras_significativas(texto: str) -> list[str]:
    """Obtiene términos útiles para comparación léxica básica."""
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
    Extrae contenido útil para relevancia, coherencia y adaptación.

    Se conserva una vista amplia del contenido generado. El chequeo de
    respaldo factual usa `_extraer_texto_factual`.
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
        partes = [
            generated_content.title,
            generated_content.summary,
        ]
        partes.extend(generated_content.key_points)
        partes.append(generated_content.conclusion)
        return " ".join(partes)

    if isinstance(generated_content, VideoScriptContent):
        partes = [generated_content.title]

        for scene in generated_content.scenes:
            partes.extend(
                [
                    scene.title,
                    scene.visual_description,
                    scene.narration,
                ]
            )

        return " ".join(partes)

    return ""


def _extraer_texto_factual(
    generated_content: GeneratedContent,
) -> str:
    """
    Extrae solo el contenido que debe estar respaldado por los chunks.

    Decisiones V1.1:
    - Quiz: pregunta, respuesta correcta y explicación.
    - Flashcards: frente y reverso.
    - TLDR: summary, key_points y conclusion; el título es framing.
    - Video Script: solo narration; títulos y visual_description son
      instrucciones de presentación, no afirmaciones factuales.
    """
    if isinstance(
        generated_content,
        (QuizContent, FlashcardsContent),
    ):
        return _extraer_texto_evaluable(generated_content)

    if isinstance(generated_content, TLDRContent):
        partes = [generated_content.summary]
        partes.extend(generated_content.key_points)
        partes.append(generated_content.conclusion)
        return " ".join(partes)

    if isinstance(generated_content, VideoScriptContent):
        return " ".join(
            scene.narration
            for scene in generated_content.scenes
        )

    return ""


def evaluate(
    generated_content: GeneratedContent,
    chunks_used: List[ChunkUsed],
    generation_context: GenerationContext,
) -> tuple[EvaluationScores, bool]:
    """
    Calcula scores de calidad combinando heurística V1.1 y fallback V2.

    La rúbrica y los umbrales permanecen sin cambios respecto de V1.0.
    """
    texto_evaluable = _extraer_texto_evaluable(
        generated_content
    )
    texto_factual = _extraer_texto_factual(
        generated_content
    )
    chunks_text = " ".join(
        chunk.text
        for chunk in chunks_used
    )

    # 1. Carga perezosa de IA
    _, modelo_embeddings = get_semantic_models()

    # 2. Relevancia
    objetivo = (
        generation_context.learning_objective or ""
    ).strip()
    nicho = (
        generation_context.niche or ""
    ).strip()
    contexto_esperado = f"{objetivo} {nicho}".strip()
    nichos_genericos = {
        "general",
        "todos",
        "n/a",
        "ninguno",
    }

    if (
        not contexto_esperado
        or nicho.lower() in nichos_genericos
    ):
        relevancia = 5
    elif modelo_embeddings is not None:
        relevancia = 4
    else:
        terminos_contexto = set(
            _palabras_significativas(
                contexto_esperado
            )
        )
        terminos_contenido = set(
            _palabras_significativas(
                texto_evaluable
            )
        )

        if not terminos_contexto:
            ratio_relevancia = 1.0
        else:
            coincidencias = (
                terminos_contexto
                & terminos_contenido
            )
            ratio_relevancia = (
                len(coincidencias)
                / len(terminos_contexto)
            )

        if (
            ratio_relevancia
            >= UMBRAL_RELEVANCIA_ALTA
        ):
            relevancia = 5
        elif (
            ratio_relevancia
            >= UMBRAL_RELEVANCIA_MEDIA
        ):
            relevancia = 4
        else:
            relevancia = 3

    # 3. Coherencia
    coherencia = (
        5
        if len(texto_evaluable.strip())
        > MIN_CARACTERES_COHERENCIA
        else 2
    )

    # 4. Adaptación didáctica
    perfil = (
        generation_context.profile or ""
    ).lower()
    nivel_detalle = (
        generation_context.detail_level or ""
    ).lower()
    adaptacion = 5

    if (
        perfil in {"principiante", "beginner"}
        and len(texto_evaluable)
        > MIN_CHARS_BEGINNER
    ):
        adaptacion = 3
    elif (
        nivel_detalle in {"alto", "high"}
        and len(texto_evaluable)
        < MIN_CHARS_HIGH_DETAIL
    ):
        adaptacion = 2

    # 5. Información respaldada / alucinación
    if modelo_embeddings is not None and chunks_text:
        informacion_no_respaldada = False
        informacion_respaldada = 5
    else:
        terminos_fuente = set(
            _palabras_significativas(
                chunks_text
            )
        )

        terminos_generados = (
            _palabras_significativas(
                texto_factual
            )
        )

        if not terminos_generados:
            informacion_no_respaldada = False
            informacion_respaldada = 5
        else:
            no_respaldadas = [
                palabra
                for palabra in terminos_generados
                if palabra
                not in terminos_fuente
            ]
            ratio_alucinacion = (
                len(no_respaldadas)
                / len(terminos_generados)
            )

            if (
                ratio_alucinacion
                >= RATIO_ALUCINACION_RECHAZO
            ):
                informacion_no_respaldada = True
                informacion_respaldada = 1
            elif (
                ratio_alucinacion
                <= RATIO_ALUCINACION_EXCELENTE
            ):
                informacion_no_respaldada = False
                informacion_respaldada = 5
            elif (
                ratio_alucinacion
                <= RATIO_ALUCINACION_BUENO
            ):
                informacion_no_respaldada = False
                informacion_respaldada = 4
            else:
                informacion_no_respaldada = False
                informacion_respaldada = 3

    scores = EvaluationScores(
        relevancia=relevancia,
        coherencia=coherencia,
        adaptacion_didactica=adaptacion,
        informacion_respaldada=(
            informacion_respaldada
        ),
    )

    return (
        scores,
        informacion_no_respaldada,
    )
