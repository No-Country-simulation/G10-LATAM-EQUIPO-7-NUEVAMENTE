"""Validate frozen Claim Atomization Holdout v1 ground truth.

Checks:
- all 20 selected holdout items are represented;
- valid claims have at least one atom;
- non-propositional items have no atomization payload;
- atom IDs are unique;
- atom order is contiguous;
- atomization class is consistent within each valid claim;
- atom types are valid;
- no accidental development overlap exists.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1"
)

HOLDOUT_DIR = (
    BASE_DIR
    / "holdout_v1"
)

DATASET_FILE = (
    HOLDOUT_DIR
    / "atomization_holdout_dataset_v1.csv"
)

GT_FILE = (
    HOLDOUT_DIR
    / "atomization_holdout_ground_truth_v1.csv"
)

DEV_DATASET = (
    BASE_DIR
    / "atomization_dataset_v1.csv"
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


def main() -> None:
    dataset_rows = load_csv(
        DATASET_FILE
    )

    gt_rows = load_csv(
        GT_FILE
    )

    dev_rows = load_csv(
        DEV_DATASET
    )

    errors: list[str] = []

    # --------------------------------------------------------------
    # Dataset coverage
    # --------------------------------------------------------------

    dataset_ids = {
        row["holdout_id"]
        for row in dataset_rows
    }

    gt_ids = {
        row["holdout_id"]
        for row in gt_rows
    }

    missing = sorted(
        dataset_ids - gt_ids
    )

    unexpected = sorted(
        gt_ids - dataset_ids
    )

    for holdout_id in missing:
        errors.append(
            f"Missing GT: {holdout_id}"
        )

    for holdout_id in unexpected:
        errors.append(
            f"Unexpected GT: {holdout_id}"
        )

    # --------------------------------------------------------------
    # Development overlap
    # --------------------------------------------------------------

    dev_keys = {
        (
            row["calibration_id"],
            row["source_claim_id"],
        )
        for row in dev_rows
    }

    holdout_keys = {
        (
            row["calibration_id"],
            row["source_claim_id"],
        )
        for row in dataset_rows
    }

    overlap = (
        dev_keys
        & holdout_keys
    )

    if overlap:
        errors.append(
            "Development/holdout leakage detected: "
            f"{sorted(overlap)}"
        )

    # --------------------------------------------------------------
    # Group GT rows
    # --------------------------------------------------------------

    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in gt_rows:
        grouped[
            row["holdout_id"]
        ].append(row)

    # --------------------------------------------------------------
    # Atom ID uniqueness
    # --------------------------------------------------------------

    atom_ids = [
        row["atom_id"]
        for row in gt_rows
        if row["atom_id"]
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
    # Validate each holdout item
    # --------------------------------------------------------------

    valid_claim_ids = set()
    non_propositional_ids = set()

    for holdout_id in sorted(
        dataset_ids
    ):
        rows = grouped.get(
            holdout_id,
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
                f"{holdout_id}: inconsistent "
                f"review_status values "
                f"{sorted(review_statuses)}"
            )
            continue

        review_status = next(
            iter(review_statuses)
        )

        if (
            review_status
            not in VALID_REVIEW_STATUS
        ):
            errors.append(
                f"{holdout_id}: invalid "
                f"review_status "
                f"{review_status}"
            )
            continue

        if (
            review_status
            == "non_propositional"
        ):
            non_propositional_ids.add(
                holdout_id
            )

            if len(rows) != 1:
                errors.append(
                    f"{holdout_id}: "
                    "non-propositional item must "
                    "have exactly one metadata row"
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
                if row[field].strip():
                    errors.append(
                        f"{holdout_id}: "
                        f"non-propositional field "
                        f"{field} must be empty"
                    )

            continue

        # valid_claim
        valid_claim_ids.add(
            holdout_id
        )

        classes = {
            row[
                "atomization_class"
            ]
            for row in rows
        }

        if len(classes) != 1:
            errors.append(
                f"{holdout_id}: inconsistent "
                f"atomization_class values "
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
                    f"{holdout_id}: invalid "
                    f"atomization_class "
                    f"{atom_class}"
                )

        orders = []

        for row in rows:
            if not row[
                "atom_id"
            ].strip():
                errors.append(
                    f"{holdout_id}: "
                    "valid claim has empty atom_id"
                )

            if not row[
                "atom_text"
            ].strip():
                errors.append(
                    f"{holdout_id}: "
                    "valid claim has empty atom_text"
                )

            atom_type = row[
                "atom_type"
            ]

            if (
                atom_type
                not in VALID_ATOM_TYPES
            ):
                errors.append(
                    f"{holdout_id}: invalid "
                    f"atom_type "
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
                    f"{holdout_id}: invalid "
                    f"atom_order "
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
                    f"{holdout_id}: "
                    f"atom_order not contiguous "
                    f"{orders}"
                )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    valid_atoms = [
        row
        for row in gt_rows
        if row[
            "review_status"
        ]
        == "valid_claim"
    ]

    class_by_claim = {}

    for row in valid_atoms:
        class_by_claim[
            row["holdout_id"]
        ] = row[
            "atomization_class"
        ]

    class_counts = Counter(
        class_by_claim.values()
    )

    atom_type_counts = Counter(
        row["atom_type"]
        for row in valid_atoms
    )

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION HOLDOUT "
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
        len(valid_claim_ids),
    )

    print(
        "Non-propositional:",
        len(
            non_propositional_ids
        ),
    )

    print(
        "Expected atoms:",
        len(valid_atoms),
    )

    print(
        "Development overlap:",
        len(overlap),
    )

    print()

    print(
        f"{'HOLDOUT':<18}"
        f"{'STATUS':<20}"
        f"{'CLASS':<14}"
        f"ATOMS"
    )

    print("-" * 88)

    for holdout_id in sorted(
        grouped
    ):
        rows = grouped[
            holdout_id
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
            atom_count = len(rows)

        print(
            f"{holdout_id:<18}"
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
        "Holdout ground truth is structurally valid "
        "and isolated from development."
    )


if __name__ == "__main__":
    main()