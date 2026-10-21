"""Evaluate frozen Claim Atomizer v0.4 against final_eval_v1 GT.

This is the first formal comparison between:

- frozen v0.4 predictions;
- frozen blind human ground truth.

Metric groups
-------------
1. Propositional detection over all final-eval items.
   Positive class = non_propositional.

2. Atomization structure over human-valid claims:
   - class accuracy
   - atom-count accuracy
   - atom-type-sequence accuracy
   - exact-structure accuracy
   - over/under atomization
   - atom delta / inflation

3. Provider execution metadata:
   - first-attempt completion
   - retry completion
   - final completion

Important
---------
- no Gemini calls;
- no prompt changes;
- no GT changes;
- atom text is NOT compared literally because semantically equivalent
  paraphrases are allowed;
- exact structure means class + count + atom-type sequence.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1/final_eval_v1"
)

GT_FILE = (
    BASE_DIR
    / "atomization_final_eval_ground_truth_v1.csv"
)

PREDICTIONS_FILE = (
    BASE_DIR
    / "results"
    / "atomization_final_eval_predictions_v0_4.csv"
)

ATTEMPT1_FILE = (
    BASE_DIR
    / "results"
    / "atomization_final_eval_predictions_v0_4_attempt1.csv"
)

RETRY_LOG_FILE = (
    BASE_DIR
    / "results"
    / "atomization_final_eval_retry_log_v0_4.csv"
)

OUTPUT_CASES = (
    BASE_DIR
    / "results"
    / "atomization_final_eval_evaluation_cases_v0_4.csv"
)

OUTPUT_METRICS = (
    BASE_DIR
    / "results"
    / "atomization_final_eval_evaluation_metrics_v0_4.csv"
)

OUTPUT_SUMMARY = (
    BASE_DIR
    / "results"
    / "atomization_final_eval_evaluation_summary_v0_4.json"
)


EXPECTED_ITEMS = 23


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


def get_single_value(
    rows: list[dict[str, str]],
    field: str,
    *,
    allow_empty: bool = False,
) -> str:
    values = {
        row[field].strip()
        for row in rows
    }

    if allow_empty:
        values.discard("")

    if not values:
        return ""

    if len(values) != 1:
        raise RuntimeError(
            f"Inconsistent {field}: "
            f"{sorted(values)}"
        )

    return next(
        iter(values)
    )


def get_gt_status(
    rows: list[dict[str, str]],
) -> str:
    return get_single_value(
        rows,
        "review_status",
    )


def get_pred_status(
    rows: list[dict[str, str]],
) -> str:
    successful_rows = [
        row
        for row in rows
        if row["status"] == "success"
    ]

    if not successful_rows:
        return "provider_failed"

    return get_single_value(
        successful_rows,
        "predicted_review_status",
    )


def get_gt_class(
    rows: list[dict[str, str]],
) -> str:
    valid_rows = [
        row
        for row in rows
        if row["review_status"]
        == "valid_claim"
    ]

    if not valid_rows:
        return ""

    return get_single_value(
        valid_rows,
        "atomization_class",
    )


def get_pred_class(
    rows: list[dict[str, str]],
) -> str:
    valid_rows = [
        row
        for row in rows
        if (
            row["status"] == "success"
            and row[
                "predicted_review_status"
            ]
            == "valid_claim"
        )
    ]

    if not valid_rows:
        return ""

    return get_single_value(
        valid_rows,
        "predicted_class",
    )


def get_gt_atoms(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    atoms = [
        row
        for row in rows
        if (
            row["review_status"]
            == "valid_claim"
            and row["atom_text"].strip()
        )
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
            row["status"] == "success"
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
            row["predicted_atom_order"]
        ),
    )


def count_successful_unique_ids(
    rows: list[dict[str, str]],
) -> int:
    return len(
        {
            row["final_eval_id"]
            for row in rows
            if row["status"]
            == "success"
        }
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
        id_field="final_eval_id",
    )

    pred_by_id = group_rows(
        prediction_rows,
        id_field="final_eval_id",
    )

    gt_ids = set(
        gt_by_id
    )

    pred_ids = set(
        pred_by_id
    )

    if len(gt_ids) != EXPECTED_ITEMS:
        raise RuntimeError(
            "Expected "
            f"{EXPECTED_ITEMS} GT items, "
            f"found {len(gt_ids)}."
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
    # Provider execution metadata
    # ==========================================================

    first_attempt_success = None
    first_attempt_failed = None
    retry_success = None
    retry_failed = None

    if ATTEMPT1_FILE.exists():
        attempt1_rows = load_csv(
            ATTEMPT1_FILE
        )

        first_attempt_success = (
            count_successful_unique_ids(
                attempt1_rows
            )
        )

        first_attempt_ids = {
            row["final_eval_id"]
            for row in attempt1_rows
        }

        first_attempt_failed = (
            len(first_attempt_ids)
            - first_attempt_success
        )

    if RETRY_LOG_FILE.exists():
        retry_rows = load_csv(
            RETRY_LOG_FILE
        )

        retry_success = len(
            {
                row["final_eval_id"]
                for row in retry_rows
                if row["status"]
                == "success"
            }
        )

        retry_failed = len(
            {
                row["final_eval_id"]
                for row in retry_rows
                if row["status"]
                == "failed"
            }
        )

    # ==========================================================
    # Detection
    #
    # Positive class = non_propositional
    # ==========================================================

    tp = 0
    fp = 0
    fn = 0
    tn = 0
    provider_failed = 0

    # ==========================================================
    # Structural evaluation
    # ==========================================================

    valid_claim_count = 0
    structurally_evaluable = 0

    class_correct = 0
    count_correct = 0
    type_sequence_correct = 0
    exact_structure_correct = 0

    expected_atoms_total = 0
    predicted_atoms_total = 0

    over_atomized_cases = 0
    under_atomized_cases = 0

    case_rows: list[
        dict[str, str | int]
    ] = []

    for final_eval_id in sorted(
        gt_ids
    ):
        gt_case = gt_by_id[
            final_eval_id
        ]

        pred_case = pred_by_id[
            final_eval_id
        ]

        gt_status = get_gt_status(
            gt_case
        )

        pred_status = get_pred_status(
            pred_case
        )

        # ------------------------------------------------------
        # Detection confusion matrix
        # ------------------------------------------------------

        if pred_status == "provider_failed":
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
                f"{final_eval_id}: "
                "unexpected status combination "
                f"GT={gt_status}, "
                f"PRED={pred_status}"
            )

        gt_class = ""
        pred_class = ""

        expected_atom_count = 0
        predicted_atom_count = 0

        gt_type_sequence = ""
        pred_type_sequence = ""

        class_match: str | int = ""
        count_match: str | int = ""
        type_sequence_match: str | int = ""
        exact_structure_match: str | int = ""

        atom_delta: str | int = ""

        # ------------------------------------------------------
        # Structure: human-valid claims only
        # ------------------------------------------------------

        if gt_status == "valid_claim":
            valid_claim_count += 1

            gt_atoms = get_gt_atoms(
                gt_case
            )

            expected_atom_count = len(
                gt_atoms
            )

            expected_atoms_total += (
                expected_atom_count
            )

            gt_class = get_gt_class(
                gt_case
            )

            gt_types = [
                row["atom_type"]
                for row in gt_atoms
            ]

            gt_type_sequence = (
                " > ".join(
                    gt_types
                )
            )

            if pred_status == "valid_claim":
                structurally_evaluable += 1

                pred_atoms = get_pred_atoms(
                    pred_case
                )

                predicted_atom_count = len(
                    pred_atoms
                )

                predicted_atoms_total += (
                    predicted_atom_count
                )

                pred_class = get_pred_class(
                    pred_case
                )

                pred_types = [
                    row[
                        "predicted_atom_type"
                    ]
                    for row in pred_atoms
                ]

                pred_type_sequence = (
                    " > ".join(
                        pred_types
                    )
                )

                class_is_correct = (
                    pred_class
                    == gt_class
                )

                count_is_correct = (
                    predicted_atom_count
                    == expected_atom_count
                )

                type_sequence_is_correct = (
                    pred_types
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

            else:
                # A human-valid claim predicted as
                # non-propositional is a detection FP.
                # It is not structurally evaluable.
                predicted_atom_count = 0
                atom_delta = (
                    -expected_atom_count
                )

        case_rows.append(
            {
                "final_eval_id": (
                    final_eval_id
                ),
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

    detection_precision = safe_divide(
        tp,
        tp + fp,
    )

    detection_recall = safe_divide(
        tp,
        tp + fn,
    )

    detection_specificity = safe_divide(
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
    # Structural metrics
    #
    # Denominator deliberately = all human-valid claims.
    # A valid claim incorrectly rejected as non-propositional
    # therefore does NOT silently disappear from quality metrics.
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

    structural_coverage = safe_divide(
        structurally_evaluable,
        valid_claim_count,
    )

    atom_delta_total = (
        predicted_atoms_total
        - expected_atoms_total
    )

    atom_inflation_rate = safe_divide(
        atom_delta_total,
        expected_atoms_total,
    )

    # ==========================================================
    # Persist case-level output
    # ==========================================================

    OUTPUT_CASES.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    case_fieldnames = [
        "final_eval_id",
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
    # Flat metrics
    # ==========================================================

    metrics = [
        (
            "final_eval_items",
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
                if get_gt_status(rows)
                == "non_propositional"
            ),
        ),
        (
            "provider_failed_final",
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
                detection_precision,
                4,
            ),
        ),
        (
            "detection_recall",
            round(
                detection_recall,
                4,
            ),
        ),
        (
            "detection_specificity",
            round(
                detection_specificity,
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
            "structural_evaluable_claims",
            structurally_evaluable,
        ),
        (
            "structural_coverage",
            round(
                structural_coverage,
                4,
            ),
        ),
        (
            "expected_atoms",
            expected_atoms_total,
        ),
        (
            "predicted_atoms_on_gt_valid",
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

    if first_attempt_success is not None:
        metrics.extend(
            [
                (
                    "first_attempt_success",
                    first_attempt_success,
                ),
                (
                    "first_attempt_failed",
                    first_attempt_failed,
                ),
                (
                    "first_attempt_completion_rate",
                    round(
                        safe_divide(
                            first_attempt_success,
                            EXPECTED_ITEMS,
                        ),
                        4,
                    ),
                ),
            ]
        )

    if retry_success is not None:
        metrics.extend(
            [
                (
                    "retry_success",
                    retry_success,
                ),
                (
                    "retry_failed",
                    retry_failed,
                ),
            ]
        )

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
        "candidate": (
            "claim-atomizer-v0.4"
        ),
        "evaluation_set": (
            "atomization-final-eval-v1"
        ),
        "methodology": {
            "candidate_frozen_before_final_eval": True,
            "predictions_frozen_before_human_gt": True,
            "human_gt_blind_to_predictions": True,
            "gemini_calls_during_evaluation": False,
            "detection_positive_class": (
                "non_propositional"
            ),
            "exact_structure_definition": (
                "class + atom count + "
                "atom-type sequence"
            ),
            "literal_atom_text_match_used": False,
            "structural_metric_denominator": (
                "all human-valid claims"
            ),
        },
        "counts": {
            "final_eval_items": (
                len(gt_ids)
            ),
            "valid_claims": (
                valid_claim_count
            ),
            "non_propositional": (
                len(gt_ids)
                - valid_claim_count
            ),
            "expected_atoms": (
                expected_atoms_total
            ),
            "predicted_atoms_on_gt_valid": (
                predicted_atoms_total
            ),
            "provider_failed_final": (
                provider_failed
            ),
        },
        "propositional_detection": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(
                detection_precision,
                4,
            ),
            "recall": round(
                detection_recall,
                4,
            ),
            "specificity": round(
                detection_specificity,
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
        "atomization_structure": {
            "structurally_evaluable_claims": (
                structurally_evaluable
            ),
            "structural_coverage": round(
                structural_coverage,
                4,
            ),
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
        "provider_execution": {
            "first_attempt_success": (
                first_attempt_success
            ),
            "first_attempt_failed": (
                first_attempt_failed
            ),
            "retry_success": (
                retry_success
            ),
            "retry_failed": (
                retry_failed
            ),
            "final_successful_items": (
                EXPECTED_ITEMS
                - provider_failed
            ),
            "final_completion_rate": round(
                safe_divide(
                    EXPECTED_ITEMS
                    - provider_failed,
                    EXPECTED_ITEMS,
                ),
                4,
            ),
        },
        "limitations": [
            (
                "Internal evaluation set derived from the "
                "same 59-claim calibration corpus."
            ),
            (
                "Final GT is highly imbalanced: "
                "13 atomic claims, 1 compound claim, "
                "0 relational claims."
            ),
            (
                "All 15 GT atoms are factual_proposition, "
                "so this set does not test generalization "
                "across atom types."
            ),
            (
                "Seven provider failures occurred on the "
                "first execution and were completed in a "
                "targeted second attempt without changing "
                "the candidate."
            ),
        ],
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
    # Console
    # ==========================================================

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION FINAL EVAL V1 "
        "— v0.4"
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

    print(f"TP = {tp}")
    print(f"FP = {fp}")
    print(f"FN = {fn}")
    print(f"TN = {tn}")

    print(
        f"Precision = "
        f"{detection_precision:.4f}"
    )

    print(
        f"Recall = "
        f"{detection_recall:.4f}"
    )

    print(
        f"Specificity = "
        f"{detection_specificity:.4f}"
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
        "ATOMIZATION — HUMAN-VALID CLAIMS"
    )
    print("-" * 44)

    print(
        f"Valid claims = "
        f"{valid_claim_count}"
    )

    print(
        f"Structurally evaluable = "
        f"{structurally_evaluable}"
    )

    print(
        f"Structural coverage = "
        f"{structural_coverage:.4f}"
    )

    print(
        f"Expected atoms = "
        f"{expected_atoms_total}"
    )

    print(
        "Predicted atoms on GT-valid "
        f"claims = {predicted_atoms_total}"
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
        "Type sequence accuracy = "
        f"{type_sequence_accuracy:.4f}"
    )

    print(
        "Exact structure accuracy = "
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
        "PROVIDER EXECUTION"
    )
    print("-" * 44)

    if first_attempt_success is not None:
        print(
            "First attempt = "
            f"{first_attempt_success}/"
            f"{EXPECTED_ITEMS}"
        )

    if retry_success is not None:
        print(
            "Retry recovered = "
            f"{retry_success}"
        )

    print(
        "Final completed = "
        f"{EXPECTED_ITEMS - provider_failed}/"
        f"{EXPECTED_ITEMS}"
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