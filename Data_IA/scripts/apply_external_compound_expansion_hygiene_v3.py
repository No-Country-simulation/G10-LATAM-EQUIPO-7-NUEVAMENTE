from __future__ import annotations

from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_compound_expansion_pool_v3.csv"
)


EXCLUDE = {
    "EXT-COMP3-V1-008": (
        "tabular_header_or_output_extraction_noise"
    ),
}


def main() -> None:
    df = pd.read_csv(
        PATH,
        keep_default_na=False,
    )

    if len(df) != 10:
        raise ValueError(
            f"Expected 10 expansion candidates; found {len(df)}."
        )

    if df["expansion_id"].duplicated().any():
        raise ValueError(
            "Duplicate expansion_id values found."
        )

    if df["source_claim_id"].duplicated().any():
        raise ValueError(
            "Duplicate source_claim_id values found."
        )

    if "cleaned_claim_text" not in df.columns:
        df["cleaned_claim_text"] = df["claim_text"]

    df["hygiene_status"] = "keep"
    df["hygiene_notes"] = (
        "manual_hygiene_adjudication_documentary_content"
    )

    for expansion_id, reason in EXCLUDE.items():
        mask = (
            df["expansion_id"] == expansion_id
        )

        if int(mask.sum()) != 1:
            raise ValueError(
                f"Expected exactly one row for "
                f"{expansion_id}; found {int(mask.sum())}."
            )

        df.loc[
            mask,
            "hygiene_status",
        ] = "exclude_noise"

        df.loc[
            mask,
            "hygiene_notes",
        ] = reason

    valid = df[
        df["hygiene_status"] == "keep"
    ].copy()

    excluded = df[
        df["hygiene_status"] == "exclude_noise"
    ].copy()

    if len(valid) != 9:
        raise ValueError(
            f"Expected 9 valid candidates; found {len(valid)}."
        )

    if len(excluded) != 1:
        raise ValueError(
            f"Expected 1 excluded candidate; found {len(excluded)}."
        )

    valid_mask = (
        df["hygiene_status"] == "keep"
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
        "Compound Expansion Hygiene Review v3"
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