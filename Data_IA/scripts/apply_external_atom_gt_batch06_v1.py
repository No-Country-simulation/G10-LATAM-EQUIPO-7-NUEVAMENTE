from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

BATCH_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_review_batch_06_v1.csv"
)

ATOMS_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_atoms_batch_06_v1.csv"
)


DECISIONS = {
    "EXT-VAL-V1-051": (
        "Question rather than a factual proposition."
    ),
    "EXT-VAL-V1-052": (
        "Context-dependent statement because the subject "
        "referred to by 'Tiene' is omitted."
    ),
    "EXT-VAL-V1-053": (
        "Section heading."
    ),
    "EXT-VAL-V1-054": (
        "Section heading."
    ),
    "EXT-VAL-V1-055": (
        "Section heading."
    ),
    "EXT-VAL-V1-056": (
        "Imperative/instruction rather than an independently "
        "checkable factual proposition."
    ),
    "EXT-VAL-V1-057": (
        "Topic heading describing inline event handler "
        "attributes and why they should not be used."
    ),
    "EXT-VAL-V1-058": (
        "Section heading."
    ),
    "EXT-VAL-V1-059": (
        "Section heading/topic label."
    ),
    "EXT-VAL-V1-060": (
        "Context-dependent statement because 'al hacerlo' "
        "refers to omitted preceding content."
    ),
}


def main() -> None:
    df = pd.read_csv(
        BATCH_PATH,
        keep_default_na=False,
    )

    expected_ids = set(DECISIONS)
    actual_ids = set(df["external_case_id"])

    if actual_ids != expected_ids:
        raise ValueError(
            "Batch case IDs do not match decisions. "
            f"Missing={sorted(expected_ids - actual_ids)}, "
            f"Unexpected={sorted(actual_ids - expected_ids)}"
        )

    if not (
        df["target_bucket"]
        == "non_propositional"
    ).all():
        raise ValueError(
            "All Batch 06 cases must belong to "
            "the non_propositional bucket."
        )

    for case_id, notes in DECISIONS.items():
        mask = (
            df["external_case_id"]
            == case_id
        )

        if int(mask.sum()) != 1:
            raise ValueError(
                f"Expected exactly one row for {case_id}; "
                f"found {int(mask.sum())}."
            )

        df.loc[
            mask,
            "expected_atom_count",
        ] = 0

        df.loc[
            mask,
            "gt_review_status",
        ] = "reviewed"

        df.loc[
            mask,
            "gt_notes",
        ] = notes

    if (
        df["gt_review_status"]
        != "reviewed"
    ).any():
        raise ValueError(
            "Some Batch 06 cases remain unreviewed."
        )

    counts = pd.to_numeric(
        df["expected_atom_count"],
        errors="coerce",
    )

    if counts.isna().any():
        raise ValueError(
            "Invalid expected_atom_count values found."
        )

    if (counts != 0).any():
        raise ValueError(
            "All Batch 06 non-propositional cases "
            "must have expected_atom_count = 0."
        )

    atoms_df = pd.DataFrame(
        columns=[
            "external_case_id",
            "atom_index",
            "atom_text",
            "atom_type",
            "gt_review_status",
        ]
    )

    df.to_csv(
        BATCH_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    atoms_df.to_csv(
        ATOMS_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "External Atom Ground Truth Batch 06 v1"
    )
    print(
        "======================================="
    )

    print()
    print(
        "Cases reviewed:",
        len(df),
    )

    print(
        "Expected atoms:",
        int(counts.sum()),
    )

    print(
        "Atom rows:",
        len(atoms_df),
    )

    print()
    print(
        df[
            [
                "external_case_id",
                "target_bucket",
                "expected_atom_count",
                "gt_review_status",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"Updated batch: {BATCH_PATH}")
    print(f"Atoms: {ATOMS_OUTPUT_PATH}")

    print()
    print("IMPORTANT:")
    print(
        "All cases in this batch are human-adjudicated "
        "non-propositional inputs."
    )
    print(
        "No Claim Atomizer v0.4 predictions were used."
    )


if __name__ == "__main__":
    main()