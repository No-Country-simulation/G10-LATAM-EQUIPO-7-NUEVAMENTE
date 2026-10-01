"""
Capa de integración para la evaluación de calidad de formatos generados.

Este módulo define la interfaz que utilizará POST /evaluate para conectar
con la lógica interna del evaluator.

La implementación real de scoring será integrada cuando esté disponible
la lógica desarrollada para Quiz y Flashcards.

Responsabilidades de esta capa:
- recibir generated_content;
- recibir chunks_used como evidencia;
- recibir generation_context;
- exponer una salida compatible con EvaluationResponse.

Este módulo NO implementa todavía reglas de scoring.
"""

from dataclasses import dataclass
from typing import List, Literal, Union

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


@dataclass
class QualityEvaluationResult:
    """
    Resultado interno producido por el evaluator.

    EvaluationResponse agregará posteriormente document_id y format
    en la capa API.
    """

    status: Literal[
        "aprobado",
        "requiere_revision",
        "rechazado",
    ]

    scores: EvaluationScores

    informacion_no_respaldada: bool

    observaciones: List[str]


def evaluate(
    generated_content: GeneratedContent,
    chunks_used: List[ChunkUsed],
    generation_context: GenerationContext,
) -> QualityEvaluationResult:
    """
    Evalúa la calidad del contenido generado.

    Parameters
    ----------
    generated_content:
        Quiz o Flashcards previamente validados por EvaluationRequest.

    chunks_used:
        Evidencia completa utilizada por Agentes durante la generación.

    generation_context:
        Contexto utilizado durante la generación, incluyendo profile,
        niche, detail_level y learning_objective cuando esté disponible.

    Returns
    -------
    QualityEvaluationResult
        Resultado estructurado compatible con EvaluationResponse.

    Raises
    ------
    NotImplementedError
        Mientras la lógica real del evaluator no esté integrada.
    """

    raise NotImplementedError(
        "La lógica del quality evaluator todavía no ha sido integrada."
    )


__all__ = [
    "GeneratedContent",
    "QualityEvaluationResult",
    "evaluate",
]