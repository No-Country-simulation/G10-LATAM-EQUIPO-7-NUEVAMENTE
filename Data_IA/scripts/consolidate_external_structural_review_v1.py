from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

BATCH_DIR = (
    BASE_DIR
    / "review_batches"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_structural_review_adjudicated_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_structural_review_adjudicated_manifest_v1.json"
)

EXPECTED_BATCHES = 6
EXPECTED_ROWS = 120

ALLOWED_BUCKETS = {
    "atomic",
    "compound",
    "relational",
    "non_propositional",
}

ALLOWED_RELATION_SUBTYPES = {
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
}

TARGET_PER_BUCKET = 20


def load_batches() -> pd.DataFrame:
    frames = []

    for batch_number in range(1, EXPECTED_BATCHES + 1):
        path = (
            BATCH_DIR
            / (
                "external_structural_review_"
                f"batch_{batch_number:02d}_v1.csv"
            )
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Missing review batch: {path}"
            )

        df = pd.read_csv(
            path,
            keep_default_na=False,
        )

        df["review_batch"] = batch_number
        frames.append(df)

    return pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )


def validate_review(df: pd.DataFrame) -> None:
    if len(df) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS} reviewed rows; "
            f"found {len(df)}."
        )

    if df["external_review_id"].duplicated().any():
        duplicates = df.loc[
            df["external_review_id"].duplicated(
                keep=False
            ),
            "external_review_id",
        ]

        raise ValueError(
            "Duplicate external_review_id values:\n"
            + duplicates.to_string(index=False)
        )

    if df["source_claim_id"].duplicated().any():
        duplicates = df.loc[
            df["source_claim_id"].duplicated(
                keep=False
            ),
            "source_claim_id",
        ]

        raise ValueError(
            "Duplicate source_claim_id values:\n"
            + duplicates.to_string(index=False)
        )

    if (df["review_status"] != "reviewed").any():
        pending = df.loc[
            df["review_status"] != "reviewed",
            [
                "external_review_id",
                "review_status",
            ],
        ]

        raise ValueError(
            "Some rows are not fully reviewed:\n"
            + pending.to_string(index=False)
        )

    unexpected_buckets = (
        set(df["target_bucket"])
        - ALLOWED_BUCKETS
    )

    if unexpected_buckets:
        raise ValueError(
            "Unexpected target buckets: "
            + ", ".join(
                sorted(unexpected_buckets)
            )
        )

    relational = (
        df["target_bucket"] == "relational"
    )

    if (
        relational
        & (df["relation_subtype"] == "")
    ).any():
        bad = df.loc[
            relational
            & (df["relation_subtype"] == ""),
            ["external_review_id"],
        ]

        raise ValueError(
            "Relational claims missing subtype:\n"
            + bad.to_string(index=False)
        )

    invalid_relational_subtypes = set(
        df.loc[
            relational,
            "relation_subtype",
        ]
    ) - ALLOWED_RELATION_SUBTYPES

    if invalid_relational_subtypes:
        raise ValueError(
            "Unexpected relation subtypes: "
            + ", ".join(
                sorted(
                    invalid_relational_subtypes
                )
            )
        )

    if (
        (~relational)
        & (df["relation_subtype"] != "")
    ).any():
        bad = df.loc[
            (~relational)
            & (df["relation_subtype"] != ""),
            [
                "external_review_id",
                "target_bucket",
                "relation_subtype",
            ],
        ]

        raise ValueError(
            "Non-relational claims must not have "
            "relation_subtype:\n"
            + bad.to_string(index=False)
        )

    expected_ids = {
        f"EXT-POOL-V1-{i:03d}"
        for i in range(1, EXPECTED_ROWS + 1)
    }

    actual_ids = set(
        df["external_review_id"]
    )

    if actual_ids != expected_ids:
        missing = expected_ids - actual_ids
        unexpected = actual_ids - expected_ids

        raise ValueError(
            "Review IDs do not match frozen pool. "
            f"Missing={sorted(missing)}, "
            f"Unexpected={sorted(unexpected)}"
        )


def main() -> None:
    df = load_batches()

    validate_review(df)

    df = df.sort_values(
        "external_review_id"
    ).reset_index(drop=True)

    bucket_counts = (
        df["target_bucket"]
        .value_counts()
        .reindex(
            [
                "atomic",
                "compound",
                "relational",
                "non_propositional",
            ],
            fill_value=0,
        )
    )

    relational = df[
        df["target_bucket"] == "relational"
    ].copy()

    subtype_counts = (
        relational["relation_subtype"]
        .value_counts()
        .reindex(
            [
                "temporal_relation",
                "causal_relation",
                "conditional_relation",
                "comparative_relation",
                "negation_or_absence",
                "scope_or_quantifier",
            ],
            fill_value=0,
        )
    )

    deficits = {
        bucket: max(
            0,
            TARGET_PER_BUCKET - int(count),
        )
        for bucket, count
        in bucket_counts.items()
    }

    surpluses = {
        bucket: max(
            0,
            int(count) - TARGET_PER_BUCKET,
        )
        for bucket, count
        in bucket_counts.items()
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "artifact": (
            "external_claim_structural_review_"
            "adjudicated_v1"
        ),
        "status": (
            "human_structural_review_complete"
        ),
        "total_claims": int(len(df)),
        "review_batches": EXPECTED_BATCHES,
        "review_status": "complete",
        "bucket_counts": {
            key: int(value)
            for key, value
            in bucket_counts.items()
        },
        "relation_subtype_counts": {
            key: int(value)
            for key, value
            in subtype_counts.items()
        },
        "target_per_bucket": TARGET_PER_BUCKET,
        "bucket_deficits": deficits,
        "bucket_surpluses": surpluses,
        "balanced_dataset_ready": (
            all(
                count >= TARGET_PER_BUCKET
                for count
                in bucket_counts.values
            )
        ),
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "predictions_available_to_reviewer": False,
        "ground_truth_status": (
            "structural_buckets_human_adjudicated"
        ),
        "production_impact": False,
        "next_stage": (
            "expand human-reviewed candidate pool "
            "for structurally underrepresented buckets"
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
        "External Structural Review "
        "Adjudicated v1"
    )
    print(
        "======================================"
    )

    print(f"Claims: {len(df)}")
    print(
        "Reviewed:",
        int(
            (
                df["review_status"]
                == "reviewed"
            ).sum()
        ),
    )

    print()
    print("Bucket distribution:")
    print(bucket_counts.to_string())

    print()
    print("Relation subtype distribution:")
    print(subtype_counts.to_string())

    print()
    print("Deficits to reach 20 per bucket:")

    for bucket, deficit in deficits.items():
        print(
            f"{bucket}: {deficit}"
        )

    print()
    print("Surpluses above 20:")

    for bucket, surplus in surpluses.items():
        print(
            f"{bucket}: {surplus}"
        )

    print()
    print(
        "Balanced dataset ready:",
        manifest["balanced_dataset_ready"],
    )

    print()
    print(f"Output: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")

    print()
    print("IMPORTANT:")
    print(
        "No Claim Atomizer predictions were used."
    )
    print(
        "Do not run v0.4 yet."
    )


if __name__ == "__main__":
    main()