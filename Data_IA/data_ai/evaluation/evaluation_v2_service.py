"""Orquestación interna de Evaluation V2.

Este servicio ejecuta los componentes de evaluación de Data/IA y
ensambla su resultado utilizando el contrato EvaluationResponseV2.

Flujo:

    generated_content
          |
          +--> reviewer heurístico V1.1
          |
          +--> SemanticEvaluator
          |
          v
    Evaluation V2 Builder
          |
          v
    EvaluationResponseV2

Este módulo todavía NO está conectado al endpoint público /evaluate.
"""

from __future__ import annotations

from typing import Union

from data_ai.evaluation.evaluation_v2_builder import (
    build_evaluation_response_v2,
)
from data_ai.evaluation.reviewer import (
    evaluar_contenido,
)
from data_ai.evaluation.semantic_evaluator import (
    SemanticEvaluator,
)
from data_ai.schemas.evaluation_v2 import (
    EvaluationResponseV2,
)
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


def evaluate_content_v2(
    *,
    document_id: str,
    content_format: str,
    generated_content: GeneratedContent,
    chunks_used: list[ChunkUsed],
    generation_context: GenerationContext,
    semantic_evaluator: SemanticEvaluator,
) -> EvaluationResponseV2:
    """Ejecuta una evaluación V2 completa.

    Parameters
    ----------
    document_id:
        Identificador del documento evaluado.

    content_format:
        Formato pedagógico generado.

    generated_content:
        Contenido educativo que debe evaluarse.

    chunks_used:
        Evidencia factual recuperada por Agentes.

    generation_context:
        Contexto utilizado durante la generación.

    semantic_evaluator:
        SemanticEvaluator ya configurado con su provider.

    Returns
    -------
    EvaluationResponseV2
        Resultado V2 con señales heurísticas y semánticas separadas.

    Notes
    -----
    Mientras no exista una Decision Layer calibrada, el verdict global
    continúa derivándose exclusivamente de la evaluación heurística.
    """

    heuristic_result = evaluar_contenido(
        generated_content=generated_content,
        chunks_used=chunks_used,
        generation_context=generation_context,
    )

    semantic_result = (
        semantic_evaluator.evaluate(
            content_format=content_format,
            generated_content=generated_content,
            generation_context=generation_context,
            chunks_used=chunks_used,
        )
    )

    return build_evaluation_response_v2(
        document_id=document_id,
        content_format=content_format,
        heuristic_result=heuristic_result,
        semantic_evaluation=semantic_result,
    )