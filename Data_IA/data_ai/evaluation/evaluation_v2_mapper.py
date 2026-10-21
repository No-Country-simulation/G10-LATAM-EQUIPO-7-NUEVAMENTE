"""Mapping determinista entre Evaluation V1.1 y Evaluation V2.

Este módulo traduce los contratos actuales del evaluador heurístico
al vocabulario público definido para Sprint 4.

Responsabilidades:
- traducir nombres de scores V1.1 -> V2;
- traducir verdict legacy español -> vocabulario canónico V2;
- construir HeuristicScoresV2 a partir del evaluator actual.

Este módulo NO:
- recalcula scores;
- combina heurístico y semántico;
- llama a Gemini;
- decide retries;
- modifica el endpoint /evaluate;
- persiste evaluaciones.
"""

from __future__ import annotations

from typing import Literal

from data_ai.schemas.evaluation_v2 import (
    EvaluationVerdict,
    HeuristicScoresV2,
)
from data_ai.schemas.format_evaluation import (
    EvaluationScores,
)


LegacyEvaluationStatus = Literal[
    "aprobado",
    "requiere_revision",
    "rechazado",
]


LEGACY_VERDICT_MAP: dict[
    LegacyEvaluationStatus,
    EvaluationVerdict,
] = {
    "aprobado": "approved",
    "requiere_revision": "requires_revision",
    "rechazado": "rejected",
}


def map_heuristic_scores_to_v2(
    scores: EvaluationScores,
) -> HeuristicScoresV2:
    """Traduce EvaluationScores V1.1 a HeuristicScoresV2.

    No modifica ni recalcula los valores originales.

    Mapping:

        relevancia
        -> relevance

        coherencia
        -> coherence

        adaptacion_didactica
        -> didactic_adaptation

        informacion_respaldada
        -> content_support

    Parameters
    ----------
    scores:
        Scores heurísticos producidos por el evaluator V1.1.

    Returns
    -------
    HeuristicScoresV2
        Scores equivalentes con nombres canónicos V2.
    """

    return HeuristicScoresV2(
        relevance=float(
            scores.relevancia
        ),
        coherence=float(
            scores.coherencia
        ),
        didactic_adaptation=float(
            scores.adaptacion_didactica
        ),
        content_support=float(
            scores.informacion_respaldada
        ),
    )


def map_legacy_verdict_to_v2(
    status: LegacyEvaluationStatus,
) -> EvaluationVerdict:
    """Traduce el status pedagógico legacy al verdict V2.

    Mapping:

        aprobado
        -> approved

        requiere_revision
        -> requires_revision

        rechazado
        -> rejected

    Parameters
    ----------
    status:
        Status producido actualmente por rubric.py.

    Returns
    -------
    EvaluationVerdict
        Valor canónico de Sprint 4.

    Raises
    ------
    ValueError
        Si se recibe un valor no soportado.
    """

    try:
        return LEGACY_VERDICT_MAP[
            status
        ]

    except KeyError as exc:
        raise ValueError(
            "Unsupported legacy evaluation status: "
            f"{status!r}"
        ) from exc