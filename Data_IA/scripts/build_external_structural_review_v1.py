from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

INPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_review_pool_final_v1.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_structural_review_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_structural_review_manifest_v1.json"
)


EXPECTED_ROWS = 120

ALLOWED_BUCKETS = {
    "needs_review",
    "atomic",
    "compound",
    "relational",
    "non_propositional",
}

ALLOWED_RELATION_SUBTYPES = {
    "",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
}


def main() -> None:
    df = pd.read_csv(INPUT_PATH)

    # -------------------------
    # Validate frozen input
    # -------------------------

    required_columns = {
        "external_review_id",
        "source_claim_id",
        "claim_text_final",
        "source_domain",
        "source_reference",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Missing required columns in frozen review pool: "
            + ", ".join(sorted(missing_columns))
        )

    if len(df) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS} rows; found {len(df)}."
        )

    if df["external_review_id"].duplicated().any():
        raise ValueError(
            "Duplicate external_review_id values found."
        )

    if df["source_claim_id"].duplicated().any():
        raise ValueError(
            "Duplicate source_claim_id values found."
        )

    if df["claim_text_final"].isna().any():
        raise ValueError(
            "claim_text_final contains null values."
        )

    if (
        df["claim_text_final"]
        .astype(str)
        .str.strip()
        .eq("")
        .any()
    ):
        raise ValueError(
            "claim_text_final contains empty values."
        )

    # -------------------------
    # Build human review sheet
    # -------------------------

    review = df[
        [
            "external_review_id",
            "source_claim_id",
            "claim_text_final",
            "source_domain",
            "source_reference",
        ]
    ].copy()

    review["target_bucket"] = "needs_review"
    review["relation_subtype"] = ""
    review["review_status"] = "pending"
    review["review_notes"] = ""

    # Keep order deterministic and easy to audit.
    review = review.sort_values(
        [
            "source_domain",
            "source_reference",
            "external_review_id",
        ]
    ).reset_index(drop=True)

    # -------------------------
    # Sanity checks
    # -------------------------

    if not set(review["target_bucket"]).issubset(
        ALLOWED_BUCKETS
    ):
        raise ValueError(
            "Unexpected target_bucket value."
        )

    if not set(review["relation_subtype"]).issubset(
        ALLOWED_RELATION_SUBTYPES
    ):
        raise ValueError(
            "Unexpected relation_subtype value."
        )

    source_counts = (
        review.groupby(
            [
                "source_domain",
                "source_reference",
            ]
        )
        .size()
        .reset_index(name="count")
    )

    if not (source_counts["count"] == 8).all():
        raise ValueError(
            "Expected exactly 8 claims per source."
        )

    domain_counts = (
        review["source_domain"]
        .value_counts()
        .sort_index()
    )

    if not (domain_counts == 24).all():
        raise ValueError(
            "Expected exactly 24 claims per domain."
        )

    # -------------------------
    # Write review sheet
    # -------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    review.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # -------------------------
    # Write manifest
    # -------------------------

    manifest = {
        "artifact": (
            "external_claim_structural_review_v1"
        ),
        "status": (
            "human_structural_review_pending"
        ),
        "input_artifact": (
            "external_claim_review_pool_final_v1"
        ),
        "input_path": str(INPUT_PATH),
        "output_path": str(OUTPUT_PATH),
        "total_claims": int(len(review)),
        "source_count": int(
            review["source_reference"].nunique()
        ),
        "domain_count": int(
            review["source_domain"].nunique()
        ),
        "claims_per_source": 8,
        "claims_per_domain": 24,
        "allowed_target_buckets": [
            "atomic",
            "compound",
            "relational",
            "non_propositional",
        ],
        "allowed_relation_subtypes": [
            "temporal_relation",
            "causal_relation",
            "conditional_relation",
            "comparative_relation",
            "negation_or_absence",
            "scope_or_quantifier",
        ],
        "initial_target_bucket": "needs_review",
        "initial_review_status": "pending",
        "review_instructions": {
            "atomic": (
                "One independently checkable proposition "
                "that should remain a single atom."
            ),
            "compound": (
                "Two or more independently checkable "
                "propositions expressed in the same claim."
            ),
            "relational": (
                "A proposition whose essential meaning "
                "depends on a relation such as temporal, "
                "causal, conditional, comparative, "
                "negation/absence, or scope/quantification."
            ),
            "non_propositional": (
                "Text that does not express an independently "
                "checkable proposition, such as a heading, "
                "label, fragment, navigation text, isolated "
                "term, or instruction-like fragment without "
                "a complete assertion."
            ),
        },
        "human_review_required": True,
        "ground_truth_status": (
            "not_created"
        ),
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "predictions_available_to_reviewer": False,
        "production_impact": False,
        "next_stage": (
            "human bucket adjudication of all 120 claims"
        ),
    }

    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # -------------------------
    # Console summary
    # -------------------------

    print("External Structural Review v1")
    print("=============================")
    print(f"Claims: {len(review)}")
    print(
        "Sources:",
        review["source_reference"].nunique(),
    )
    print(
        "Domains:",
        review["source_domain"].nunique(),
    )

    print()
    print("Initial bucket state:")
    print(
        review["target_bucket"]
        .value_counts()
        .to_string()
    )

    print()
    print("Initial review state:")
    print(
        review["review_status"]
        .value_counts()
        .to_string()
    )

    print()
    print("By domain:")
    print(domain_counts.to_string())

    print()
    print(f"Output: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")

    print()
    print("IMPORTANT:")
    print(
        "This file is for human structural review only."
    )
    print(
        "Do not run Claim Atomizer v0.4 before the "
        "human review and ground truth are frozen."
    )


if __name__ == "__main__":
    main()