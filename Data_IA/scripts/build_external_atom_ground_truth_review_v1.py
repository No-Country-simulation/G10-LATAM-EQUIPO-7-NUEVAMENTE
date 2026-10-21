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
    / "external_claim_balanced_dataset_v1.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "external_atom_ground_truth_review_v1.csv"
)

BATCH_DIR = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_atom_ground_truth_review_manifest_v1.json"
)


EXPECTED_TOTAL = 80
BATCH_SIZE = 10

ALLOWED_BUCKETS = {
    "atomic",
    "compound",
    "relational",
    "non_propositional",
}

ALLOWED_ATOM_TYPES = [
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
]


def main() -> None:
    df = pd.read_csv(
        INPUT_PATH,
        keep_default_na=False,
    )

    required_columns = {
        "external_case_id",
        "source_claim_id",
        "claim_text_final",
        "target_bucket",
        "relation_subtype",
        "source_domain",
        "source_reference",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    if len(df) != EXPECTED_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_TOTAL} selected cases; "
            f"found {len(df)}."
        )

    if df["external_case_id"].duplicated().any():
        raise ValueError(
            "Duplicate external_case_id values found."
        )

    if df["source_claim_id"].duplicated().any():
        raise ValueError(
            "Duplicate source_claim_id values found."
        )

    unexpected_buckets = (
        set(df["target_bucket"])
        - ALLOWED_BUCKETS
    )

    if unexpected_buckets:
        raise ValueError(
            "Unexpected structural buckets: "
            + ", ".join(sorted(unexpected_buckets))
        )

    review = df[
        [
            "external_case_id",
            "source_claim_id",
            "claim_text_final",
            "target_bucket",
            "relation_subtype",
            "source_domain",
            "source_reference",
        ]
    ].copy()

    # Human atom-level Ground Truth fields.
    #
    # Non-propositional cases should ultimately have
    # expected_atom_count = 0.
    #
    # All other cases must contain one or more atoms.
    review["expected_atom_count"] = ""
    review["gt_review_status"] = "pending"
    review["gt_notes"] = ""

    # Keep atom text/type outside the case-level table until
    # adjudication. They will be materialized later in a
    # long-form Ground Truth artifact.
    review = review.sort_values(
        "external_case_id"
    ).reset_index(drop=True)

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
    # Export blind review batches
    # -------------------------

    BATCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    batch_manifest = []

    for start in range(
        0,
        len(review),
        BATCH_SIZE,
    ):
        batch_number = (
            start // BATCH_SIZE
        ) + 1

        end = min(
            start + BATCH_SIZE,
            len(review),
        )

        batch = review.iloc[
            start:end
        ].copy()

        batch_path = (
            BATCH_DIR
            / (
                "external_atom_gt_review_"
                f"batch_{batch_number:02d}_v1.csv"
            )
        )

        batch.to_csv(
            batch_path,
            index=False,
            encoding="utf-8-sig",
        )

        batch_manifest.append(
            {
                "batch": batch_number,
                "start_case": (
                    batch.iloc[0]["external_case_id"]
                ),
                "end_case": (
                    batch.iloc[-1]["external_case_id"]
                ),
                "rows": int(len(batch)),
                "path": str(batch_path),
            }
        )

    manifest = {
        "artifact": (
            "external_atom_ground_truth_review_v1"
        ),
        "status": (
            "blind_human_atom_ground_truth_pending"
        ),
        "input_dataset": str(INPUT_PATH),
        "total_cases": int(len(review)),
        "batch_size": BATCH_SIZE,
        "batch_count": len(batch_manifest),
        "allowed_atom_types": ALLOWED_ATOM_TYPES,
        "ground_truth_rules": {
            "non_propositional": (
                "Expected atom count must be 0."
            ),
            "atomic": (
                "Normally one independently checkable atom."
            ),
            "compound": (
                "Two or more independently checkable atoms."
            ),
            "relational": (
                "At least one atom whose essential meaning "
                "is relational; preserve the relation and "
                "its qualifiers."
            ),
            "preserve_meaning": (
                "Atoms may be minimally rewritten for "
                "standalone clarity, but must not add facts "
                "not present in the source claim."
            ),
            "preserve_qualifiers": (
                "Do not drop temporal, causal, conditional, "
                "comparative, negation, scope, or quantity "
                "qualifiers."
            ),
        },
        "batches": batch_manifest,
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "predictions_available_to_reviewer": False,
        "production_impact": False,
        "next_stage": (
            "human atom decomposition and atom type "
            "adjudication for all 80 cases"
        ),
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

    print(
        "External Atom Ground Truth Review v1"
    )
    print(
        "===================================="
    )

    print(
        "Cases:",
        len(review),
    )

    print(
        "Batches:",
        len(batch_manifest),
    )

    print(
        "Batch size:",
        BATCH_SIZE,
    )

    print()

    print("Structural buckets:")
    print(
        review["target_bucket"]
        .value_counts()
        .to_string()
    )

    print()

    for item in batch_manifest:
        print(
            f"Batch {item['batch']:02d}: "
            f"{item['start_case']} -> "
            f"{item['end_case']} "
            f"({item['rows']} rows)"
        )

    print()

    print(f"Review sheet: {OUTPUT_PATH}")
    print(f"Batch directory: {BATCH_DIR}")
    print(f"Manifest: {MANIFEST_PATH}")

    print()

    print("IMPORTANT:")
    print(
        "No atom predictions have been generated."
    )
    print(
        "Ground Truth must be frozen before "
        "running Claim Atomizer v0.4."
    )


if __name__ == "__main__":
    main()