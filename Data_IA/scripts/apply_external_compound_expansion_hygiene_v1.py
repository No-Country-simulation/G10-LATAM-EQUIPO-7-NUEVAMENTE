from __future__ import annotations

from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_compound_expansion_pool_v1.csv"
)


EXCLUDE = {
    "EXT-COMP-V1-006": (
        "table_header_extraction_noise"
    ),
    "EXT-COMP-V1-020": (
        "code_or_literal_data_extraction_noise"
    ),
    "EXT-COMP-V1-021": (
        "tabular_output_extraction_noise"
    ),
    "EXT-COMP-V1-022": (
        "tuple_or_output_extraction_noise"
    ),
    "EXT-COMP-V1-024": (
        "tabular_header_extraction_noise"
    ),
}


CLEAN = {
    "EXT-COMP-V1-011": (
        "Parámetros de path conteniendo paths"
    ),
}


def main() -> None:
    df = pd.read_csv(
        PATH,
        keep_default_na=False,
    )

    if len(df) != 30:
        raise ValueError(
            f"Expected 30 expansion candidates; found {len(df)}."
        )

    if df["expansion_id"].duplicated().any():
        raise ValueError(
            "Duplicate expansion_id values found."
        )

    if df["source_claim_id"].duplicated().any():
        raise ValueError(
            "Duplicate source_claim_id values found."
        )

    # Preserve original extracted text and store any
    # superficial cleaning separately.
    if "cleaned_claim_text" not in df.columns:
        df["cleaned_claim_text"] = df["claim_text"]

    df["hygiene_status"] = "keep"
    df["hygiene_notes"] = (
        "manual_hygiene_adjudication_documentary_content"
    )

    # -------------------------
    # Explicit noise exclusions
    # -------------------------

    for expansion_id, reason in EXCLUDE.items():
        mask = (
            df["expansion_id"] == expansion_id
        )

        if int(mask.sum()) != 1:
            raise ValueError(
                f"Expected exactly one row for {expansion_id}; "
                f"found {int(mask.sum())}."
            )

        df.loc[
            mask,
            "hygiene_status",
        ] = "exclude_noise"

        df.loc[
            mask,
            "hygiene_notes",
        ] = reason

    # -------------------------
    # Superficial cleaning only
    # -------------------------

    for expansion_id, cleaned_text in CLEAN.items():
        mask = (
            df["expansion_id"] == expansion_id
        )

        if int(mask.sum()) != 1:
            raise ValueError(
                f"Expected exactly one row for {expansion_id}; "
                f"found {int(mask.sum())}."
            )

        df.loc[
            mask,
            "hygiene_status",
        ] = "keep_cleaned"

        df.loc[
            mask,
            "cleaned_claim_text",
        ] = cleaned_text

        df.loc[
            mask,
            "hygiene_notes",
        ] = (
            "removed_superficial_documentation_marker"
        )

    # -------------------------
    # Integrity checks
    # -------------------------

    valid_statuses = {
        "keep",
        "keep_cleaned",
        "exclude_noise",
    }

    unexpected = (
        set(df["hygiene_status"])
        - valid_statuses
    )

    if unexpected:
        raise ValueError(
            "Unexpected hygiene statuses: "
            + ", ".join(sorted(unexpected))
        )

    valid = df[
        df["hygiene_status"].isin(
            {"keep", "keep_cleaned"}
        )
    ].copy()

    excluded = df[
        df["hygiene_status"]
        == "exclude_noise"
    ].copy()

    if len(valid) != 25:
        raise ValueError(
            f"Expected 25 valid candidates; found {len(valid)}."
        )

    if len(excluded) != 5:
        raise ValueError(
            f"Expected 5 excluded candidates; found {len(excluded)}."
        )

    # Reset structural fields for valid cases.
    # No structural adjudication occurs in this script.
    valid_mask = df[
        "hygiene_status"
    ].isin(
        {"keep", "keep_cleaned"}
    )

    df.loc[
        valid_mask,
        "target_bucket",
    ] = "needs_review"

    df.loc[
        valid_mask,
        "relation_subtype",
    ] = ""

    df.loc[
        valid_mask,
        "review_status",
    ] = "pending"

    df.loc[
        valid_mask,
        "review_notes",
    ] = ""

    df.to_csv(
        PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "Compound Expansion Hygiene Review v1"
    )
    print(
        "===================================="
    )

    print()
    print("Hygiene status:")
    print(
        df["hygiene_status"]
        .value_counts()
        .to_string()
    )

    print()
    print("Valid candidates:", len(valid))
    print(
        "Excluded candidates:",
        len(excluded),
    )

    print()
    print("Excluded:")
    print(
        excluded[
            [
                "expansion_id",
                "source_claim_id",
                "claim_text",
                "hygiene_notes",
            ]
        ].to_string(index=False)
    )

    print()
    print("Cleaned:")
    cleaned = df[
        df["hygiene_status"]
        == "keep_cleaned"
    ]

    print(
        cleaned[
            [
                "expansion_id",
                "claim_text",
                "cleaned_claim_text",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"Updated: {PATH}")

    print()
    print("IMPORTANT:")
    print(
        "No structural bucket decisions were made."
    )
    print(
        "No Claim Atomizer predictions were used."
    )


if __name__ == "__main__":
    main()