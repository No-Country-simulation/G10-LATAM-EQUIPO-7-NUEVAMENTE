"""Compare Claim Atomizer v0.1 and v0.2 against frozen GT.

Compares structural metrics only.

Does NOT:
- modify ground truth;
- call Gemini;
- evaluate factual support.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1"
)

RESULTS_DIR = (
    BASE_DIR
    / "results"
)

GT_FILE = (
    BASE_DIR
    / "atomization_ground_truth_v1.csv"
)

VERSIONS = {
    "v0.1": (
        RESULTS_DIR
        / "atomization_predictions_v1.csv"
    ),
    "v0.2": (
        RESULTS_DIR
        / "atomization_predictions_v0_2.csv"
    ),
    "v0.3": (
    RESULTS_DIR
        / "atomization_predictions_v0_3.csv"
    ),
}

OUTPUT_FILE = (
    RESULTS_DIR
    / "atomization_version_comparison_v1.csv"
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


def group_gt(
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped = defaultdict(list)

    for row in rows:
        grouped[
            row["dataset_id"]
        ].append(row)

    return grouped


def group_predictions(
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped = defaultdict(list)

    for row in rows:
        if row["status"] != "success":
            continue

        grouped[
            row["dataset_id"]
        ].append(row)

    return grouped


def safe_div(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def evaluate_version(
    version: str,
    prediction_file: Path,
    gt_by_id: dict[
        str,
        list[dict[str, str]],
    ],
) -> dict[str, str | int | float]:
    prediction_rows = load_csv(
        prediction_file
    )

    pred_by_id = group_predictions(
        prediction_rows
    )

    total = len(gt_by_id)

    expected_atoms = 0
    predicted_atoms = 0

    class_matches = 0
    count_matches = 0
    type_matches = 0
    exact_matches = 0

    over_atomized = 0
    under_atomized = 0

    for dataset_id, gt_rows in (
        gt_by_id.items()
    ):
        gt_rows = sorted(
            gt_rows,
            key=lambda row: int(
                row["atom_order"]
            ),
        )

        pred_rows = sorted(
            pred_by_id.get(
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
            gt_rows[0][
                "atomization_class"
            ]
        )

        predicted_class = (
            pred_rows[0][
                "predicted_class"
            ]
            if pred_rows
            else ""
        )

        expected_count = len(
            gt_rows
        )

        predicted_count = len(
            pred_rows
        )

        expected_atoms += (
            expected_count
        )

        predicted_atoms += (
            predicted_count
        )

        expected_types = [
            row["atom_type"]
            for row in gt_rows
        ]

        predicted_types = [
            row[
                "predicted_atom_type"
            ]
            for row in pred_rows
        ]

        class_match = (
            expected_class
            == predicted_class
        )

        count_match = (
            expected_count
            == predicted_count
        )

        type_match = (
            expected_types
            == predicted_types
        )

        exact = (
            class_match
            and count_match
            and type_match
        )

        class_matches += int(
            class_match
        )

        count_matches += int(
            count_match
        )

        type_matches += int(
            type_match
        )

        exact_matches += int(
            exact
        )

        if (
            predicted_count
            > expected_count
        ):
            over_atomized += 1

        elif (
            predicted_count
            < expected_count
        ):
            under_atomized += 1

    atom_delta = (
        predicted_atoms
        - expected_atoms
    )

    return {
        "version": version,
        "source_claims": total,
        "expected_atoms": (
            expected_atoms
        ),
        "predicted_atoms": (
            predicted_atoms
        ),
        "atom_delta": (
            atom_delta
        ),
        "atom_inflation_rate": (
            safe_div(
                atom_delta,
                expected_atoms,
            )
        ),
        "class_accuracy": (
            safe_div(
                class_matches,
                total,
            )
        ),
        "count_accuracy": (
            safe_div(
                count_matches,
                total,
            )
        ),
        "type_sequence_accuracy": (
            safe_div(
                type_matches,
                total,
            )
        ),
        "exact_structure_accuracy": (
            safe_div(
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


def main() -> None:
    gt_rows = load_csv(
        GT_FILE
    )

    gt_by_id = group_gt(
        gt_rows
    )

    results = []

    for version, file_path in (
        VERSIONS.items()
    ):
        results.append(
            evaluate_version(
                version,
                file_path,
                gt_by_id,
            )
        )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(
                results[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            results
        )

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION — "
        "VERSION COMPARISON"
    )
    print("=" * 88)

    for result in results:
        print()
        print(
            result["version"]
        )
        print("-" * 44)

        for key, value in (
            result.items()
        ):
            if key == "version":
                continue

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
                    f"{key} = "
                    f"{value}"
                )

    print()
    print("=" * 88)
    print(
        "Output:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()