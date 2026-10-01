"""Orquestador de la evaluación de calidad del contenido generado."""

from typing import List, Union

from data_ai.evaluation.quality_evaluator import evaluate
from data_ai.evaluation.rubric import calcular_veredicto_evaluacion
from data_ai.schemas.evaluation import EvaluacionReviewerContract
from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    FlashcardsContent,
    GenerationContext,
    QuizContent,
)


GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
]


def evaluar_contenido(
    generated_content: GeneratedContent,
    chunks_used: List[ChunkUsed],
    generation_context: GenerationContext,
) -> EvaluacionReviewerContract:
    """
    Evalúa un Quiz o conjunto de Flashcards.

    Orquesta:
    1. cálculo de scores de calidad;
    2. detección de información no respaldada;
    3. cálculo del veredicto final.

    Returns
    -------
    EvaluacionReviewerContract
        Resultado estructurado con status, scores,
        informacion_no_respaldada y observaciones.
    """

    scores, informacion_no_respaldada = evaluate(
        generated_content=generated_content,
        chunks_used=chunks_used,
        generation_context=generation_context,
    )

    status, observaciones = calcular_veredicto_evaluacion(
        scores,
        informacion_no_respaldada,
    )

    return EvaluacionReviewerContract(
        status=status,
        scores=scores,
        informacion_no_respaldada=informacion_no_respaldada,
        observaciones=observaciones,
    )
