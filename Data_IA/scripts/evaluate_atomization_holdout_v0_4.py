"""Evaluate frozen Claim Atomizer v0.4 against frozen holdout v1.

This script computes two metric groups:

1. Propositional detection over all 20 holdout items:
   - valid_claim vs non_propositional
   - TP / FP / FN / TN
   - precision / recall / specificity / accuracy

2. Atomization structure over human-valid claims only:
   - class accuracy
   - count accuracy
   - type sequence accuracy
   - exact structure accuracy
   - over / under atomization
   - atom delta
   - atom inflation rate

Important:
- no Gemini calls;
- no prompt changes;
- no GT changes;
- failed provider attempts are not used when a successful
  prediction exists in the final predictions file.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1/holdout_v1"
)

GT_FILE = (
    BASE_DIR
    / "atomization_holdout_ground_truth_v1.csv"
)

PREDICTIONS_FILE = (
    BASE_DIR
    / "results"
    / "atomization_holdout_predictions_v0_4.csv"
)

OUTPUT_CASES = (
    BASE_DIR
    / "results"
    / "atomization_holdout_evaluation_cases_v0_4.csv"
)

OUTPUT_METRICS = (
    BASE_DIR
    / "results"
    / "atomization_holdout_evaluation_metrics_v0_4.csv"
)

OUTPUT_SUMMARY = (
    BASE_DIR
    / "results"
    / "atomization_holdout_evaluation_summary_v0_4.json"
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


def safe_divide(
    numerator: int | float,
    denominator: int | float,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def group_rows(
    rows: list[dict[str, str]],
    *,
    id_field: str,
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in rows:
        grouped[
            row[id_field]
        ].append(row)

    return grouped


def get_gt_status(
    rows: list[dict[str, str]],
) -> str:
    statuses = {
        row["review_status"]
        for row in rows
    }

    if len(statuses) != 1:
        raise RuntimeError(
            "Inconsistent GT review_status: "
            f"{sorted(statuses)}"
        )

    return next(
        iter(statuses)
    )


def get_pred_status(
    rows: list[dict[str, str]],
) -> str:
    success_rows = [
        row
        for row in rows
        if row["status"]
        == "success"
    ]

    if not success_rows:
        return "provider_failed"

    statuses = {
        row[
            "predicted_review_status"
        ]
        for row in success_rows
    }

    statuses.discard("")

    if len(statuses) != 1:
        raise RuntimeError(
            "Inconsistent predicted_review_status: "
            f"{sorted(statuses)}"
        )

    return next(
        iter(statuses)
    )


def get_gt_class(
    rows: list[dict[str, str]],
) -> str:
    classes = {
        row["atomization_class"]
        for row in rows
        if row["review_status"]
        == "valid_claim"
    }

    classes.discard("")

    if not classes:
        return ""

    if len(classes) != 1:
        raise RuntimeError(
            "Inconsistent GT atomization_class: "
            f"{sorted(classes)}"
        )

    return next(
        iter(classes)
    )


def get_pred_class(
    rows: list[dict[str, str]],
) -> str:
    success_rows = [
        row
        for row in rows
        if row["status"]
        == "success"
    ]

    classes = {
        row["predicted_class"]
        for row in success_rows
        if row[
            "predicted_review_status"
        ]
        == "valid_claim"
    }

    classes.discard("")

    if not classes:
        return ""

    if len(classes) != 1:
        raise RuntimeError(
            "Inconsistent predicted_class: "
            f"{sorted(classes)}"
        )

    return next(
        iter(classes)
    )


def get_gt_atoms(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    atoms = [
        row
        for row in rows
        if row["review_status"]
        == "valid_claim"
    ]

    return sorted(
        atoms,
        key=lambda row: int(
            row["atom_order"]
        ),
    )


def get_pred_atoms(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    atoms = [
        row
        for row in rows
        if (
            row["status"]
            == "success"
            and row[
                "predicted_review_status"
            ]
            == "valid_claim"
            and row[
                "predicted_atom_text"
            ].strip()
        )
    ]

    return sorted(
        atoms,
        key=lambda row: int(
            row[
                "predicted_atom_order"
            ]
        ),
    )


def main() -> None:
    gt_rows = load_csv(
        GT_FILE
    )

    prediction_rows = load_csv(
        PREDICTIONS_FILE
    )

    gt_by_id = group_rows(
        gt_rows,
        id_field="holdout_id",
    )

    pred_by_id = group_rows(
        prediction_rows,
        id_field="holdout_id",
    )

    gt_ids = set(
        gt_by_id
    )

    pred_ids = set(
        pred_by_id
    )

    missing_predictions = sorted(
        gt_ids - pred_ids
    )

    unexpected_predictions = sorted(
        pred_ids - gt_ids
    )

    if missing_predictions:
        raise RuntimeError(
            "Missing prediction IDs: "
            f"{missing_predictions}"
        )

    if unexpected_predictions:
        raise RuntimeError(
            "Unexpected prediction IDs: "
            f"{unexpected_predictions}"
        )

    # ==========================================================
    # 1. PROPOSITIONAL DETECTION METRICS
    #
    # Positive class = non_propositional
    #
    # TP = GT non_propositional, predicted non_propositional
    # FP = GT valid_claim, predicted non_propositional
    # FN = GT non_propositional, predicted valid_claim
    # TN = GT valid_claim, predicted valid_claim
    # ==========================================================

    tp = 0
    fp = 0
    fn = 0
    tn = 0
    provider_failed = 0

    case_rows: list[
        dict[str, str | int | float]
    ] = []

    # ==========================================================
    # 2. ATOMIZATION METRICS
    # ==========================================================

    valid_claim_count = 0

    class_correct = 0
    count_correct = 0
    type_sequence_correct = 0
    exact_structure_correct = 0

    expected_atoms_total = 0
    predicted_atoms_total = 0

    over_atomized_cases = 0
    under_atomized_cases = 0

    for holdout_id in sorted(
        gt_ids
    ):
        gt_case = gt_by_id[
            holdout_id
        ]

        pred_case = pred_by_id[
            holdout_id
        ]

        gt_status = get_gt_status(
            gt_case
        )

        pred_status = get_pred_status(
            pred_case
        )

        detection_result = ""

        if (
            pred_status
            == "provider_failed"
        ):
            provider_failed += 1
            detection_result = (
                "provider_failed"
            )

        elif (
            gt_status
            == "non_propositional"
            and pred_status
            == "non_propositional"
        ):
            tp += 1
            detection_result = "TP"

        elif (
            gt_status
            == "valid_claim"
            and pred_status
            == "non_propositional"
        ):
            fp += 1
            detection_result = "FP"

        elif (
            gt_status
            == "non_propositional"
            and pred_status
            == "valid_claim"
        ):
            fn += 1
            detection_result = "FN"

        elif (
            gt_status
            == "valid_claim"
            and pred_status
            == "valid_claim"
        ):
            tn += 1
            detection_result = "TN"

        else:
            raise RuntimeError(
                f"{holdout_id}: unexpected "
                "status combination "
                f"GT={gt_status}, "
                f"PRED={pred_status}"
            )

        gt_class = ""
        pred_class = ""

        expected_atom_count = 0
        predicted_atom_count = 0

        gt_type_sequence = ""
        pred_type_sequence = ""

        class_match = ""
        count_match = ""
        type_sequence_match = ""
        exact_structure_match = ""

        atom_delta = ""

        if (
            gt_status
            == "valid_claim"
        ):
            valid_claim_count += 1

            gt_atoms = get_gt_atoms(
                gt_case
            )

            pred_atoms = get_pred_atoms(
                pred_case
            )

            gt_class = get_gt_class(
                gt_case
            )

            pred_class = get_pred_class(
                pred_case
            )

            expected_atom_count = len(
                gt_atoms
            )

            predicted_atom_count = len(
                pred_atoms
            )

            expected_atoms_total += (
                expected_atom_count
            )

            predicted_atoms_total += (
                predicted_atom_count
            )

            class_is_correct = (
                pred_status
                == "valid_claim"
                and pred_class
                == gt_class
            )

            count_is_correct = (
                pred_status
                == "valid_claim"
                and predicted_atom_count
                == expected_atom_count
            )

            gt_types = [
                row["atom_type"]
                for row in gt_atoms
            ]

            pred_types = [
                row[
                    "predicted_atom_type"
                ]
                for row in pred_atoms
            ]

            gt_type_sequence = (
                " > ".join(
                    gt_types
                )
            )

            pred_type_sequence = (
                " > ".join(
                    pred_types
                )
            )

            type_sequence_is_correct = (
                pred_status
                == "valid_claim"
                and pred_types
                == gt_types
            )

            exact_structure_is_correct = (
                class_is_correct
                and count_is_correct
                and type_sequence_is_correct
            )

            if class_is_correct:
                class_correct += 1

            if count_is_correct:
                count_correct += 1

            if type_sequence_is_correct:
                type_sequence_correct += 1

            if exact_structure_is_correct:
                exact_structure_correct += 1

            delta = (
                predicted_atom_count
                - expected_atom_count
            )

            atom_delta = delta

            if delta > 0:
                over_atomized_cases += 1

            elif delta < 0:
                under_atomized_cases += 1

            class_match = int(
                class_is_correct
            )

            count_match = int(
                count_is_correct
            )

            type_sequence_match = int(
                type_sequence_is_correct
            )

            exact_structure_match = int(
                exact_structure_is_correct
            )

        case_rows.append(
            {
                "holdout_id": holdout_id,
                "gt_review_status": (
                    gt_status
                ),
                "predicted_review_status": (
                    pred_status
                ),
                "detection_result": (
                    detection_result
                ),
                "gt_class": (
                    gt_class
                ),
                "predicted_class": (
                    pred_class
                ),
                "expected_atom_count": (
                    expected_atom_count
                ),
                "predicted_atom_count": (
                    predicted_atom_count
                ),
                "atom_delta": (
                    atom_delta
                ),
                "gt_type_sequence": (
                    gt_type_sequence
                ),
                "predicted_type_sequence": (
                    pred_type_sequence
                ),
                "class_match": (
                    class_match
                ),
                "count_match": (
                    count_match
                ),
                "type_sequence_match": (
                    type_sequence_match
                ),
                "exact_structure_match": (
                    exact_structure_match
                ),
            }
        )

    # ==========================================================
    # Detection metrics
    # ==========================================================

    evaluated_detection = (
        tp + fp + fn + tn
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

    detection_accuracy = safe_divide(
        tp + tn,
        evaluated_detection,
    )

    detection_coverage = safe_divide(
        evaluated_detection,
        len(gt_ids),
    )

    # ==========================================================
    # Atomization metrics
    # ==========================================================

    class_accuracy = safe_divide(
        class_correct,
        valid_claim_count,
    )

    count_accuracy = safe_divide(
        count_correct,
        valid_claim_count,
    )

    type_sequence_accuracy = (
        safe_divide(
            type_sequence_correct,
            valid_claim_count,
        )
    )

    exact_structure_accuracy = (
        safe_divide(
            exact_structure_correct,
            valid_claim_count,
        )
    )

    atom_delta_total = (
        predicted_atoms_total
        - expected_atoms_total
    )

    atom_inflation_rate = (
        safe_divide(
            atom_delta_total,
            expected_atoms_total,
        )
    )

    # ==========================================================
    # Write case-level output
    # ==========================================================

    OUTPUT_CASES.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    case_fieldnames = [
        "holdout_id",
        "gt_review_status",
        "predicted_review_status",
        "detection_result",
        "gt_class",
        "predicted_class",
        "expected_atom_count",
        "predicted_atom_count",
        "atom_delta",
        "gt_type_sequence",
        "predicted_type_sequence",
        "class_match",
        "count_match",
        "type_sequence_match",
        "exact_structure_match",
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
            case_rows
        )

    # ==========================================================
    # Flat metrics CSV
    # ==========================================================

    metrics = [
        (
            "holdout_items",
            len(gt_ids),
        ),
        (
            "valid_claims",
            valid_claim_count,
        ),
        (
            "non_propositional_gt",
            sum(
                1
                for rows
                in gt_by_id.values()
                if get_gt_status(
                    rows
                )
                == "non_propositional"
            ),
        ),
        (
            "provider_failed",
            provider_failed,
        ),
        (
            "detection_tp",
            tp,
        ),
        (
            "detection_fp",
            fp,
        ),
        (
            "detection_fn",
            fn,
        ),
        (
            "detection_tn",
            tn,
        ),
        (
            "detection_precision",
            round(
                precision,
                4,
            ),
        ),
        (
            "detection_recall",
            round(
                recall,
                4,
            ),
        ),
        (
            "detection_specificity",
            round(
                specificity,
                4,
            ),
        ),
        (
            "detection_accuracy",
            round(
                detection_accuracy,
                4,
            ),
        ),
        (
            "detection_coverage",
            round(
                detection_coverage,
                4,
            ),
        ),
        (
            "expected_atoms",
            expected_atoms_total,
        ),
        (
            "predicted_atoms",
            predicted_atoms_total,
        ),
        (
            "atom_delta",
            atom_delta_total,
        ),
        (
            "atom_inflation_rate",
            round(
                atom_inflation_rate,
                4,
            ),
        ),
        (
            "class_accuracy",
            round(
                class_accuracy,
                4,
            ),
        ),
        (
            "count_accuracy",
            round(
                count_accuracy,
                4,
            ),
        ),
        (
            "type_sequence_accuracy",
            round(
                type_sequence_accuracy,
                4,
            ),
        ),
        (
            "exact_structure_accuracy",
            round(
                exact_structure_accuracy,
                4,
            ),
        ),
        (
            "over_atomized_cases",
            over_atomized_cases,
        ),
        (
            "under_atomized_cases",
            under_atomized_cases,
        ),
    ]

    with OUTPUT_METRICS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "metric",
                "value",
            ]
        )

        writer.writerows(
            metrics
        )

    # ==========================================================
    # JSON summary
    # ==========================================================

    summary = {
        "version": (
            "claim-atomizer-v0.4"
        ),
        "holdout": (
            "atomization-holdout-v1"
        ),
        "methodology": {
            "holdout_frozen_before_v0_4_run": True,
            "prompt_modified_after_holdout_run": False,
            "gemini_calls_during_evaluation_script": False,
            "primary_atomization_scope": (
                "human-valid claims only"
            ),
            "detection_positive_class": (
                "non_propositional"
            ),
        },
        "counts": {
            "holdout_items": (
                len(gt_ids)
            ),
            "valid_claims": (
                valid_claim_count
            ),
            "expected_atoms": (
                expected_atoms_total
            ),
            "predicted_atoms": (
                predicted_atoms_total
            ),
            "provider_failed": (
                provider_failed
            ),
        },
        "propositional_detection": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(
                precision,
                4,
            ),
            "recall": round(
                recall,
                4,
            ),
            "specificity": round(
                specificity,
                4,
            ),
            "accuracy": round(
                detection_accuracy,
                4,
            ),
            "coverage": round(
                detection_coverage,
                4,
            ),
        },
        "atomization": {
            "class_accuracy": round(
                class_accuracy,
                4,
            ),
            "count_accuracy": round(
                count_accuracy,
                4,
            ),
            "type_sequence_accuracy": round(
                type_sequence_accuracy,
                4,
            ),
            "exact_structure_accuracy": round(
                exact_structure_accuracy,
                4,
            ),
            "atom_delta": (
                atom_delta_total
            ),
            "atom_inflation_rate": round(
                atom_inflation_rate,
                4,
            ),
            "over_atomized_cases": (
                over_atomized_cases
            ),
            "under_atomized_cases": (
                under_atomized_cases
            ),
        },
    }

    OUTPUT_SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ==========================================================
    # Console report
    # ==========================================================

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION HOLDOUT V1 "
        "— v0.4 EVALUATION"
    )
    print("=" * 88)

    print()
    print(
        "PROPOSITIONAL DETECTION"
    )
    print("-" * 44)

    print(
        "Positive class: "
        "non_propositional"
    )

    print(
        f"TP = {tp}"
    )

    print(
        f"FP = {fp}"
    )

    print(
        f"FN = {fn}"
    )

    print(
        f"TN = {tn}"
    )

    print(
        f"Precision = "
        f"{precision:.4f}"
    )

    print(
        f"Recall = "
        f"{recall:.4f}"
    )

    print(
        f"Specificity = "
        f"{specificity:.4f}"
    )

    print(
        f"Accuracy = "
        f"{detection_accuracy:.4f}"
    )

    print(
        f"Coverage = "
        f"{detection_coverage:.4f}"
    )

    print()
    print(
        "ATOMIZATION — VALID CLAIMS ONLY"
    )
    print("-" * 44)

    print(
        f"Valid claims = "
        f"{valid_claim_count}"
    )

    print(
        f"Expected atoms = "
        f"{expected_atoms_total}"
    )

    print(
        f"Predicted atoms = "
        f"{predicted_atoms_total}"
    )

    print(
        f"Atom delta = "
        f"{atom_delta_total}"
    )

    print(
        f"Atom inflation rate = "
        f"{atom_inflation_rate:.4f}"
    )

    print(
        f"Class accuracy = "
        f"{class_accuracy:.4f}"
    )

    print(
        f"Count accuracy = "
        f"{count_accuracy:.4f}"
    )

    print(
        f"Type sequence accuracy = "
        f"{type_sequence_accuracy:.4f}"
    )

    print(
        f"Exact structure accuracy = "
        f"{exact_structure_accuracy:.4f}"
    )

    print(
        f"Over-atomized cases = "
        f"{over_atomized_cases}"
    )

    print(
        f"Under-atomized cases = "
        f"{under_atomized_cases}"
    )

    print()
    print(
        "OUTPUTS"
    )
    print("-" * 44)

    print(
        "Cases:",
        OUTPUT_CASES,
    )

    print(
        "Metrics:",
        OUTPUT_METRICS,
    )

    print(
        "Summary:",
        OUTPUT_SUMMARY,
    )


if __name__ == "__main__":
    main()