import pandas as pd
import pytest

from data_ai.metrics.retrieval_reporting import (
    get_case_result,
    build_metric_summary,
    build_status_summary,
    build_category_summary,
)


def make_results_df():
    return pd.DataFrame(
        [
            {
                "case_id": "Q01",
                "categoria": "IA",
                "status": "success",
                "metric_eligible": True,
                "recall_at_3": 1.0,
                "recall_at_5": 1.0,
                "precision_at_3": 1 / 3,
                "precision_at_5": 0.2,
            },
            {
                "case_id": "Q02",
                "categoria": "IA",
                "status": "no_results",
                "metric_eligible": True,
                "recall_at_3": 0.0,
                "recall_at_5": 0.0,
                "precision_at_3": 0.0,
                "precision_at_5": 0.0,
            },
            {
                "case_id": "Q03",
                "categoria": "Backend",
                "status": "error",
                "metric_eligible": False,
                "recall_at_3": None,
                "recall_at_5": None,
                "precision_at_3": None,
                "precision_at_5": None,
            },
        ]
    )


def test_get_case_result():
    results_df = make_results_df()

    result = get_case_result(
        results_df,
        "Q01",
    )

    assert result["case_id"] == "Q01"


def test_get_case_result_rejects_duplicates():
    results_df = make_results_df()

    duplicated = pd.concat(
        [
            results_df,
            results_df.loc[
                results_df["case_id"] == "Q01"
            ],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match="múltiples resultados",
    ):
        get_case_result(
            duplicated,
            "Q01",
        )


def test_metric_summary_excludes_technical_errors():
    results_df = make_results_df()

    summary = build_metric_summary(
        results_df
    )

    recall_at_5 = summary.loc[
        summary["metric"] == "recall_at_5",
        "mean",
    ].iloc[0]

    assert recall_at_5 == 0.5


def test_status_summary():
    results_df = make_results_df()

    summary = build_status_summary(
        results_df
    )

    assert summary["count"].sum() == 3

    statuses = set(
        summary["status"].tolist()
    )

    assert statuses == {
        "success",
        "no_results",
        "error",
    }


def test_category_summary_excludes_errors():
    results_df = make_results_df()

    summary = build_category_summary(
        results_df
    )

    assert "IA" in summary["categoria"].tolist()
    assert "Backend" not in summary["categoria"].tolist()