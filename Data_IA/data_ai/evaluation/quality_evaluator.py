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
    Calcula scores heurísticos de calidad y detecta
    información potencialmente no respaldada.
    """

    texto_evaluable = _extraer_texto_evaluable(
        generated_content
    )

    chunks_text = " ".join(
        chunk.text
        for chunk in chunks_used
    )

    # ========================================================
    # 1. RELEVANCIA
    # ========================================================

    objetivo = (
        generation_context.learning_objective or ""
    )

    nicho = generation_context.niche or ""

    terminos_contexto = set(
        _palabras_significativas(
            f"{objetivo} {nicho}"
        )
    )

    terminos_contenido = set(
        _palabras_significativas(
            texto_evaluable
        )
    )

    if terminos_contexto:
        coincidencias = (
            terminos_contexto
            & terminos_contenido
        )

        ratio_relevancia = (
            len(coincidencias)
            / len(terminos_contexto)
        )
    else:
        ratio_relevancia = 1.0

    if ratio_relevancia >= 0.50:
        relevancia = 5
    elif ratio_relevancia >= 0.25:
        relevancia = 4
    else:
        relevancia = 3

    # ========================================================
    # 2. COHERENCIA
    # ========================================================

    coherencia = (
        5
        if len(texto_evaluable.strip()) > 50
        else 2
    )

    # ========================================================
    # 3. ADAPTACIÓN DIDÁCTICA
    # ========================================================

    perfil = (
        generation_context.profile or ""
    ).lower()

    nivel_detalle = (
        generation_context.detail_level or ""
    ).lower()

    adaptacion = 5

    if (
        perfil in {"principiante", "beginner"}
        and len(texto_evaluable) > 3000
    ):
        adaptacion = 3

    elif (
        nivel_detalle in {"alto", "high"}
        and len(texto_evaluable) < 200
    ):
        adaptacion = 2

    # ========================================================
    # 4. INFORMACIÓN RESPALDADA
    # ========================================================

    palabras_generadas = set(
        _palabras_significativas(
            texto_evaluable
        )
    )

    palabras_fuente = set(
        _palabras_significativas(
            chunks_text
        )
    )

    if palabras_generadas:
        palabras_no_respaldadas = (
            palabras_generadas
            - palabras_fuente
        )

        ratio_no_respaldado = (
            len(palabras_no_respaldadas)
            / len(palabras_generadas)
        )
    else:
        ratio_no_respaldado = 0.0

    informacion_no_respaldada = (
        ratio_no_respaldado > 0.40
    )

    if ratio_no_respaldado <= 0.15:
        informacion_respaldada = 5
    elif ratio_no_respaldado <= 0.30:
        informacion_respaldada = 4
    elif ratio_no_respaldado <= 0.40:
        informacion_respaldada = 3
    else:
        informacion_respaldada = 1

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
