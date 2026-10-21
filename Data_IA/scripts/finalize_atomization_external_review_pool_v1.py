from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

ORIGINAL_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_review_pool_hygiene_v1.csv"
)

ROUND1_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacements_v1.csv"
)

ROUND2_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacement_round2_v1.csv"
)

ROUND3_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacement_round3_v1.csv"
)

ROUND4_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacement_round4_v1.csv"
)

ROUND5_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacement_round5_v1.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_review_pool_final_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_review_pool_final_manifest_v1.json"
)


VALID_STATUSES = {
    "keep",
    "keep_cleaned",
}


def effective_text(row: pd.Series) -> str:
    cleaned = row.get("cleaned_claim_text")

    if pd.notna(cleaned) and str(cleaned).strip():
        return str(cleaned).strip()

    return str(row["claim_text"]).strip()


def prepare_original() -> pd.DataFrame:
    df = pd.read_csv(ORIGINAL_PATH)

    valid = df[
        df["hygiene_status"].isin(VALID_STATUSES)
    ].copy()

    valid["selection_origin"] = "original_review_pool"
    valid["replacement_id"] = pd.NA

    return valid


def prepare_round1() -> pd.DataFrame:
    df = pd.read_csv(ROUND1_PATH)

    valid = df[
        df["hygiene_status"].isin(VALID_STATUSES)
    ].copy()

    valid["selection_origin"] = "replacement_round_1"
    valid["review_id"] = pd.NA

    return valid


