"""Evalúa el routing experimental de content_support_v2.

Este script NO modifica producción.

Objetivo:
- leer los resultados por claim del experimento content_support_v2;
- resumir la decisión de routing a nivel de caso;
- comparar esa decisión contra ground truth humano;
- calcular TP, FP, FN, TN;
- calcular precision, recall, specificity y accuracy;
- generar CSVs de análisis.

Definición experimental:

case_requires_semantic_review = True
si al menos un factual claim tiene
needs_semantic_review = True.

Ground truth positivo:
- casos cuyo problema esperado incluye unsupported content;
- en particular, variant == unsupported_claim.

Ground truth negativo:
- clean_reference;
- perturbaciones cuyo target principal no es content_support.

Importante:
este análisis evalúa el ROUTER,
no el evaluador semántico final.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

CASES_DIR = Path(
    "data/evaluation/calibration_v1/cases"
)

INPUT_CLAIMS_CSV = (
    RESULTS_DIR
    / "content_support_v2_experiment_batch1.csv"
)

HUMAN_GT_CSV = (
    RESULTS_DIR
    / "human_gt_vs_semantic_v1.csv"
)

OUTPUT_CASE_CSV = (
    RESULTS_DIR
    / "content_support_v2_routing_cases_batch1.csv"
)

OUTPUT_METRICS_CSV = (
    RESULTS_DIR
    / "content_support_v2_routing_metrics_batch1.csv"
)


def parse_bool(
    value: str,
) -> bool:
    """Convierte strings CSV a bool."""

    normalized = (
        value.strip().lower()
    )

    return normalized in {
        "true",
        "1",
        "yes",
    }


def load_claim_rows() -> list[dict[str, str]]:
    """Carga resultados por claim."""

    with INPUT_CLAIMS_CSV.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def load_human_gt() -> dict[str, dict[str, str]]:
    """Carga ground truth humano indexado por calibration_id."""

    with HUMAN_GT_CSV.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    return {
        row["calibration_id"]: row
        for row in rows
    }


def infer_expected_support_issue(
    gt_row: dict[str, str],
) -> bool:
    """Determina si el ground truth espera un problema de soporte.

    Se intenta usar información explícita del CSV.

    Si existe una columna booleana relacionada con
    expected unsupported information, se usa.

    Como fallback, se usa la variante o target dimension
    si están disponibles.
    """

    candidate_columns = [
        "expected_unsupported_information",
        "expected_unsupported",
        "unsupported_expected",
        "expected_support_issue",
    ]

    for column in candidate_columns:
        if column in gt_row:
            value = (
                gt_row[column]
                .strip()
            )

            if value:
                return parse_bool(
                    value
                )

    variant = (
        gt_row.get(
            "variant",
            "",
        )
        .strip()
        .lower()
    )

    if variant == "unsupported_claim":
        return True

    target_dimension = (
        gt_row.get(
            "target_dimension",
            "",
        )
        .strip()
        .lower()
    )

    expected_verdict = (
        gt_row.get(
            "expected_verdict",
            "",
        )
        .strip()
        .lower()
    )

    if (
        target_dimension
        == "content_support"
        and expected_verdict
        in {
            "requires_revision",
            "rejected",
        }
    ):
        return True

    return False


def summarize_routing(
    claim_rows: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    """Resume routing por calibration_id."""

    grouped: dict[
        str,
        list[dict[str, str]],
    ] = {}

    for row in claim_rows:
        calibration_id = row[
            "calibration_id"
        ]

        grouped.setdefault(
            calibration_id,
            [],
        ).append(
            row
        )

    summaries: dict[
        str,
        dict[str, Any],
    ] = {}

    for (
        calibration_id,
        rows,
    ) in grouped.items():

        factual_rows = [
            row
            for row in rows
            if row["factual_role"]
            == "factual_content"
        ]

        semantic_review_rows = [
            row
            for row in factual_rows
            if parse_bool(
                row[
                    "needs_semantic_review"
                ]
            )
        ]

        summaries[
            calibration_id
        ] = {
            "calibration_id": (
                calibration_id
            ),
            "format": (
                rows[0]["format"]
                if rows
                else ""
            ),
            "total_claims": len(
                rows
            ),
            "factual_claims": len(
                factual_rows
            ),
            "semantic_review_claims": len(
                semantic_review_rows
            ),
            "case_requires_semantic_review": bool(
                semantic_review_rows
            ),
        }

    return summaries


def classify_confusion(
    expected_positive: bool,
    predicted_positive: bool,
) -> str:
    """Clasifica resultado en matriz de confusión."""

    if (
        expected_positive
        and predicted_positive
    ):
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


def safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    """División segura."""

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
    )


def calculate_metrics(
    case_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calcula métricas del router."""

    tp = sum(
        1
        for row in case_rows
        if row["confusion"] == "TP"
    )

    fp = sum(
        1
        for row in case_rows
        if row["confusion"] == "FP"
    )

    fn = sum(
        1
        for row in case_rows
        if row["confusion"] == "FN"
    )

    tn = sum(
        1
        for row in case_rows
        if row["confusion"] == "TN"
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
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "accuracy": accuracy,
        "case_review_rate": review_rate,
    }


