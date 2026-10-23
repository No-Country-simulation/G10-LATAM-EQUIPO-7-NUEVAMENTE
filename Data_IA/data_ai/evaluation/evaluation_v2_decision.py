"""Decision Layer v0.1 para Evaluation V2.

Combina de forma conservadora las señales heurística y semántica
sin modificar los scores originales.

Reglas principales:
- si la evaluación semántica falla o no está disponible,
  se conserva el verdict heurístico;
- si solo existe una señal válida, se utiliza esa señal;
- si ambas señales producen el mismo verdict, se conserva;
- si existe desacuerdo entre ambas, el resultado es
  ``requires_revision``.

La capa no calcula promedios ni ponderaciones.
"""

from __future__ import annotations

from data_ai.schemas.evaluation_v2 import EvaluationVerdict
from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
    SemanticScores,
)


def derive_semantic_verdict(
    scores: SemanticScores,
) -> EvaluationVerdict:
    """Deriva un verdict discreto desde los scores semánticos.

    La escala semántica admite valores float entre 1 y 5.

    Reglas:
    - cualquier dimensión <= 2.0 -> rejected;
    - cualquier dimensión < 4.0 -> requires_revision;
    - todas las dimensiones >= 4.0 -> approved.
    """

    values = (
        scores.relevance,
        scores.coherence,
        scores.didactic_adaptation,
        scores.content_support,
    )

    if any(score <= 2.0 for score in values):
        return "rejected"

    if any(score < 4.0 for score in values):
        return "requires_revision"

    return "approved"


def resolve_evaluation_v2_verdict(
    *,
    heuristic_verdict: EvaluationVerdict | None,
    semantic_evaluation: SemanticEvaluationResult,
) -> EvaluationVerdict | None:
    """Resuelve el verdict final de Evaluation V2.

    La política v0.1 prioriza seguridad y trazabilidad:

    1. Si Semantic Evaluator no produjo scores válidos,
       se conserva la señal heurística.
    2. Si no existe señal heurística pero sí semántica,
       se utiliza el verdict semántico.
    3. Si ambas señales coinciden, se conserva el acuerdo.
    4. Si ambas señales discrepan, se solicita revisión.

    Esta función no modifica los scores originales.
    """

    semantic_verdict: EvaluationVerdict | None = None

    if (
        semantic_evaluation.status == "success"
        and semantic_evaluation.scores is not None
    ):
        semantic_verdict = derive_semantic_verdict(
            semantic_evaluation.scores
        )

    if semantic_verdict is None:
        return heuristic_verdict

    if heuristic_verdict is None:
        return semantic_verdict

    if heuristic_verdict == semantic_verdict:
        return heuristic_verdict

    return "requires_revision"