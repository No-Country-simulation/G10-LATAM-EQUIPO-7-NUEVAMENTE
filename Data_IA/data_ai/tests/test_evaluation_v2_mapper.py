"""Tests para evaluation_v2_mapper."""

import pytest

from data_ai.evaluation.evaluation_v2_mapper import (
    LEGACY_VERDICT_MAP,
    map_heuristic_scores_to_v2,
    map_legacy_verdict_to_v2,
)
from data_ai.schemas.format_evaluation import (
    EvaluationScores,
)


def _legacy_scores() -> EvaluationScores:
    return EvaluationScores(
        relevancia=5,
        coherencia=4,
        adaptacion_didactica=3,
        informacion_respaldada=2,
    )


def test_map_heuristic_scores_to_v2():
    result = map_heuristic_scores_to_v2(
        _legacy_scores()
    )

    assert result.relevance == 5.0
    assert result.coherence == 4.0

    assert (
        result.didactic_adaptation
        == 3.0
    )

    assert (
        result.content_support
        == 2.0
    )


def test_mapping_does_not_modify_original_scores():
    original = _legacy_scores()

    map_heuristic_scores_to_v2(
        original
    )

    assert original.relevancia == 5
    assert original.coherencia == 4

    assert (
        original.adaptacion_didactica
        == 3
    )

    assert (
        original.informacion_respaldada
        == 2
    )


@pytest.mark.parametrize(
    (
        "legacy_status",
        "expected_verdict",
    ),
    [
        (
            "aprobado",
            "approved",
        ),
        (
            "requiere_revision",
            "requires_revision",
        ),
        (
            "rechazado",
            "rejected",
        ),
    ],
)
def test_map_legacy_verdict_to_v2(
    legacy_status,
    expected_verdict,
):
    result = map_legacy_verdict_to_v2(
        legacy_status
    )

    assert result == expected_verdict


def test_legacy_verdict_map_contains_exact_values():
    assert LEGACY_VERDICT_MAP == {
        "aprobado": "approved",
        "requiere_revision": (
            "requires_revision"
        ),
        "rechazado": "rejected",
    }


def test_map_legacy_verdict_rejects_unknown_status():
    with pytest.raises(
        ValueError,
        match=(
            "Unsupported legacy "
            "evaluation status"
        ),
    ):
        map_legacy_verdict_to_v2(
            "unknown",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "score_value",
    [
        1,
        2,
        3,
        4,
        5,
    ],
)
def test_mapper_preserves_score_values(
    score_value,
):
    original = EvaluationScores(
        relevancia=score_value,
        coherencia=score_value,
        adaptacion_didactica=score_value,
        informacion_respaldada=(
            score_value
        ),
    )

    mapped = (
        map_heuristic_scores_to_v2(
            original
        )
    )

    assert mapped.relevance == float(
        score_value
    )

    assert mapped.coherence == float(
        score_value
    )

    assert (
        mapped.didactic_adaptation
        == float(score_value)
    )

    assert (
        mapped.content_support
        == float(score_value)
    )