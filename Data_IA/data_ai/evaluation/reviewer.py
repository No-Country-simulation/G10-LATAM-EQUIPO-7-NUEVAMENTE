"""Orquestador de la evaluación heurística de contenido generado.

Este módulo coordina el evaluador heurístico V1.1 y la rúbrica
de decisión legacy.

Formatos soportados:
- quiz
- flashcards
- tldr
- video_script

Este módulo todavía devuelve el contrato interno legacy
EvaluacionReviewerContract.

La migración al contrato Evaluation V2 se realiza en una capa
independiente para mantener compatibilidad durante Sprint 4.
"""

from typing import List, Union

from data_ai.evaluation.quality_evaluator import evaluate
from data_ai.evaluation.rubric import calcular_veredicto_evaluacion
from data_ai.schemas.evaluation import EvaluacionReviewerContract
from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    FlashcardsContent,
    GenerationContext,
    QuizContent,
    TLDRContent,
    VideoScriptContent,
)


GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
    TLDRContent,
    VideoScriptContent,
]


def evaluar_contenido(
    generated_content: GeneratedContent,
    chunks_used: List[ChunkUsed],
    generation_context: GenerationContext,
) -> EvaluacionReviewerContract:
    """Evalúa un contenido educativo generado.

    Orquesta:

    1. cálculo de scores heurísticos;
    2. detección de información no respaldada;
    3. cálculo del veredicto legacy.

    Parameters
    ----------
    generated_content:
        Contenido generado en uno de los cuatro formatos
        soportados por Data/IA.

    chunks_used:
        Evidencia factual utilizada durante la generación.

    generation_context:
        Contexto pedagógico utilizado para adaptar el contenido.

    Returns
    -------
    EvaluacionReviewerContract
        Resultado heurístico estructurado con status legacy,
        scores, detección de información no respaldada y
        observaciones.
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