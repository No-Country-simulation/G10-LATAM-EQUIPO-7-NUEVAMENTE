"""Evalúa el benchmark semántico claim-level de content_support.

Este script NO modifica producción.

Compara:
- human_support_label
- semantic_supported

sobre resultados exitosos del runner Gemini.

Calcula:
- TP
- FP
- FN
- TN
- precision
- recall
- specificity
- accuracy
- cobertura técnica
- latencia media/min/max
"""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

INPUT_CSV = (
    RESULTS_DIR
    / "content_support_semantic_review_results_v1.csv"
)

OUTPUT_CSV = (
    RESULTS_DIR
    / "content_support_semantic_review_metrics_v1.csv"
)


def safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def confusion(
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
    with INPUT_CSV.open(
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
        if row[
            "semantic_status"
        ] == "success"
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
                "confusion": confusion(
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

    technical_coverage = safe_divide(
        len(successful),
        len(rows),
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

    min_latency = (
        min(latencies)
        if latencies
        else 0
    )

    max_latency = (
        max(latencies)
        if latencies
        else 0
    )

    metrics = {
        "total_manifest_claims": len(
            rows
        ),
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
        "technical_coverage": (
            technical_coverage
        ),
        "average_latency_ms": (
            round(
                average_latency,
                2,
            )
        ),
        "min_latency_ms": (
            min_latency
        ),
        "max_latency_ms": (
            max_latency
        ),
    }

    print()
    print("=" * 80)
    print(
        "CONTENT SUPPORT SEMANTIC "
        "REVIEW METRICS V1"
    )
    print("=" * 80)

    for key, value in metrics.items():
        if isinstance(
            value,
            float,
        ):
            print(
                f"{key} = "
                f"{value:.4f}"
            )
        else:
            print(
                f"{key} = {value}"
            )

    with OUTPUT_CSV.open(
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
    print(
        "Output:",
        OUTPUT_CSV,
    )


if __name__ == "__main__":
    main()