def prepare_round5() -> pd.DataFrame:
    df = pd.read_csv(ROUND5_PATH)

    if len(df) != 1:
        raise ValueError(
            f"Round 5 must contain exactly 1 row; found {len(df)}."
        )

    # Human hygiene adjudication:
    # EXT-REPL5-V1-001 is valid documentary content.
    df["hygiene_status"] = "keep"
    df["hygiene_notes"] = (
        "manual_hygiene_adjudication_documentary_content"
    )

    if "cleaned_claim_text" not in df.columns:
        df["cleaned_claim_text"] = df["claim_text"]

    # Persist adjudication into the round-5 artifact.
    df.to_csv(
        ROUND5_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    df["selection_origin"] = "replacement_round_5"
    df["review_id"] = pd.NA

    return df


def validate_rejected_rounds() -> None:
    expected = {
        ROUND2_PATH: "EXT-REPL2-V1-001",
        ROUND3_PATH: "EXT-REPL3-V1-001",
        ROUND4_PATH: "EXT-REPL4-V1-001",
    }

    for path, replacement_id in expected.items():
        df = pd.read_csv(path)

        if len(df) != 1:
            raise ValueError(
                f"{path.name} must contain exactly one candidate."
            )

        actual_id = str(df.iloc[0]["replacement_id"])

        if actual_id != replacement_id:
            raise ValueError(
                f"Unexpected candidate in {path.name}: "
                f"{actual_id}"
            )


def main() -> None:
    validate_rejected_rounds()

    original = prepare_original()
    round1 = prepare_round1()
    round5 = prepare_round5()

    final = pd.concat(
        [original, round1, round5],
        ignore_index=True,
        sort=False,
    )

    final["claim_text_final"] = final.apply(
        effective_text,
        axis=1,
    )

    # The external material is natural documentation text.
    # We do not invent an internal NuevaMente output format.
    final["format"] = "source_text"

    # Structural bucket and final benchmark selection are still
    # unresolved and require human review.
    final["target_bucket"] = "needs_review"
    final["selection_status"] = "needs_review"

    final = final.sort_values(
        [
            "source_domain",
            "source_reference",
            "source_claim_id",
        ]
    ).reset_index(drop=True)

    final.insert(
        0,
        "external_review_id",
        [
            f"EXT-POOL-V1-{i:03d}"
            for i in range(1, len(final) + 1)
        ],
    )

    # -------------------------
    # Integrity checks
    # -------------------------

    if len(final) != 120:
        raise ValueError(
            f"Expected 120 valid claims; found {len(final)}."
        )

    if final["source_claim_id"].duplicated().any():
        duplicated = final.loc[
            final["source_claim_id"].duplicated(
                keep=False
            ),
            ["source_claim_id", "claim_text_final"],
        ]

        raise ValueError(
            "Duplicate source_claim_id values found:\n"
            + duplicated.to_string(index=False)
        )

    source_counts = (
        final.groupby(
            [
                "source_domain",
                "source_reference",
            ]
        )
        .size()
        .reset_index(name="count")
    )

    bad_sources = source_counts[
        source_counts["count"] != 8
    ]

    if not bad_sources.empty:
        raise ValueError(
            "Every source must contribute exactly 8 claims:\n"
            + bad_sources.to_string(index=False)
        )

    domain_counts = (
        final["source_domain"]
        .value_counts()
        .sort_index()
    )

    if not (domain_counts == 24).all():
        raise ValueError(
            "Every domain must contain exactly 24 claims:\n"
            + domain_counts.to_string()
        )

    if final["source_reference"].nunique() != 15:
        raise ValueError(
            "Expected exactly 15 source documents."
        )

    if final["claim_text_final"].isna().any():
        raise ValueError(
            "claim_text_final contains null values."
        )

    if (
        final["claim_text_final"]
        .astype(str)
        .str.strip()
        .eq("")
        .any()
    ):
        raise ValueError(
            "claim_text_final contains empty values."
        )

    # Keep a compact but auditable column order.
    preferred_columns = [
        "external_review_id",
        "source_claim_id",
        "claim_text",
        "cleaned_claim_text",
        "claim_text_final",
        "format",
        "source_domain",
        "source_reference",
        "target_bucket",
        "selection_status",
        "hygiene_status",
        "hygiene_notes",
        "selection_origin",
        "review_id",
        "replacement_id",
        "notes",
    ]

    existing_columns = [
        column
        for column in preferred_columns
        if column in final.columns
    ]

    remaining_columns = [
        column
        for column in final.columns
        if column not in existing_columns
    ]

    final = final[
        existing_columns + remaining_columns
    ]

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    final.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "artifact": "external_claim_review_pool_final_v1",
        "status": (
            "hygiene_complete_frozen_before_bucket_review"
        ),
        "total_claims": int(len(final)),
        "source_count": int(
            final["source_reference"].nunique()
        ),
        "domain_count": int(
            final["source_domain"].nunique()
        ),
        "claims_per_source": 8,
        "claims_per_domain": 24,
        "format": "source_text",
        "composition": {
            "original_review_pool": int(
                (
                    final["selection_origin"]
                    == "original_review_pool"
                ).sum()
            ),
            "replacement_round_1": int(
                (
                    final["selection_origin"]
                    == "replacement_round_1"
                ).sum()
            ),
            "replacement_round_5": int(
                (
                    final["selection_origin"]
                    == "replacement_round_5"
                ).sum()
            ),
        },
        "rejected_replacement_rounds": {
            "round_2": {
                "replacement_id": "EXT-REPL2-V1-001",
                "reason": "numeric_output_noise",
            },
            "round_3": {
                "replacement_id": "EXT-REPL3-V1-001",
                "reason": "tabular_output_noise",
            },
            "round_4": {
                "replacement_id": "EXT-REPL4-V1-001",
                "reason": "tabular_output_noise",
            },
        },
        "next_stage": (
            "human structural bucket review "
            "before final balanced dataset selection"
        ),
        "human_review_pending": [
            "target_bucket",
            "selection_status",
        ],
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "ground_truth_used": False,
        "production_impact": False,
    }

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("External Claim Review Pool Final v1")
    print("===================================")
    print(f"Claims: {len(final)}")
    print(
        "Sources:",
        final["source_reference"].nunique(),
    )
    print(
        "Domains:",
        final["source_domain"].nunique(),
    )

    print()
    print("By domain:")
    print(domain_counts.to_string())

    print()
    print("By source:")
    print(
        source_counts.to_string(index=False)
    )

    print()
    print("Composition:")
    print(
        final["selection_origin"]
        .value_counts()
        .to_string()
    )

    print()
    print(f"Output: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")

    print()
    print("IMPORTANT:")
    print(
        "Hygiene is complete."
    )
    print(
        "No Claim Atomizer predictions have been used."
    )
    print(
        "Human target_bucket review is the next stage."
    )


if __name__ == "__main__":
    main()