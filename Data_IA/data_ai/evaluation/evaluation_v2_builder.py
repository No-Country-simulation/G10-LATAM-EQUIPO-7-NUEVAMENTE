"""Builder del contrato público Evaluation V2.

Este módulo ensambla resultados ya calculados por los componentes
de evaluación de Data/IA.

Responsabilidades:
- traducir el resultado heurístico legacy al vocabulario V2;
- adjuntar el SemanticEvaluationResult sin modificarlo;
- construir EvaluationResponseV2;
- mantener separados scores heurísticos y semánticos.

Este módulo NO:
- ejecuta el evaluador heurístico;
- ejecuta el evaluador semántico;
- combina scores;
- calcula pesos;
- infiere un verdict a partir de scores semánticos;
- controla retries;
- modifica FastAPI;
- persiste evaluaciones.
"""

from __future__ import annotations

from data_ai.evaluation.config import (
    EVALUATOR_VERSION,
    RUBRIC_VERSION,
)
from data_ai.evaluation.evaluation_v2_mapper import (
    map_heuristic_scores_to_v2,
    map_legacy_verdict_to_v2,
)
from data_ai.schemas.evaluation import (
    EvaluacionReviewerContract,
)
from data_ai.schemas.evaluation_v2 import (
    EvaluationResponseV2,
)
from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
)
from data_ai.evaluation.evaluation_v2_decision import (
    resolve_evaluation_v2_verdict,
)

def build_evaluation_response_v2(
    *,
    document_id: str,
    content_format: str,
    heuristic_result: EvaluacionReviewerContract | None,
    semantic_evaluation: SemanticEvaluationResult,
    evaluator_version: str = EVALUATOR_VERSION,
    rubric_version: str = RUBRIC_VERSION,
) -> EvaluationResponseV2:
    """Construye una respuesta Evaluation V2.

    Parameters
    ----------
    document_id:
        Identificador del documento evaluado.

    content_format:
        Formato pedagógico evaluado.

    heuristic_result:
        Resultado producido por el reviewer heurístico legacy.
        Puede ser None si ese componente no produjo una señal válida.

    semantic_evaluation:
        Resultado normalizado del SemanticEvaluator.

    evaluator_version:
        Versión del evaluador Data/IA.

    rubric_version:
        Versión de la rúbrica utilizada.

    Returns
    -------
    EvaluationResponseV2
        Contrato V2 ensamblado.

    Notes
    -----
    Evaluation V2 utiliza Decision Layer v0.1:

    - mantiene separados los scores heurísticos y semánticos;
    - si el Semantic Evaluator falla o no está disponible,
    conserva el verdict heurístico;
    - si ambas señales coinciden, conserva el acuerdo;
    - si las señales discrepan, devuelve requires_revision;
    - no calcula promedios ni ponderaciones entre scores.
    """

    if heuristic_result is None:
        heuristic_scores = None
        heuristic_verdict = None

    else:
        heuristic_scores = (
            map_heuristic_scores_to_v2(
                heuristic_result.scores
            )
        )

        heuristic_verdict = (
            map_legacy_verdict_to_v2(
                heuristic_result.status
            )
        )

    verdict = resolve_evaluation_v2_verdict(
        heuristic_verdict=heuristic_verdict,
        semantic_evaluation=semantic_evaluation,
    )

    return EvaluationResponseV2(
        document_id=document_id,
        format=content_format,
        verdict=verdict,
        heuristic_scores=heuristic_scores,
        semantic_evaluation=semantic_evaluation,
        evaluator_version=evaluator_version,
        rubric_version=rubric_version,
    )