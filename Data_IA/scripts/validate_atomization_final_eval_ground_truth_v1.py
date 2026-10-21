"""Validate blind human ground truth for atomization final_eval_v1.

Checks:
- all 23 final-eval items are represented;
- valid claims have valid atomization payloads;
- non-propositional items have no atomization payload;
- atom IDs are unique;
- atom orders are contiguous;
- classes and atom types are valid;
- final-eval IDs match the frozen dataset exactly;
- no overlap exists with development or validation sets.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1"
)

FINAL_DIR = (
    BASE_DIR
    / "final_eval_v1"
)

FINAL_DATASET = (
    FINAL_DIR
    / "atomization_final_eval_dataset_v1.csv"
)

FINAL_GT = (
    FINAL_DIR
    / "atomization_final_eval_ground_truth_v1.csv"
)

DEV_DATASET = (
    BASE_DIR
    / "atomization_dataset_v1.csv"
)

VALIDATION_DATASET = (
    BASE_DIR
    / "holdout_v1"
    / "atomization_holdout_dataset_v1.csv"
)


VALID_REVIEW_STATUS = {
    "valid_claim",
    "non_propositional",
}

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


def source_key(
    calibration_id: str,
    source_claim_id: str,
) -> str:
    return (
        f"{calibration_id}|"
        f"{source_claim_id}"
    )


def main() -> None:
    dataset_rows = load_csv(
        FINAL_DATASET
    )

    gt_rows = load_csv(
        FINAL_GT
    )

    dev_rows = load_csv(
        DEV_DATASET
    )

    validation_rows = load_csv(
        VALIDATION_DATASET
    )

    errors: list[str] = []

    # ----------------------------------------------------------
    # Dataset coverage
    # ----------------------------------------------------------

    dataset_ids = {
        row["final_eval_id"]
        for row in dataset_rows
    }

    gt_ids = {
        row["final_eval_id"]
        for row in gt_rows
    }

    if len(dataset_ids) != 23:
        errors.append(
            "Expected 23 final-eval dataset IDs, "
            f"found {len(dataset_ids)}."
        )

    missing = sorted(
        dataset_ids - gt_ids
    )

    unexpected = sorted(
        gt_ids - dataset_ids
    )

    for final_eval_id in missing:
        errors.append(
            f"Missing GT: "
            f"{final_eval_id}"
        )

    for final_eval_id in unexpected:
        errors.append(
            f"Unexpected GT: "
            f"{final_eval_id}"
        )

    # ----------------------------------------------------------
    # Partition isolation
    # ----------------------------------------------------------

    final_keys = {
        source_key(
            row["calibration_id"],
            row["source_claim_id"],
        )
        for row in dataset_rows
    }

    dev_keys = {
        source_key(
            row["calibration_id"],
            row["source_claim_id"],
        )
        for row in dev_rows
    }

    validation_keys = {
        source_key(
            row["calibration_id"],
            row["source_claim_id"],
        )
        for row in validation_rows
    }

    dev_overlap = (
        final_keys
        & dev_keys
    )

    validation_overlap = (
        final_keys
        & validation_keys
    )

    if dev_overlap:
        errors.append(
            "Final/development overlap detected: "
            f"{sorted(dev_overlap)}"
        )

    if validation_overlap:
        errors.append(
            "Final/validation overlap detected: "
            f"{sorted(validation_overlap)}"
        )

    # ----------------------------------------------------------
    # Group GT rows
    # ----------------------------------------------------------

    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in gt_rows:
        grouped[
            row["final_eval_id"]
        ].append(row)

    # ----------------------------------------------------------
    # Atom ID uniqueness
    # ----------------------------------------------------------

    atom_ids = [
        row["atom_id"]
        for row in gt_rows
        if row["atom_id"].strip()
    ]

    duplicates = [
        atom_id
        for atom_id, count
        in Counter(
            atom_ids
        ).items()
        if count > 1
    ]

    for atom_id in duplicates:
        errors.append(
            f"Duplicate atom_id: "
            f"{atom_id}"
        )

    # ----------------------------------------------------------
    # Validate each case
    # ----------------------------------------------------------

    valid_ids = set()
    non_prop_ids = set()

    for final_eval_id in sorted(
        dataset_ids
    ):
        rows = grouped.get(
            final_eval_id,
            [],
        )

        if not rows:
            continue

        review_statuses = {
            row["review_status"]
            for row in rows
        }

        if len(review_statuses) != 1:
            errors.append(
                f"{final_eval_id}: "
                "inconsistent review_status "
                f"{sorted(review_statuses)}"
            )
            continue

        review_status = next(
            iter(
                review_statuses
            )
        )

        if (
            review_status
            not in VALID_REVIEW_STATUS
        ):
            errors.append(
                f"{final_eval_id}: "
                "invalid review_status "
                f"{review_status}"
            )
            continue

        if (
            review_status
            == "non_propositional"
        ):
            non_prop_ids.add(
                final_eval_id
            )

            if len(rows) != 1:
                errors.append(
                    f"{final_eval_id}: "
                    "non-propositional item "
                    "must have exactly one row"
                )

            row = rows[0]

            fields_that_must_be_empty = [
                "atomization_class",
                "atom_id",
                "atom_order",
                "atom_text",
                "atom_type",
            ]

            for field in (
                fields_that_must_be_empty
            ):
                if row[
                    field
                ].strip():
                    errors.append(
                        f"{final_eval_id}: "
                        f"{field} must be "
                        "empty for "
                        "non_propositional"
                    )

            continue

        # valid_claim
        valid_ids.add(
            final_eval_id
        )

        classes = {
            row["atomization_class"]
            for row in rows
        }

        if len(classes) != 1:
            errors.append(
                f"{final_eval_id}: "
                "inconsistent classes "
                f"{sorted(classes)}"
            )

        else:
            atom_class = next(
                iter(
                    classes
                )
            )

            if (
                atom_class
                not in VALID_CLASSES
            ):
                errors.append(
                    f"{final_eval_id}: "
                    "invalid class "
                    f"{atom_class}"
                )

        orders: list[int] = []

        for row in rows:
            if not row[
                "atom_id"
            ].strip():
                errors.append(
                    f"{final_eval_id}: "
                    "empty atom_id"
                )

            if not row[
                "atom_text"
            ].strip():
                errors.append(
                    f"{final_eval_id}: "
                    "empty atom_text"
                )

            atom_type = row[
                "atom_type"
            ]

            if (
                atom_type
                not in VALID_ATOM_TYPES
            ):
                errors.append(
                    f"{final_eval_id}: "
                    "invalid atom_type "
                    f"{atom_type}"
                )

            try:
                orders.append(
                    int(
                        row[
                            "atom_order"
                        ]
                    )
                )

            except ValueError:
                errors.append(
                    f"{final_eval_id}: "
                    "invalid atom_order "
                    f"{row['atom_order']}"
                )

        if orders:
            orders = sorted(
                orders
            )

            expected_orders = list(
                range(
                    1,
                    len(rows) + 1,
                )
            )

            if (
                orders
                != expected_orders
            ):
                errors.append(
                    f"{final_eval_id}: "
                    "non-contiguous atom_order "
                    f"{orders}"
                )

        # Class-specific invariants
        atom_class = rows[0][
            "atomization_class"
        ]

        if (
            atom_class
            == "atomic"
            and len(rows) != 1
        ):
            errors.append(
                f"{final_eval_id}: "
                "atomic must have "
                "exactly one atom"
            )

        if (
            atom_class
            == "compound"
            and len(rows) < 2
        ):
            errors.append(
                f"{final_eval_id}: "
                "compound must have "
                "at least two atoms"
            )

    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------

    valid_atoms = [
        row
        for row in gt_rows
        if row[
            "review_status"
        ]
        == "valid_claim"
    ]

    class_by_claim = {
        row["final_eval_id"]:
        row["atomization_class"]
        for row in valid_atoms
    }

    class_counts = Counter(
        class_by_claim.values()
    )

    atom_type_counts = Counter(
        row["atom_type"]
        for row in valid_atoms
    )

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION FINAL EVAL "
        "GROUND TRUTH VALIDATION V1"
    )
    print("=" * 88)

    print(
        "Dataset items:",
        len(dataset_ids),
    )

    print(
        "GT items:",
        len(gt_ids),
    )

    print(
        "Valid claims:",
        len(valid_ids),
    )

    print(
        "Non-propositional:",
        len(non_prop_ids),
    )

    print(
        "Expected atoms:",
        len(valid_atoms),
    )

    print(
        "Development overlap:",
        len(dev_overlap),
    )

    print(
        "Validation overlap:",
        len(
            validation_overlap
        ),
    )

    print()

    print(
        f"{'FINAL ID':<18}"
        f"{'STATUS':<20}"
        f"{'CLASS':<14}"
        f"ATOMS"
    )

    print("-" * 88)

    for final_eval_id in sorted(
        grouped
    ):
        rows = grouped[
            final_eval_id
        ]

        status = rows[0][
            "review_status"
        ]

        if (
            status
            == "non_propositional"
        ):
            atom_class = "-"
            atom_count = 0

        else:
            atom_class = rows[0][
                "atomization_class"
            ]
            atom_count = len(
                rows
            )

        print(
            f"{final_eval_id:<18}"
            f"{status:<20}"
            f"{atom_class:<14}"
            f"{atom_count}"
        )

    print()
    print("=" * 88)
    print("CLASS COUNTS")
    print("=" * 88)

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
    print("=" * 88)
    print("ATOM TYPE COUNTS")
    print("=" * 88)

    for name in [
        "factual_proposition",
        "temporal_relation",
        "causal_relation",
        "conditional_relation",
        "comparative_relation",
        "negation_or_absence",
        "scope_or_quantifier",
    ]:
        print(
            f"{name} = "
            f"{atom_type_counts[name]}"
        )

    print()

    if errors:
        print("=" * 88)
        print("VALIDATION ERRORS")
        print("=" * 88)

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
        "Final-eval ground truth is "
        "structurally valid and isolated "
        "from development and validation."
    )


if __name__ == "__main__":
    main()