"""Evaluate frozen Claim Atomizer v0.4 on external validation v1.

This script compares:
- frozen external human Ground Truth;
- frozen Claim Atomizer v0.4 predictions.

Methodological constraints:
- no Gemini calls are made here;
- the candidate is not modified;
- Ground Truth was frozen before predictions;
- predictions were frozen before this comparison;
- literal atom-text equality is NOT used as a structural metric;
- structural metrics use all human-valid claims as denominator;
- non_propositional is the positive class for detection;
- provider reliability is reported separately from model quality.

Internal Test A criteria:
- exact structure accuracy >= 0.90
- count accuracy >= 0.95
- non-propositional recall >= 0.85
- non-propositional precision >= 0.90
- detection coverage >= 0.95
- no obvious systematic over/under-atomization

These thresholds are internal experiment criteria, not production SLAs.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

GROUND_TRUTH_CASES_FILE = (
    BASE_DIR
    / "ground_truth"
    / "external_atom_ground_truth_cases_v1.csv"
)

GROUND_TRUTH_ATOMS_FILE = (
    BASE_DIR
    / "ground_truth"
    / "external_atom_ground_truth_atoms_v1.csv"
)

RESULTS_DIR = (
    BASE_DIR
    / "results"
)

PREDICTIONS_FILE = (
    RESULTS_DIR
    / "atomization_external_predictions_v0_4.csv"
)

ATTEMPT1_FILE = (
    RESULTS_DIR
    / "atomization_external_predictions_attempt1_v0_4.csv"
)

RETRY_LOG_FILE = (
    RESULTS_DIR
    / "atomization_external_retry_log_v0_4.csv"
)

OUTPUT_CASES = (
    RESULTS_DIR
    / "atomization_external_evaluation_cases_v0_4.csv"
)

OUTPUT_METRICS = (
    RESULTS_DIR
    / "atomization_external_evaluation_metrics_v0_4.csv"
)

OUTPUT_SUMMARY = (
    RESULTS_DIR
    / "atomization_external_evaluation_summary_v0_4.json"
)


EXPECTED_ITEMS = 80

EXPECTED_VALID_CLAIMS = 60

EXPECTED_NON_PROPOSITIONAL = 20

EXPECTED_GT_ATOMS = 88


THRESHOLDS = {
    "exact_structure_accuracy": 0.90,
    "count_accuracy": 0.95,
    "non_propositional_recall": 0.85,
    "non_propositional_precision": 0.90,
    "detection_coverage": 0.95,
}


VALID_TARGET_BUCKETS = {
    "atomic",
    "compound",
    "relational",
    "non_propositional",
}


def load_csv(
    path: Path,
) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
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

    return (
        numerator
        / denominator
    )


def group_rows(
    rows: list[dict[str, str]],
    key: str,
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[
        str,
        list[dict[str, str]]
    ] = defaultdict(list)

    for row in rows:
        grouped[
            row[key]
        ].append(
            row
        )

    return dict(
        grouped
    )


def parse_int(
    value: str,
    *,
    field_name: str,
    case_id: str,
) -> int:
    try:
        return int(
            str(value).strip()
        )
    except ValueError as exc:
        raise RuntimeError(
            f"{case_id}: invalid integer "
            f"for {field_name}: {value!r}"
        ) from exc


def validate_ground_truth(
    case_rows: list[dict[str, str]],
    atom_rows: list[dict[str, str]],
) -> None:
    if len(case_rows) != EXPECTED_ITEMS:
        raise RuntimeError(
            f"Expected {EXPECTED_ITEMS} GT cases, "
            f"found {len(case_rows)}."
        )

    case_ids = [
        row["external_case_id"]
        for row in case_rows
    ]

    if len(
        set(case_ids)
    ) != EXPECTED_ITEMS:
        raise RuntimeError(
            "Ground Truth case IDs are not unique."
        )

    invalid_buckets = {
        row["target_bucket"]
        for row in case_rows
        if row["target_bucket"]
        not in VALID_TARGET_BUCKETS
    }

    if invalid_buckets:
        raise RuntimeError(
            "Unexpected Ground Truth target buckets: "
            + ", ".join(
                sorted(
                    invalid_buckets
                )
            )
        )

    if any(
        row["gt_review_status"]
        != "reviewed"
        for row in case_rows
    ):
        raise RuntimeError(
            "Ground Truth contains non-reviewed cases."
        )

    valid_claims = sum(
        1
        for row in case_rows
        if row["target_bucket"]
        != "non_propositional"
    )

    non_prop = sum(
        1
        for row in case_rows
        if row["target_bucket"]
        == "non_propositional"
    )

    if valid_claims != EXPECTED_VALID_CLAIMS:
        raise RuntimeError(
            "Unexpected number of human-valid claims. "
            f"Expected {EXPECTED_VALID_CLAIMS}, "
            f"found {valid_claims}."
        )

    if non_prop != EXPECTED_NON_PROPOSITIONAL:
        raise RuntimeError(
            "Unexpected number of "
            "non-propositional GT cases. "
            f"Expected {EXPECTED_NON_PROPOSITIONAL}, "
            f"found {non_prop}."
        )

    expected_atom_total = sum(
        parse_int(
            row["expected_atom_count"],
            field_name=(
                "expected_atom_count"
            ),
            case_id=(
                row["external_case_id"]
            ),
        )
        for row in case_rows
    )

    if expected_atom_total != EXPECTED_GT_ATOMS:
        raise RuntimeError(
            f"Expected {EXPECTED_GT_ATOMS} GT atoms "
            "from case counts, "
            f"found {expected_atom_total}."
        )

    if len(atom_rows) != EXPECTED_GT_ATOMS:
        raise RuntimeError(
            f"Expected {EXPECTED_GT_ATOMS} atom rows, "
            f"found {len(atom_rows)}."
        )


def validate_predictions(
    prediction_rows: list[dict[str, str]],
    gt_ids: set[str],
) -> None:
    prediction_ids = {
        row["external_case_id"]
        for row in prediction_rows
    }

    missing_ids = (
        gt_ids
        - prediction_ids
    )

    unexpected_ids = (
        prediction_ids
        - gt_ids
    )

    if missing_ids:
        raise RuntimeError(
            "Predictions missing GT cases: "
            + ", ".join(
                sorted(
                    missing_ids
                )
            )
        )

    if unexpected_ids:
        raise RuntimeError(
            "Predictions contain unknown cases: "
            + ", ".join(
                sorted(
                    unexpected_ids
                )
            )
        )

    final_failed = {
        row["external_case_id"]
        for row in prediction_rows
        if row["status"]
        == "failed"
    }

    if final_failed:
        print(
            "WARNING:"
        )
        print(
            "Final predictions still contain "
            f"{len(final_failed)} provider failures."
        )


def get_gt_status(
    case_row: dict[str, str],
) -> str:
    bucket = (
        case_row[
            "target_bucket"
        ].strip()
    )

    if bucket == "non_propositional":
        return "non_propositional"

    return "valid_claim"


def get_gt_class(
    case_row: dict[str, str],
) -> str:
    bucket = (
        case_row[
            "target_bucket"
        ].strip()
    )

    if bucket == "non_propositional":
        return ""

    return bucket


def get_gt_atoms(
    external_case_id: str,
    atoms_by_id: dict[
        str,
        list[dict[str, str]]
    ],
) -> list[dict[str, str]]:
    rows = list(
        atoms_by_id.get(
            external_case_id,
            [],
        )
    )

    def atom_order(
        row: dict[str, str],
    ) -> int:
        return parse_int(
            row["atom_index"],
            field_name="atom_index",
            case_id=external_case_id,
        )

    return sorted(
        rows,
        key=atom_order,
    )


def get_pred_status(
    prediction_rows: list[
        dict[str, str]
    ],
) -> str:
    statuses = {
        row["status"]
        for row in prediction_rows
    }

    if "failed" in statuses:
        if statuses != {"failed"}:
            raise RuntimeError(
                "Prediction case mixes failed "
                "and successful rows."
            )

        return "provider_failed"

    review_statuses = {
        row["predicted_review_status"]
        for row in prediction_rows
    }

    if len(review_statuses) != 1:
        raise RuntimeError(
            "Prediction case contains multiple "
            "review statuses."
        )

    review_status = next(
        iter(
            review_statuses
        )
    )

    if review_status not in {
        "valid_claim",
        "non_propositional",
    }:
        raise RuntimeError(
            "Unexpected predicted review status: "
            f"{review_status!r}"
        )

    return review_status


def get_pred_class(
    prediction_rows: list[
        dict[str, str]
    ],
) -> str:
    classes = {
        row["predicted_class"]
        for row in prediction_rows
        if row["status"]
        == "success"
    }

    if len(classes) != 1:
        raise RuntimeError(
            "Prediction case contains multiple "
            "predicted classes."
        )

    return next(
        iter(
            classes
        )
    )


def get_pred_atoms(
    prediction_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    atoms = [
        row
        for row in prediction_rows
        if (
            row["status"]
            == "success"
            and row[
                "predicted_review_status"
            ]
            == "valid_claim"
            and row[
                "predicted_atom_type"
            ].strip()
        )
    ]

    def atom_order(
        row: dict[str, str],
    ) -> int:
        return parse_int(
            row["predicted_atom_order"],
            field_name=(
                "predicted_atom_order"
            ),
            case_id=(
                row["external_case_id"]
            ),
        )

    return sorted(
        atoms,
        key=atom_order,
    )


def count_successful_unique_ids(
    rows: list[dict[str, str]],
) -> int:
    return len(
        {
            row["external_case_id"]
            for row in rows
            if row["status"]
            == "success"
        }
    )


def main() -> None:
    gt_cases = load_csv(
        GROUND_TRUTH_CASES_FILE
    )

    gt_atoms = load_csv(
        GROUND_TRUTH_ATOMS_FILE
    )

    predictions = load_csv(
        PREDICTIONS_FILE
    )

    validate_ground_truth(
        gt_cases,
        gt_atoms,
    )

    gt_case_by_id = {
        row["external_case_id"]: row
        for row in gt_cases
    }

    gt_ids = set(
        gt_case_by_id
    )

    atoms_by_id = group_rows(
        gt_atoms,
        "external_case_id",
    )

    pred_by_id = group_rows(
        predictions,
        "external_case_id",
    )

    validate_predictions(
        predictions,
        gt_ids,
    )

    # ==========================================================
    # Provider execution
    # ==========================================================

    first_attempt_success = None
    first_attempt_failed = None
    first_attempt_completion_rate = None

    retry_success = None
    retry_failed = None

    if ATTEMPT1_FILE.exists():
        attempt1_rows = load_csv(
            ATTEMPT1_FILE
        )

        attempt1_ids = {
            row["external_case_id"]
            for row in attempt1_rows
        }

        if len(attempt1_ids) != EXPECTED_ITEMS:
            raise RuntimeError(
                "Attempt-1 snapshot does not "
                f"contain {EXPECTED_ITEMS} unique cases."
            )

        first_attempt_success = (
            count_successful_unique_ids(
                attempt1_rows
            )
        )

        first_attempt_failed = (
            EXPECTED_ITEMS
            - first_attempt_success
        )

        first_attempt_completion_rate = (
            safe_divide(
                first_attempt_success,
                EXPECTED_ITEMS,
            )
        )

    if RETRY_LOG_FILE.exists():
        retry_rows = load_csv(
            RETRY_LOG_FILE
        )

        retry_success = sum(
            1
            for row in retry_rows
            if row["status"]
            == "success"
        )

        retry_failed = sum(
            1
            for row in retry_rows
            if row["status"]
            == "failed"
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
    #
    # Denominator = ALL human-valid claims.
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

    bucket_stats: dict[
        str,
        dict[str, int]
    ] = defaultdict(
        lambda: {
            "cases": 0,
            "class_correct": 0,
            "count_correct": 0,
            "type_correct": 0,
            "exact_correct": 0,
            "over": 0,
            "under": 0,
        }
    )

    for external_case_id in sorted(
        gt_ids
    ):
        gt_case = gt_case_by_id[
            external_case_id
        ]

        pred_case_rows = pred_by_id[
            external_case_id
        ]

        gt_status = get_gt_status(
            gt_case
        )

        pred_status = get_pred_status(
            pred_case_rows
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
                f"{external_case_id}: "
                "unexpected status combination "
                f"GT={gt_status}, "
                f"PRED={pred_status}"
            )

        target_bucket = (
            gt_case[
                "target_bucket"
            ]
        )

        relation_subtype = (
            gt_case.get(
                "relation_subtype",
                "",
            )
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
        # Structural evaluation
        # ------------------------------------------------------

        if gt_status == "valid_claim":
            valid_claim_count += 1

            bucket_stats[
                target_bucket
            ]["cases"] += 1

            gt_atom_rows = get_gt_atoms(
                external_case_id,
                atoms_by_id,
            )

            expected_atom_count = len(
                gt_atom_rows
            )

            expected_atoms_total += (
                expected_atom_count
            )

            gt_class = get_gt_class(
                gt_case
            )

            gt_types = [
                row["atom_type"]
                for row in gt_atom_rows
            ]

            gt_type_sequence = (
                " > ".join(
                    gt_types
                )
            )

            if pred_status == "valid_claim":
                structurally_evaluable += 1

                pred_atom_rows = (
                    get_pred_atoms(
                        pred_case_rows
                    )
                )

                predicted_atom_count = len(
                    pred_atom_rows
                )

                predicted_atoms_total += (
                    predicted_atom_count
                )

                pred_class = (
                    get_pred_class(
                        pred_case_rows
                    )
                )

                pred_types = [
                    row[
                        "predicted_atom_type"
                    ]
                    for row
                    in pred_atom_rows
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

                    bucket_stats[
                        target_bucket
                    ][
                        "class_correct"
                    ] += 1

                if count_is_correct:
                    count_correct += 1

                    bucket_stats[
                        target_bucket
                    ][
                        "count_correct"
                    ] += 1

                if type_sequence_is_correct:
                    type_sequence_correct += 1

                    bucket_stats[
                        target_bucket
                    ][
                        "type_correct"
                    ] += 1

                if exact_structure_is_correct:
                    exact_structure_correct += 1

                    bucket_stats[
                        target_bucket
                    ][
                        "exact_correct"
                    ] += 1

                delta = (
                    predicted_atom_count
                    - expected_atom_count
                )

                atom_delta = delta

                if delta > 0:
                    over_atomized_cases += 1

                    bucket_stats[
                        target_bucket
                    ][
                        "over"
                    ] += 1

                elif delta < 0:
                    under_atomized_cases += 1

                    bucket_stats[
                        target_bucket
                    ][
                        "under"
                    ] += 1

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

            elif (
                pred_status
                == "non_propositional"
            ):
                predicted_atom_count = 0

                atom_delta = (
                    -expected_atom_count
                )

                under_atomized_cases += 1

                bucket_stats[
                    target_bucket
                ][
                    "under"
                ] += 1

            else:
                # provider_failed
                predicted_atom_count = 0

        case_rows.append(
            {
                "external_case_id": (
                    external_case_id
                ),
                "source_domain": (
                    gt_case.get(
                        "source_domain",
                        "",
                    )
                ),
                "target_bucket": (
                    target_bucket
                ),
                "relation_subtype": (
                    relation_subtype
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
        EXPECTED_ITEMS,
    )

    # ==========================================================
    # Structural metrics
    # ==========================================================

    class_accuracy = safe_divide(
        class_correct,
        valid_claim_count,
    )

    count_accuracy = safe_divide(
        count_correct,
        valid_claim_count,
    )

    type_sequence_accuracy = safe_divide(
        type_sequence_correct,
        valid_claim_count,
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
    # Threshold evaluation
    # ==========================================================

    threshold_results = {
        "exact_structure_accuracy": (
            exact_structure_accuracy
            >= THRESHOLDS[
                "exact_structure_accuracy"
            ]
        ),
        "count_accuracy": (
            count_accuracy
            >= THRESHOLDS[
                "count_accuracy"
            ]
        ),
        "non_propositional_recall": (
            detection_recall
            >= THRESHOLDS[
                "non_propositional_recall"
            ]
        ),
        "non_propositional_precision": (
            detection_precision
            >= THRESHOLDS[
                "non_propositional_precision"
            ]
        ),
        "detection_coverage": (
            detection_coverage
            >= THRESHOLDS[
                "detection_coverage"
            ]
        ),
    }

    passed_thresholds = sum(
        1
        for value
        in threshold_results.values()
        if value
    )

    failed_thresholds = [
        name
        for name, passed
        in threshold_results.items()
        if not passed
    ]

    # "Systematic" is not reduced to one arbitrary threshold.
    # We expose over/under counts for human interpretation.
    if failed_thresholds:
        test_a_decision = (
            "INVESTIGATE"
        )
    else:
        test_a_decision = (
            "CONTINUE"
        )

    # ==========================================================
    # Bucket metrics
    # ==========================================================

    bucket_summary = {}

    for bucket in [
        "atomic",
        "compound",
        "relational",
    ]:
        stats = bucket_stats[
            bucket
        ]

        cases = stats["cases"]

        bucket_summary[
            bucket
        ] = {
            "cases": cases,
            "class_accuracy": round(
                safe_divide(
                    stats[
                        "class_correct"
                    ],
                    cases,
                ),
                4,
            ),
            "count_accuracy": round(
                safe_divide(
                    stats[
                        "count_correct"
                    ],
                    cases,
                ),
                4,
            ),
            "type_sequence_accuracy": round(
                safe_divide(
                    stats[
                        "type_correct"
                    ],
                    cases,
                ),
                4,
            ),
            "exact_structure_accuracy": round(
                safe_divide(
                    stats[
                        "exact_correct"
                    ],
                    cases,
                ),
                4,
            ),
            "over_atomized_cases": (
                stats["over"]
            ),
            "under_atomized_cases": (
                stats["under"]
            ),
        }

    # ==========================================================
    # Persist case-level evaluation
    # ==========================================================

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    case_fieldnames = [
        "external_case_id",
        "source_domain",
        "target_bucket",
        "relation_subtype",
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

    metrics: list[
        tuple[str, str | int | float]
    ] = [
        (
            "external_items",
            EXPECTED_ITEMS,
        ),
        (
            "valid_claims",
            valid_claim_count,
        ),
        (
            "non_propositional_gt",
            EXPECTED_NON_PROPOSITIONAL,
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
        (
            "test_a_thresholds_passed",
            passed_thresholds,
        ),
        (
            "test_a_thresholds_total",
            len(
                threshold_results
            ),
        ),
        (
            "test_a_decision",
            test_a_decision,
        ),
    ]

    if (
        first_attempt_success
        is not None
    ):
        metrics.extend(
            [
                (
                    "first_attempt_success",
                    first_attempt_success,
                ),
                (
                    "first_attempt_failed",
                    first_attempt_failed
                    if (
                        first_attempt_failed
                        is not None
                    )
                    else "",
                ),
                (
                    "first_attempt_completion_rate",
                    round(
                        first_attempt_completion_rate
                        or 0.0,
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
                    retry_failed
                    if retry_failed
                    is not None
                    else 0,
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
            "atomization-external-validation-v1"
        ),
        "methodology": {
            "candidate_frozen_before_external_evaluation": True,
            "external_dataset_frozen_before_ground_truth": True,
            "ground_truth_frozen_before_predictions": True,
            "predictions_frozen_before_evaluation": True,
            "gemini_calls_during_evaluation": False,
            "detection_positive_class": (
                "non_propositional"
            ),
            "literal_atom_text_match_used": False,
            "exact_structure_definition": (
                "class + atom count + "
                "atom-type sequence"
            ),
            "structural_metric_denominator": (
                "all human-valid claims"
            ),
            "content_format_metadata_used": (
                "external_documentation"
            ),
            "benchmark_sampling": (
                "deliberately balanced structural "
                "benchmark, not natural prevalence"
            ),
        },
        "counts": {
            "external_items": (
                EXPECTED_ITEMS
            ),
            "valid_claims": (
                valid_claim_count
            ),
            "non_propositional": (
                EXPECTED_NON_PROPOSITIONAL
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
            "expected_atoms": (
                expected_atoms_total
            ),
            "predicted_atoms": (
                predicted_atoms_total
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
        "bucket_performance": (
            bucket_summary
        ),
        "provider_execution": {
            "first_attempt_success": (
                first_attempt_success
            ),
            "first_attempt_failed": (
                first_attempt_failed
            ),
            "first_attempt_completion_rate": (
                round(
                    first_attempt_completion_rate,
                    4,
                )
                if (
                    first_attempt_completion_rate
                    is not None
                )
                else None
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
        "test_a": {
            "thresholds": (
                THRESHOLDS
            ),
            "results": {
                key: {
                    "passed": (
                        threshold_results[
                            key
                        ]
                    ),
                    "observed": (
                        round(
                            {
                                "exact_structure_accuracy": (
                                    exact_structure_accuracy
                                ),
                                "count_accuracy": (
                                    count_accuracy
                                ),
                                "non_propositional_recall": (
                                    detection_recall
                                ),
                                "non_propositional_precision": (
                                    detection_precision
                                ),
                                "detection_coverage": (
                                    detection_coverage
                                ),
                            }[
                                key
                            ],
                            4,
                        )
                    ),
                    "threshold": (
                        THRESHOLDS[
                            key
                        ]
                    ),
                }
                for key
                in threshold_results
            },
            "thresholds_passed": (
                passed_thresholds
            ),
            "thresholds_total": (
                len(
                    threshold_results
                )
            ),
            "failed_thresholds": (
                failed_thresholds
            ),
            "decision": (
                test_a_decision
            ),
            "note": (
                "Over/under-atomization is reported "
                "separately and requires pattern review; "
                "no arbitrary numeric threshold was added."
            ),
        },
        "limitations": [
            (
                "Benchmark is deliberately balanced across "
                "atomic, compound, relational, and "
                "non-propositional structural buckets."
            ),
            (
                "The benchmark therefore does not estimate "
                "natural production prevalence."
            ),
            (
                "Ground Truth was human-reviewed with "
                "assistant support rather than independently "
                "annotated by multiple blinded experts."
            ),
            (
                "The selected relational benchmark contains "
                "no scope_or_quantifier target case."
            ),
            (
                "Exact normalized textual overlap with the "
                "historical 59-case corpus is zero, but "
                "semantic near-duplicate independence was "
                "not formally measured."
            ),
            (
                "The inherited dataset format field was not "
                "a reliable content-format variable; the "
                "runner therefore used the constant neutral "
                "metadata value external_documentation."
            ),
            (
                "Provider reliability must be interpreted "
                "separately from atomization quality."
            ),
        ],
        "next_stage": (
            "Review Test A results and case-level failure "
            "patterns. If warranted, continue to stability/"
            "provider reliability Test B and content-support "
            "impact A/B Test C without tuning v0.4."
        ),
    }

    OUTPUT_SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # ==========================================================
    # Console
    # ==========================================================

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION EXTERNAL "
        "VALIDATION V1 - v0.4"
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
        "Precision = "
        f"{detection_precision:.4f}"
    )

    print(
        "Recall = "
        f"{detection_recall:.4f}"
    )

    print(
        "Specificity = "
        f"{detection_specificity:.4f}"
    )

    print(
        "Accuracy = "
        f"{detection_accuracy:.4f}"
    )

    print(
        "Coverage = "
        f"{detection_coverage:.4f}"
    )

    print()
    print(
        "ATOMIZATION - HUMAN-VALID CLAIMS"
    )
    print("-" * 44)

    print(
        "Valid claims = "
        f"{valid_claim_count}"
    )

    print(
        "Structurally evaluable = "
        f"{structurally_evaluable}"
    )

    print(
        "Structural coverage = "
        f"{structural_coverage:.4f}"
    )

    print(
        "Expected atoms = "
        f"{expected_atoms_total}"
    )

    print(
        "Predicted atoms on GT-valid "
        f"claims = {predicted_atoms_total}"
    )

    print(
        "Atom delta = "
        f"{atom_delta_total}"
    )

    print(
        "Atom inflation rate = "
        f"{atom_inflation_rate:.4f}"
    )

    print(
        "Class accuracy = "
        f"{class_accuracy:.4f}"
    )

    print(
        "Count accuracy = "
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
        "Over-atomized cases = "
        f"{over_atomized_cases}"
    )

    print(
        "Under-atomized cases = "
        f"{under_atomized_cases}"
    )

    print()
    print(
        "STRUCTURE BY HUMAN BUCKET"
    )
    print("-" * 44)

    for bucket in [
        "atomic",
        "compound",
        "relational",
    ]:
        stats = (
            bucket_summary[
                bucket
            ]
        )

        print()
        print(
            bucket.upper()
        )

        print(
            "  Cases = "
            f"{stats['cases']}"
        )

        print(
            "  Class accuracy = "
            f"{stats['class_accuracy']:.4f}"
        )

        print(
            "  Count accuracy = "
            f"{stats['count_accuracy']:.4f}"
        )

        print(
            "  Type accuracy = "
            f"{stats['type_sequence_accuracy']:.4f}"
        )

        print(
            "  Exact structure = "
            f"{stats['exact_structure_accuracy']:.4f}"
        )

        print(
            "  Over / Under = "
            f"{stats['over_atomized_cases']} / "
            f"{stats['under_atomized_cases']}"
        )

    print()
    print(
        "PROVIDER EXECUTION"
    )
    print("-" * 44)

    if (
        first_attempt_success
        is not None
    ):
        print(
            "First attempt = "
            f"{first_attempt_success}/"
            f"{EXPECTED_ITEMS}"
        )

        print(
            "First-attempt completion = "
            f"{first_attempt_completion_rate:.4f}"
        )

    if retry_success is not None:
        print(
            "Retry success rows = "
            f"{retry_success}"
        )

        print(
            "Retry failed rows = "
            f"{retry_failed}"
        )

    print(
        "Final completed = "
        f"{EXPECTED_ITEMS - provider_failed}/"
        f"{EXPECTED_ITEMS}"
    )

    print()
    print(
        "TEST A - INTERNAL CRITERIA"
    )
    print("-" * 44)

    observed_values = {
        "exact_structure_accuracy": (
            exact_structure_accuracy
        ),
        "count_accuracy": (
            count_accuracy
        ),
        "non_propositional_recall": (
            detection_recall
        ),
        "non_propositional_precision": (
            detection_precision
        ),
        "detection_coverage": (
            detection_coverage
        ),
    }

    for metric_name, threshold in (
        THRESHOLDS.items()
    ):
        observed = (
            observed_values[
                metric_name
            ]
        )

        passed = (
            threshold_results[
                metric_name
            ]
        )

        print(
            f"{metric_name}: "
            f"{observed:.4f} "
            f">= {threshold:.4f} "
            f"=> "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print(
        "Thresholds passed: "
        f"{passed_thresholds}/"
        f"{len(threshold_results)}"
    )

    print(
        "TEST A DECISION: "
        f"{test_a_decision}"
    )

    if failed_thresholds:
        print(
            "Failed thresholds:"
        )

        for item in failed_thresholds:
            print(
                f"  - {item}"
            )

    print()
    print(
        "NOTE:"
    )

    print(
        "Over/under-atomization requires "
        "case-pattern review before a final "
        "Continue/Investigate/Stop interpretation."
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