def write_case_results(
    rows: list[dict[str, Any]],
) -> None:
    """Guarda resultados por caso."""

    fieldnames = [
        "calibration_id",
        "format",
        "total_claims",
        "factual_claims",
        "semantic_review_claims",
        "case_requires_semantic_review",
        "expected_support_issue",
        "confusion",
    ]

    with OUTPUT_CASE_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    key: row[key]
                    for key in fieldnames
                }
            )


def write_metrics(
    metrics: dict[str, Any],
) -> None:
    """Guarda métricas globales."""

    fieldnames = [
        "tp",
        "fp",
        "fn",
        "tn",
        "precision",
        "recall",
        "specificity",
        "accuracy",
        "case_review_rate",
    ]

    with OUTPUT_METRICS_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerow(
            metrics
        )


def main() -> None:
    claim_rows = load_claim_rows()

    human_gt = load_human_gt()

    routing = summarize_routing(
        claim_rows
    )

    case_rows: list[
        dict[str, Any]
    ] = []

    print()
    print("=" * 90)
    print(
        "CONTENT SUPPORT V2 ROUTING EVALUATION"
    )
    print("=" * 90)

    for (
        calibration_id,
        routing_row,
    ) in routing.items():

        gt_row = human_gt.get(
            calibration_id
        )

        if gt_row is None:
            print()
            print(
                f"{calibration_id}: "
                "sin ground truth humano, "
                "se omite de métricas."
            )

            continue

        expected_support_issue = (
            infer_expected_support_issue(
                gt_row
            )
        )

        predicted_review = (
            routing_row[
                "case_requires_semantic_review"
            ]
        )

        confusion = classify_confusion(
            expected_support_issue,
            predicted_review,
        )

        result = {
            **routing_row,
            "expected_support_issue": (
                expected_support_issue
            ),
            "confusion": confusion,
        }

        case_rows.append(
            result
        )

        print()
        print("-" * 70)

        print(
            "CASE:",
            calibration_id,
        )

        print(
            "expected_support_issue=",
            expected_support_issue,
        )

        print(
            "case_requires_semantic_review=",
            predicted_review,
        )

        print(
            "semantic_review_claims=",
            routing_row[
                "semantic_review_claims"
            ],
        )

        print(
            "confusion=",
            confusion,
        )

    metrics = calculate_metrics(
        case_rows
    )

    write_case_results(
        case_rows
    )

    write_metrics(
        metrics
    )

    print()
    print("=" * 90)
    print("ROUTER METRICS")
    print("=" * 90)

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

    print()

    print(
        "precision =",
        round(
            metrics["precision"],
            4,
        ),
    )

    print(
        "recall =",
        round(
            metrics["recall"],
            4,
        ),
    )

    print(
        "specificity =",
        round(
            metrics["specificity"],
            4,
        ),
    )

    print(
        "accuracy =",
        round(
            metrics["accuracy"],
            4,
        ),
    )

    print(
        "case_review_rate =",
        round(
            metrics[
                "case_review_rate"
            ],
            4,
        ),
    )

    print()
    print("=" * 90)
    print("RESULT FILES")
    print("=" * 90)

    print(
        OUTPUT_CASE_CSV
    )

    print(
        OUTPUT_METRICS_CSV
    )


if __name__ == "__main__":
    main()