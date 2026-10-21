from __future__ import annotations

from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_compound_expansion_pool_v2.csv"
)


EXCLUDE = {
    "EXT-COMP2-V1-010": (
        "pandas_output_metadata_extraction_noise"
    ),
    "EXT-COMP2-V1-011": (
        "executable_code_extraction_noise"
    ),
    "EXT-COMP2-V1-012": (
        "tabular_output_extraction_noise"
    ),
}


CLEAN = {
    "EXT-COMP2-V1-005": (
        "Este será el punto principal de interacción "
        "para crear toda tu API."
    ),
    "EXT-COMP2-V1-007": (
        "Kubernetes ofrece un entorno de administración "
        "centrado en contenedores."
    ),
    "EXT-COMP2-V1-015": (
        "Puedes ver el ejemplo completo funcionando en vivo; "
        "pruébalo ahí."
    ),
}


def main() -> None:
    df = pd.read_csv(
        PATH,
        keep_default_na=False,
    )

    if len(df) != 15:
        raise ValueError(
            f"Expected 15 expansion candidates; found {len(df)}."
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

    # -------------------------
    # Noise exclusions
    # -------------------------

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

    # -------------------------
    # Superficial cleaning
    # -------------------------

    for expansion_id, cleaned_text in CLEAN.items():
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
        ] = "keep_cleaned"

        df.loc[
            mask,
            "cleaned_claim_text",
        ] = cleaned_text

        df.loc[
            mask,
            "hygiene_notes",
        ] = (
            "corrected_extraction_spacing_artifact"
        )

    # -------------------------
    # Integrity checks
    # -------------------------

    valid = df[
        df["hygiene_status"].isin(
            {"keep", "keep_cleaned"}
        )
    ].copy()

    excluded = df[
        df["hygiene_status"] == "exclude_noise"
    ].copy()

    if len(valid) != 12:
        raise ValueError(
            f"Expected 12 valid candidates; found {len(valid)}."
        )

    if len(excluded) != 3:
        raise ValueError(
            f"Expected 3 excluded candidates; found {len(excluded)}."
        )

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
        "Compound Expansion Hygiene Review v2"
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