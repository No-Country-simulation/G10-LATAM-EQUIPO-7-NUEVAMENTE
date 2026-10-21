"""Validates Claim Atomization v1 ground truth.

Checks:
- every dataset source claim is represented;
- atom IDs are unique;
- atom order is contiguous per source claim;
- atomization class is consistent within each source claim;
- atom types and support labels are valid;
- prints the exact atom distribution per source claim.

Does NOT modify any file.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ATOMIZATION_DIR = Path(
    "data/evaluation/atomization_v1"
)

DATASET_FILE = (
    ATOMIZATION_DIR
    / "atomization_dataset_v1.csv"
)

GT_FILE = (
    ATOMIZATION_DIR
    / "atomization_ground_truth_v1.csv"
)


VALID_CLASSES = {
    "atomic",
    "compound",
    "relational",
}

VALID_ATOM_TYPES = {
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
}

VALID_SUPPORT = {
    "supported",
    "unsupported",
    "uncertain",
}


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


def main() -> None:
    dataset_rows = load_csv(
        DATASET_FILE
    )

    gt_rows = load_csv(
        GT_FILE
    )

    errors: list[str] = []

    dataset_ids = {
        row["dataset_id"]
        for row in dataset_rows
    }

    gt_dataset_ids = {
        row["dataset_id"]
        for row in gt_rows
    }

    # --------------------------------------------------------------
    # Coverage
    # --------------------------------------------------------------

    missing = sorted(
        dataset_ids
        - gt_dataset_ids
    )

    unexpected = sorted(
        gt_dataset_ids
        - dataset_ids
    )

    for dataset_id in missing:
        errors.append(
            f"Missing GT for {dataset_id}"
        )

    for dataset_id in unexpected:
        errors.append(
            f"Unexpected GT dataset_id: {dataset_id}"
        )

    # --------------------------------------------------------------
    # Unique atom IDs
    # --------------------------------------------------------------

    atom_ids = [
        row["atom_id"]
        for row in gt_rows
    ]

    duplicate_atom_ids = [
        atom_id
        for atom_id, count
        in Counter(atom_ids).items()
        if count > 1
    ]

    for atom_id in duplicate_atom_ids:
        errors.append(
            f"Duplicate atom_id: {atom_id}"
        )

    # --------------------------------------------------------------
    # Group by source claim
    # --------------------------------------------------------------

    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in gt_rows:
        grouped[
            row["dataset_id"]
        ].append(row)

    # --------------------------------------------------------------
    # Validate each source claim
    # --------------------------------------------------------------

    for dataset_id, rows in grouped.items():
        classes = {
            row[
                "atomization_class"
            ]
            for row in rows
        }

        if len(classes) != 1:
            errors.append(
                f"{dataset_id}: inconsistent "
                f"atomization_class values: "
                f"{sorted(classes)}"
            )

        else:
            atom_class = next(
                iter(classes)
            )

            if (
                atom_class
                not in VALID_CLASSES
            ):
                errors.append(
                    f"{dataset_id}: invalid "
                    f"atomization_class "
                    f"{atom_class}"
                )

        orders = sorted(
            int(
                row["atom_order"]
            )
            for row in rows
        )

        expected_orders = list(
            range(
                1,
                len(rows) + 1,
            )
        )

        if orders != expected_orders:
            errors.append(
                f"{dataset_id}: atom_order "
                f"is not contiguous: {orders}"
            )

        for row in rows:
            atom_type = (
                row[
                    "atom_type"
                ]
            )

            support = (
                row[
                    "expected_support"
                ]
            )

            if (
                atom_type
                not in VALID_ATOM_TYPES
            ):
                errors.append(
                    f"{row['atom_id']}: "
                    f"invalid atom_type "
                    f"{atom_type}"
                )

            if (
                support
                not in VALID_SUPPORT
            ):
                errors.append(
                    f"{row['atom_id']}: "
                    f"invalid expected_support "
                    f"{support}"
                )

            if not (
                row[
                    "atom_text"
                ].strip()
            ):
                errors.append(
                    f"{row['atom_id']}: "
                    "empty atom_text"
                )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    print("=" * 84)
    print(
        "CLAIM ATOMIZATION GROUND TRUTH "
        "VALIDATION V1"
    )
    print("=" * 84)

    print(
        "Dataset source claims:",
        len(dataset_ids),
    )

    print(
        "GT source claims:",
        len(gt_dataset_ids),
    )

    print(
        "GT atoms:",
        len(gt_rows),
    )

    print()

    print(
        f"{'DATASET':<14}"
        f"{'CLASS':<14}"
        f"{'ATOMS':<8}"
        f"SUPPORT PATTERN"
    )

    print("-" * 84)

    for dataset_id in sorted(
        grouped
    ):
        rows = sorted(
            grouped[dataset_id],
            key=lambda row: int(
                row["atom_order"]
            ),
        )

        atom_class = (
            rows[0][
                "atomization_class"
            ]
        )

        pattern = " + ".join(
            row[
                "expected_support"
            ]
            for row in rows
        )

        print(
            f"{dataset_id:<14}"
            f"{atom_class:<14}"
            f"{len(rows):<8}"
            f"{pattern}"
        )

    print()
    print("=" * 84)
    print("TOTALS")
    print("=" * 84)

    class_counts = Counter(
        next(
            iter(
                {
                    row[
                        "atomization_class"
                    ]
                    for row in rows
                }
            )
        )
        for rows in grouped.values()
    )

    support_counts = Counter(
        row[
            "expected_support"
        ]
        for row in gt_rows
    )

    for name in [
        "atomic",
        "compound",
        "relational",
    ]:
        print(
            f"{name} = "
            f"{class_counts[name]}"
        )

    print()

    for name in [
        "supported",
        "unsupported",
        "uncertain",
    ]:
        print(
            f"{name} = "
            f"{support_counts[name]}"
        )

    print()

    if errors:
        print("=" * 84)
        print("VALIDATION ERRORS")
        print("=" * 84)

        for error in errors:
            print(
                "-",
                error,
            )

        raise SystemExit(1)

    print(
        "VALIDATION PASSED"
    )

    print(
        "No structural errors found."
    )


if __name__ == "__main__":
    main()