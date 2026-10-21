"""Evaluates Claim Atomization v1 structural predictions.

Compares frozen manual GT against Gemini predictions.

Measures only structural properties:
- atomization class;
- atom count;
- atom type sequence;
- exact structural match;
- over/under atomization.

Does NOT evaluate semantic text equivalence.
Does NOT modify the ground truth.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ATOMIZATION_DIR = Path(
    "data/evaluation/atomization_v1"
)

RESULTS_DIR = (
    ATOMIZATION_DIR
    / "results"
)

GT_FILE = (
    ATOMIZATION_DIR
    / "atomization_ground_truth_v1.csv"
)

PREDICTIONS_FILE = (
    RESULTS_DIR
    / "atomization_predictions_v1.csv"
)

OUTPUT_CASES = (
    RESULTS_DIR
    / "atomization_structure_cases_v1.csv"
)

OUTPUT_METRICS = (
    RESULTS_DIR
    / "atomization_structure_metrics_v1.csv"
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
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def main() -> None:
    gt_rows = load_csv(
        GT_FILE
    )

    prediction_rows = load_csv(
        PREDICTIONS_FILE
    )

    gt_by_dataset = defaultdict(list)

    for row in gt_rows:
        gt_by_dataset[
            row["dataset_id"]
        ].append(row)

    pred_by_dataset = defaultdict(list)

    for row in prediction_rows:
        if row["status"] != "success":
            continue

        pred_by_dataset[
            row["dataset_id"]
        ].append(row)

    case_rows = []

    for dataset_id in sorted(
        gt_by_dataset
    ):
        gt = sorted(
            gt_by_dataset[
                dataset_id
            ],
            key=lambda row: int(
                row["atom_order"]
            ),
        )

        pred = sorted(
            pred_by_dataset.get(
                dataset_id,
                [],
            ),
            key=lambda row: int(
                row[
                    "predicted_atom_order"
                ]
            ),
        )

        expected_class = (
            gt[0][
                "atomization_class"
            ]
        )

        predicted_class = (
            pred[0][
                "predicted_class"
            ]
            if pred
            else ""
        )

        expected_count = len(gt)
        predicted_count = len(pred)

        expected_types = [
            row["atom_type"]
            for row in gt
        ]

        predicted_types = [
            row[
                "predicted_atom_type"
            ]
            for row in pred
        ]

        class_match = (
            expected_class
            == predicted_class
        )

        count_match = (
            expected_count
            == predicted_count
        )

        type_sequence_match = (
            expected_types
            == predicted_types
        )

        exact_structure = (
            class_match
            and count_match
            and type_sequence_match
        )

        if predicted_count > expected_count:
            atomization_error = (
                "over_atomized"
            )

        elif predicted_count < expected_count:
            atomization_error = (
                "under_atomized"
            )

        else:
            atomization_error = (
                "count_exact"
            )

        case_rows.append(
            {
                "dataset_id": (
                    dataset_id
                ),
                "expected_class": (
                    expected_class
                ),
                "predicted_class": (
                    predicted_class
                ),
                "class_match": (
                    class_match
                ),
                "expected_count": (
                    expected_count
                ),
                "predicted_count": (
                    predicted_count
                ),
                "count_match": (
                    count_match
                ),
                "expected_types": (
                    " | ".join(
                        expected_types
                    )
                ),
                "predicted_types": (
                    " | ".join(
                        predicted_types
                    )
                ),
                "type_sequence_match": (
                    type_sequence_match
                ),
                "exact_structure": (
                    exact_structure
                ),
                "atomization_error": (
                    atomization_error
                ),
            }
        )

    total = len(case_rows)

    class_matches = sum(
        row["class_match"]
        for row in case_rows
    )

    count_matches = sum(
        row["count_match"]
        for row in case_rows
    )

    type_matches = sum(
        row[
            "type_sequence_match"
        ]
        for row in case_rows
    )

    exact_matches = sum(
        row["exact_structure"]
        for row in case_rows
    )

    over_atomized = sum(
        row["atomization_error"]
        == "over_atomized"
        for row in case_rows
    )

    under_atomized = sum(
        row["atomization_error"]
        == "under_atomized"
        for row in case_rows
    )

    expected_atoms = sum(
        row["expected_count"]
        for row in case_rows
    )

    predicted_atoms = sum(
        row["predicted_count"]
        for row in case_rows
    )

    atom_delta = (
        predicted_atoms
        - expected_atoms
    )

    atom_inflation_rate = (
        safe_divide(
            atom_delta,
            expected_atoms,
        )
    )

    metrics = {
        "source_claims": total,
        "expected_atoms": expected_atoms,
        "predicted_atoms": predicted_atoms,
        "atom_delta": atom_delta,
        "atom_inflation_rate": (
            atom_inflation_rate
        ),
        "class_accuracy": (
            safe_divide(
                class_matches,
                total,
            )
        ),
        "count_accuracy": (
            safe_divide(
                count_matches,
                total,
            )
        ),
        "type_sequence_accuracy": (
            safe_divide(
                type_matches,
                total,
            )
        ),
        "exact_structure_accuracy": (
            safe_divide(
                exact_matches,
                total,
            )
        ),
        "over_atomized_cases": (
            over_atomized
        ),
        "under_atomized_cases": (
            under_atomized
        ),
    }

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_CASES.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(
                case_rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            case_rows
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

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION V1 — "
        "STRUCTURAL EVALUATION"
    )
    print("=" * 88)

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
    print("=" * 88)
    print("CASE RESULTS")
    print("=" * 88)

    for row in case_rows:
        status = (
            "PASS"
            if row[
                "exact_structure"
            ]
            else "FAIL"
        )

        print(
            f"{row['dataset_id']} "
            f"{status} | "
            f"class "
            f"{row['expected_class']} "
            f"→ "
            f"{row['predicted_class']} | "
            f"atoms "
            f"{row['expected_count']} "
            f"→ "
            f"{row['predicted_count']} | "
            f"{row['atomization_error']}"
        )

    print()
    print("=" * 88)
    print("OUTPUTS")
    print("=" * 88)

    print(
        OUTPUT_CASES
    )

    print(
        OUTPUT_METRICS
    )


if __name__ == "__main__":
    main()