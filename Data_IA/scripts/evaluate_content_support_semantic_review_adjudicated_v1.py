"""Evalúa resultados semánticos contra ground truth adjudicado.

Este script NO llama a Gemini y NO modifica producción.

Cruza:
- content_support_semantic_review_results_v1.csv
- content_support_claim_ground_truth_v1.csv

por:
- calibration_id
- claim_id

Usa SIEMPRE la etiqueta humana más reciente del GT.

Los claims con human_support_label == uncertain
se excluyen de las métricas binarias.
"""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

SEMANTIC_RESULTS = (
    RESULTS_DIR
    / "content_support_semantic_review_results_v1.csv"
)

GROUND_TRUTH = (
    RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)

OUTPUT_METRICS = (
    RESULTS_DIR
    / "content_support_semantic_review_adjudicated_metrics_v1.csv"
)

OUTPUT_CASES = (
    RESULTS_DIR
    / "content_support_semantic_review_adjudicated_cases_v1.csv"
)


def load_csv(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def key(
    row: dict[str, str],
) -> tuple[str, str]:
    return (
        row["calibration_id"],
        row["claim_id"],
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
    semantic_rows = load_csv(
        SEMANTIC_RESULTS
    )

    gt_rows = load_csv(
        GROUND_TRUTH
    )

    gt_by_key = {
        key(row): row
        for row in gt_rows
    }

    merged = []

    missing_gt = []

    for semantic_row in semantic_rows:
        row_key = key(
            semantic_row
        )

        gt_row = gt_by_key.get(
            row_key
        )

        if gt_row is None:
            missing_gt.append(
                row_key
            )
            continue

        current_label = (
            gt_row[
                "human_support_label"
            ]
            .strip()
            .lower()
        )

        merged.append(
            {
                **semantic_row,
                "human_support_label_original": (
                    semantic_row[
                        "human_support_label"
                    ]
                ),
                "human_support_label_adjudicated": (
                    current_label
                ),
                "human_notes_adjudicated": (
                    gt_row[
                        "human_notes"
                    ]
                ),
            }
        )

    if missing_gt:
        print(
            "WARNING: resultados sin GT:"
        )

        for item in missing_gt:
            print(
                "-",
                item[0],
                item[1],
            )

    successful = [
        row
        for row in merged
        if row[
            "semantic_status"
        ].strip()
        == "success"
    ]

    uncertain = [
        row
        for row in successful
        if row[
            "human_support_label_adjudicated"
        ]
        == "uncertain"
    ]

    evaluated = []

    for row in successful:
        human = row[
            "human_support_label_adjudicated"
        ]

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

    technical_coverage = safe_divide(
        len(successful),
        len(semantic_rows),
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
        "total_semantic_results": (
            len(semantic_rows)
        ),
        "successful_claims": (
            len(successful)
        ),
        "uncertain_excluded": (
            len(uncertain)
        ),
        "evaluated_claims": (
            len(evaluated)
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
        "REVIEW — ADJUDICATED V1"
    )
    print("=" * 80)

    for metric, value in (
        metrics.items()
    ):
        if isinstance(
            value,
            float,
        ):
            print(
                f"{metric} = "
                f"{value:.4f}"
            )
        else:
            print(
                f"{metric} = {value}"
            )

    print()
    print("=" * 80)
    print(
        "REMAINING DISAGREEMENTS"
    )
    print("=" * 80)

    disagreements = [
        row
        for row in evaluated
        if row[
            "confusion"
        ]
        in {
            "FP",
            "FN",
        }
    ]

    if not disagreements:
        print(
            "None"
        )

    for row in disagreements:
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
                "human_support_label_adjudicated"
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

    case_fieldnames = [
        "calibration_id",
        "format",
        "claim_id",
        "claim_text",
        "human_support_label_original",
        "human_support_label_adjudicated",
        "human_notes_adjudicated",
        "semantic_status",
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