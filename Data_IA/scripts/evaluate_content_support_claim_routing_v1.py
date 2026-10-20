"""Evalúa routing de content_support a nivel de claim.

Este script NO modifica producción.

Objetivo:
- leer el ground truth humano a nivel de claim;
- comparar legacy_needs_review vs normalized_needs_review;
- calcular TP, FP, FN, TN;
- calcular precision, recall, specificity, accuracy y review_rate;
- evaluar únicamente claims con human_support_label completo.

Interpretación:
- unsupported = positivo real
- supported = negativo real
- needs_review=True = predicción positiva
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

GT_FILE = (
    RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)

OUTPUT_CASES = (
    RESULTS_DIR
    / "content_support_claim_routing_v1_cases.csv"
)

OUTPUT_METRICS = (
    RESULTS_DIR
    / "content_support_claim_routing_v1_metrics.csv"
)


def parse_bool(
    value: str,
) -> bool:
    return value.strip().lower() in {
        "true",
        "1",
        "yes",
    }


def safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def classify_confusion(
    expected_positive: bool,
    predicted_positive: bool,
) -> str:
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


def calculate_metrics(
    rows: list[dict[str, Any]],
    prefix: str,
) -> dict[str, Any]:
    confusion_key = (
        f"{prefix}_confusion"
    )

    tp = sum(
        row[confusion_key] == "TP"
        for row in rows
    )

    fp = sum(
        row[confusion_key] == "FP"
        for row in rows
    )

    fn = sum(
        row[confusion_key] == "FN"
        for row in rows
    )

    tn = sum(
        row[confusion_key] == "TN"
        for row in rows
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

    review_rate = safe_divide(
        tp + fp,
        tp + fp + fn + tn,
    )

    return {
        "router": prefix,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "accuracy": accuracy,
        "review_rate": review_rate,
    }


def main() -> None:
    with GT_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    annotated = [
        row
        for row in rows
        if row[
            "human_support_label"
        ].strip()
        in {
            "supported",
            "unsupported",
        }
    ]

    evaluated_rows: list[
        dict[str, Any]
    ] = []

    print()
    print("=" * 90)
    print(
        "CONTENT SUPPORT CLAIM ROUTING EVALUATION V1"
    )
    print("=" * 90)

    print(
        "Annotated claims:",
        len(annotated),
    )

    for row in annotated:
        label = row[
            "human_support_label"
        ].strip()

        expected_positive = (
            label == "unsupported"
        )

        legacy_prediction = (
            parse_bool(
                row[
                    "legacy_needs_review"
                ]
            )
        )

        normalized_prediction = (
            parse_bool(
                row[
                    "normalized_needs_review"
                ]
            )
        )

        legacy_confusion = (
            classify_confusion(
                expected_positive,
                legacy_prediction,
            )
        )

        normalized_confusion = (
            classify_confusion(
                expected_positive,
                normalized_prediction,
            )
        )

        result = {
            "calibration_id": (
                row[
                    "calibration_id"
                ]
            ),
            "claim_id": (
                row[
                    "claim_id"
                ]
            ),
            "claim_text": (
                row[
                    "claim_text"
                ]
            ),
            "human_support_label": (
                label
            ),
            "legacy_needs_review": (
                legacy_prediction
            ),
            "legacy_confusion": (
                legacy_confusion
            ),
            "normalized_needs_review": (
                normalized_prediction
            ),
            "normalized_confusion": (
                normalized_confusion
            ),
        }

        evaluated_rows.append(
            result
        )

        print()
        print("-" * 70)

        print(
            "CASE:",
            result[
                "calibration_id"
            ],
        )

        print(
            "CLAIM:",
            result[
                "claim_id"
            ],
        )

        print(
            "HUMAN:",
            label,
        )

        print(
            "LEGACY:",
            legacy_prediction,
            legacy_confusion,
        )

        print(
            "NORMALIZED:",
            normalized_prediction,
            normalized_confusion,
        )

    legacy_metrics = (
        calculate_metrics(
            evaluated_rows,
            "legacy",
        )
    )

    normalized_metrics = (
        calculate_metrics(
            evaluated_rows,
            "normalized",
        )
    )

    print()
    print("=" * 90)
    print("CLAIM-LEVEL METRICS")
    print("=" * 90)

    for metrics in [
        legacy_metrics,
        normalized_metrics,
    ]:
        print()
        print(
            metrics["router"].upper()
        )

        print(
            "TP =",
            metrics["tp"],
        )

        print(
            "FP =",
            metrics["fp"],
        )

        print(
            "FN =",
            metrics["fn"],
        )

        print(
            "TN =",
            metrics["tn"],
        )

        print(
            "precision =",
            round(
                metrics[
                    "precision"
                ],
                4,
            ),
        )

        print(
            "recall =",
            round(
                metrics[
                    "recall"
                ],
                4,
            ),
        )

        print(
            "specificity =",
            round(
                metrics[
                    "specificity"
                ],
                4,
            ),
        )

        print(
            "accuracy =",
            round(
                metrics[
                    "accuracy"
                ],
                4,
            ),
        )

        print(
            "review_rate =",
            round(
                metrics[
                    "review_rate"
                ],
                4,
            ),
        )

    case_fieldnames = [
        "calibration_id",
        "claim_id",
        "claim_text",
        "human_support_label",
        "legacy_needs_review",
        "legacy_confusion",
        "normalized_needs_review",
        "normalized_confusion",
    ]

    with OUTPUT_CASES.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=case_fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            evaluated_rows
        )

    metrics_fieldnames = [
        "router",
        "tp",
        "fp",
        "fn",
        "tn",
        "precision",
        "recall",
        "specificity",
        "accuracy",
        "review_rate",
    ]

    with OUTPUT_METRICS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=metrics_fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            [
                legacy_metrics,
                normalized_metrics,
            ]
        )

    print()
    print("=" * 90)
    print("RESULT FILES")
    print("=" * 90)

    print(
        OUTPUT_CASES
    )

    print(
        OUTPUT_METRICS
    )


if __name__ == "__main__":
    main()