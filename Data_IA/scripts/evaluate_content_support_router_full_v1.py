"""Evaluación completa del router experimental de content_support.

Este script NO modifica producción.

Objetivo:
- cargar todos los casos CAL-V1-*.json disponibles;
- extraer unidades estructurales;
- dividir contenido factual en claims;
- excluir prompts pedagógicos;
- comparar routing legacy vs routing normalizado;
- contrastar ambos contra ground truth humano;
- calcular matrices de confusión y métricas globales;
- generar resultados reproducibles en CSV.

Importante:
- evalúa routing, no soporte factual final;
- no llama a Gemini;
- no modifica quality_evaluator.py;
- no modifica umbrales productivos.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from data_ai.schemas.format_evaluation import (
    EvaluationRequest,
)

from scripts.experiment_content_support_v2 import (
    CASES_DIR,
    RESULTS_DIR,
    extract_structural_units,
    expand_unit_into_claims,
)

from scripts.experiment_content_support_normalization_v1 import (
    calculate_legacy,
    calculate_normalized,
    requires_review,
)

from data_ai.evaluation.quality_evaluator import (
    _palabras_significativas,
)


HUMAN_GT_CSV = (
    RESULTS_DIR
    / "human_gt_vs_semantic_v1.csv"
)

OUTPUT_CASES_CSV = (
    RESULTS_DIR
    / "content_support_router_full_v1_cases.csv"
)

OUTPUT_METRICS_CSV = (
    RESULTS_DIR
    / "content_support_router_full_v1_metrics.csv"
)

OUTPUT_CLAIMS_CSV = (
    RESULTS_DIR
    / "content_support_router_full_v1_claims.csv"
)


# ============================================================
# UTILIDADES
# ============================================================


def parse_bool(
    value: str,
) -> bool:
    """Convierte representación textual a bool."""

    return value.strip().lower() in {
        "true",
        "1",
        "yes",
    }


def safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    """División segura."""

    if denominator == 0:
        return 0.0

    return numerator / denominator


def classify_confusion(
    expected_positive: bool,
    predicted_positive: bool,
) -> str:
    """Clasifica TP / FP / FN / TN."""

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


# ============================================================
# GROUND TRUTH
# ============================================================


def load_human_gt() -> dict[str, dict[str, str]]:
    """Carga ground truth humano."""

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
    """Determina si el caso tiene problema esperado de content support.

    Prioriza columnas explícitas de unsupported information.
    """

    candidate_columns = [
        "expected_unsupported_information",
        "expected_unsupported",
        "unsupported_expected",
        "expected_support_issue",
    ]

    for column in candidate_columns:
        if column not in gt_row:
            continue

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


# ============================================================
# CASOS
# ============================================================


def discover_cases() -> list[Path]:
    """Encuentra todos los CAL-V1-*.json."""

    return sorted(
        CASES_DIR.glob(
            "CAL-V1-*.json"
        )
    )


def evaluate_case(
    case_path: Path,
    adapter: TypeAdapter,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
]:
    """Evalúa un caso con ambos routers."""

    data = json.loads(
        case_path.read_text(
            encoding="utf-8"
        )
    )

    request = adapter.validate_python(
        data["evaluation_request"]
    )

    calibration_id = (
        data.get(
            "calibration_id"
        )
        or case_path.stem
    )

    chunks_text = " ".join(
        chunk.text
        for chunk in request.chunks_used
    )

    source_terms_list = (
        _palabras_significativas(
            chunks_text
        )
    )

    source_terms_set = set(
        source_terms_list
    )

    units = extract_structural_units(
        request
    )

    claim_rows: list[
        dict[str, Any]
    ] = []

    for unit in units:
        claims = expand_unit_into_claims(
            unit
        )

        for claim in claims:
            legacy = calculate_legacy(
                claim["claim_text"],
                source_terms_set,
            )

            normalized = (
                calculate_normalized(
                    claim["claim_text"],
                    source_terms_list,
                )
            )

            legacy_review = (
                requires_review(
                    claim[
                        "factual_role"
                    ],
                    legacy[
                        "legacy_status"
                    ],
                )
            )

            normalized_review = (
                requires_review(
                    claim[
                        "factual_role"
                    ],
                    normalized[
                        "normalized_status"
                    ],
                )
            )

            row = {
                "calibration_id": (
                    calibration_id
                ),
                "format": (
                    request.format
                ),
                "unit_id": (
                    claim["unit_id"]
                ),
                "unit_type": (
                    claim["unit_type"]
                ),
                "factual_role": (
                    claim[
                        "factual_role"
                    ]
                ),
                "claim_id": (
                    claim["claim_id"]
                ),
                "claim_text": (
                    claim["claim_text"]
                ),
                "legacy_ratio": (
                    legacy[
                        "legacy_ratio"
                    ]
                ),
                "legacy_status": (
                    legacy[
                        "legacy_status"
                    ]
                ),
                "legacy_needs_review": (
                    legacy_review
                ),
                "normalized_ratio": (
                    normalized[
                        "normalized_ratio"
                    ]
                ),
                "normalized_status": (
                    normalized[
                        "normalized_status"
                    ]
                ),
                "normalized_needs_review": (
                    normalized_review
                ),
            }

            claim_rows.append(
                row
            )

    factual_rows = [
        row
        for row in claim_rows
        if row["factual_role"]
        == "factual_content"
    ]

    legacy_review_rows = [
        row
        for row in factual_rows
        if row[
            "legacy_needs_review"
        ]
    ]

    normalized_review_rows = [
        row
        for row in factual_rows
        if row[
            "normalized_needs_review"
        ]
    ]

    case_summary = {
        "calibration_id": (
            calibration_id
        ),
        "format": (
            request.format
        ),
        "total_claims": len(
            claim_rows
        ),
        "factual_claims": len(
            factual_rows
        ),
        "legacy_review_claims": len(
            legacy_review_rows
        ),
        "normalized_review_claims": len(
            normalized_review_rows
        ),
        "legacy_case_review": bool(
            legacy_review_rows
        ),
        "normalized_case_review": bool(
            normalized_review_rows
        ),
    }

    return (
        case_summary,
        claim_rows,
    )


# ============================================================
# MÉTRICAS
# ============================================================


def calculate_metrics(
    rows: list[dict[str, Any]],
    prefix: str,
) -> dict[str, Any]:
    """Calcula métricas para legacy o normalized."""

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
        "case_review_rate": (
            review_rate
        ),
    }


# ============================================================
# EXPORTACIÓN
# ============================================================


def write_claims(
    rows: list[dict[str, Any]],
) -> None:
    """Exporta resultados por claim."""

    fieldnames = [
        "calibration_id",
        "format",
        "unit_id",
        "unit_type",
        "factual_role",
        "claim_id",
        "claim_text",
        "legacy_ratio",
        "legacy_status",
        "legacy_needs_review",
        "normalized_ratio",
        "normalized_status",
        "normalized_needs_review",
    ]

    with OUTPUT_CLAIMS_CSV.open(
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


def write_cases(
    rows: list[dict[str, Any]],
) -> None:
    """Exporta comparación por caso."""

    fieldnames = [
        "calibration_id",
        "format",
        "total_claims",
        "factual_claims",
        "legacy_review_claims",
        "normalized_review_claims",
        "legacy_case_review",
        "normalized_case_review",
        "expected_support_issue",
        "legacy_confusion",
        "normalized_confusion",
    ]

    with OUTPUT_CASES_CSV.open(
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
    rows: list[dict[str, Any]],
) -> None:
    """Exporta métricas globales."""

    fieldnames = [
        "router",
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

        for row in rows:
            writer.writerow(
                row
            )


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    adapter = TypeAdapter(
        EvaluationRequest
    )

    human_gt = load_human_gt()

    case_paths = discover_cases()

    print()
    print("=" * 90)
    print(
        "CONTENT SUPPORT ROUTER FULL EVALUATION V1"
    )
    print("=" * 90)

    print(
        "Cases discovered:",
        len(case_paths),
    )

    all_claim_rows: list[
        dict[str, Any]
    ] = []

    evaluated_case_rows: list[
        dict[str, Any]
    ] = []

    skipped_no_gt: list[str] = []

    for case_path in case_paths:
        (
            case_summary,
            claim_rows,
        ) = evaluate_case(
            case_path,
            adapter,
        )

        calibration_id = (
            case_summary[
                "calibration_id"
            ]
        )

        all_claim_rows.extend(
            claim_rows
        )

        gt_row = human_gt.get(
            calibration_id
        )

        if gt_row is None:
            skipped_no_gt.append(
                calibration_id
            )

            print()
            print(
                f"{calibration_id}: "
                "sin ground truth humano "
                "→ excluido de métricas."
            )

            continue

        expected_support_issue = (
            infer_expected_support_issue(
                gt_row
            )
        )

        legacy_confusion = (
            classify_confusion(
                expected_support_issue,
                case_summary[
                    "legacy_case_review"
                ],
            )
        )

        normalized_confusion = (
            classify_confusion(
                expected_support_issue,
                case_summary[
                    "normalized_case_review"
                ],
            )
        )

        result = {
            **case_summary,
            "expected_support_issue": (
                expected_support_issue
            ),
            "legacy_confusion": (
                legacy_confusion
            ),
            "normalized_confusion": (
                normalized_confusion
            ),
        }

        evaluated_case_rows.append(
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
            "legacy_review_claims=",
            result[
                "legacy_review_claims"
            ],
        )

        print(
            "legacy_case_review=",
            result[
                "legacy_case_review"
            ],
        )

        print(
            "legacy_confusion=",
            legacy_confusion,
        )

        print(
            "normalized_review_claims=",
            result[
                "normalized_review_claims"
            ],
        )

        print(
            "normalized_case_review=",
            result[
                "normalized_case_review"
            ],
        )

        print(
            "normalized_confusion=",
            normalized_confusion,
        )

    legacy_metrics = (
        calculate_metrics(
            evaluated_case_rows,
            "legacy",
        )
    )

    normalized_metrics = (
        calculate_metrics(
            evaluated_case_rows,
            "normalized",
        )
    )

    write_claims(
        all_claim_rows
    )

    write_cases(
        evaluated_case_rows
    )

    write_metrics(
        [
            legacy_metrics,
            normalized_metrics,
        ]
    )

    print()
    print("=" * 90)
    print("GLOBAL COMPARISON")
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
    print("DATASET")
    print("=" * 90)

    print(
        "discovered_cases=",
        len(case_paths),
    )

    print(
        "cases_with_human_gt=",
        len(
            evaluated_case_rows
        ),
    )

    print(
        "cases_without_human_gt=",
        len(
            skipped_no_gt
        ),
    )

    if skipped_no_gt:
        print(
            "without_gt=",
            skipped_no_gt,
        )

    print()
    print("=" * 90)
    print("RESULT FILES")
    print("=" * 90)

    print(
        OUTPUT_CLAIMS_CSV
    )

    print(
        OUTPUT_CASES_CSV
    )

    print(
        OUTPUT_METRICS_CSV
    )


if __name__ == "__main__":
    main()