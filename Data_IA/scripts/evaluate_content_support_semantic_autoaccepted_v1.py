"""Evalúa Gemini sobre claims que legacy habría autoaceptado.

NO modifica producción.

Calcula métricas contra human_support_label para:
content_support_semantic_autoaccepted_results_v1.csv
"""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

INPUT_RESULTS = (
    RESULTS_DIR
    / "content_support_semantic_autoaccepted_results_v1.csv"
)

OUTPUT_METRICS = (
    RESULTS_DIR
    / "content_support_semantic_autoaccepted_metrics_v1.csv"
)

OUTPUT_CASES = (
    RESULTS_DIR
    / "content_support_semantic_autoaccepted_cases_v1.csv"
)


def safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def classify(
    human: str,
    semantic: str,
) -> str:
    expected_positive = (
        human == "unsupported"
    )

    predicted_positive = (
        semantic == "unsupported"
    )

    if expected_positive and predicted_positive:
        return "TP"

    if (
        not expected_positive
        and predicted_positive
    ):
        return "FP"

    if (
        expected_positive
        and not predicted_positive
    ):
        return "FN"

    return "TN"


def main() -> None:
    with INPUT_RESULTS.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    successful = [
        row
        for row in rows
        if (
            row[
                "semantic_status"
            ].strip()
            == "success"
        )
    ]

    evaluated = []

    for row in successful:
        human = (
            row[
                "human_support_label"
            ]
            .strip()
            .lower()
        )

        semantic = (
            row[
                "semantic_supported"
            ]
            .strip()
            .lower()
        )

        if human not in {
            "supported",
            "unsupported",
        }:
            continue

        if semantic not in {
            "supported",
            "unsupported",
        }:
            continue

        evaluated.append(
            {
                **row,
                "confusion": classify(
                    human,
                    semantic,
                ),
            }
        )

    tp = sum(
        row["confusion"] == "TP"
        for row in evaluated
    )

    fp = sum(
        row["confusion"] == "FP"
        for row in evaluated
    )

    fn = sum(
        row["confusion"] == "FN"
        for row in evaluated
    )

    tn = sum(
        row["confusion"] == "TN"
        for row in evaluated
    )

    precision = safe_divide(
        tp,
        tp + fp,
    )

    recall = safe_divide(
        tp,
        tp + fn,
    )

    specificity = safe_divide(
        tn,
        tn + fp,
    )

    accuracy = safe_divide(
        tp + tn,
        tp + fp + fn + tn,
    )

    latencies = [
        int(
            row[
                "semantic_latency_ms"
            ]
        )
        for row in successful
        if row[
            "semantic_latency_ms"
        ].strip()
    ]

    average_latency = (
        mean(latencies)
        if latencies
        else 0.0
    )

    metrics = {
        "total_claims": len(rows),
        "successful_claims": len(
            successful
        ),
        "evaluated_claims": len(
            evaluated
        ),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "accuracy": accuracy,
        "average_latency_ms": round(
            average_latency,
            2,
        ),
        "min_latency_ms": (
            min(latencies)
            if latencies
            else 0
        ),
        "max_latency_ms": (
            max(latencies)
            if latencies
            else 0
        ),
    }

    print()
    print("=" * 80)
    print(
        "CONTENT SUPPORT SEMANTIC "
        "AUTOACCEPTED METRICS V1"
    )
    print("=" * 80)

    for name, value in metrics.items():
        if isinstance(
            value,
            float,
        ):
            print(
                f"{name} = "
                f"{value:.4f}"
            )
        else:
            print(
                f"{name} = {value}"
            )

    print()
    print("=" * 80)
    print("ERROR CASES")
    print("=" * 80)

    errors = [
        row
        for row in evaluated
        if row["confusion"]
        in {
            "FP",
            "FN",
        }
    ]

    if not errors:
        print("None")

    for row in errors:
        print()

        print(
            row[
                "calibration_id"
            ],
            row[
                "claim_id"
            ],
        )

        print(
            "HUMAN:",
            row[
                "human_support_label"
            ],
        )

        print(
            "SEMANTIC:",
            row[
                "semantic_supported"
            ],
        )

        print(
            "CONFUSION:",
            row[
                "confusion"
            ],
        )

        print(
            "REASON:",
            row[
                "semantic_reason"
            ],
        )

    case_fieldnames = [
        "calibration_id",
        "format",
        "claim_id",
        "claim_text",
        "human_support_label",
        "semantic_supported",
        "semantic_reason",
        "semantic_model",
        "semantic_prompt_version",
        "semantic_latency_ms",
        "confusion",
    ]

    with OUTPUT_CASES.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=case_fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(
            evaluated
        )

    with OUTPUT_METRICS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(
                metrics.keys()
            ),
        )

        writer.writeheader()
        writer.writerow(
            metrics
        )

    print()
    print("=" * 80)
    print("OUTPUTS")
    print("=" * 80)

    print(
        OUTPUT_CASES
    )

    print(
        OUTPUT_METRICS
    )


if __name__ == "__main__":
    main()