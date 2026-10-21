from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


SEED = 20261021
PER_SOURCE = 8

BASE_DIR = Path("data/evaluation/atomization_external_v1")

INPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_candidates_v1.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_review_pool_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_review_pool_manifest_v1.json"
)


def deterministic_seed(source_reference: str) -> int:
    """
    Build a stable per-source seed.

    Do not use Python's built-in hash(), because its value can
    vary between interpreter sessions.
    """
    value = f"{SEED}:{source_reference}".encode("utf-8")
    digest = hashlib.sha256(value).hexdigest()
    return int(digest[:8], 16)


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {INPUT_PATH}"
        )

    df = pd.read_csv(INPUT_PATH)

    required_columns = {
        "source_claim_id",
        "claim_text",
        "source_domain",
        "source_reference",
        "format",
        "target_bucket",
        "selection_status",
        "notes",
    }

    missing = required_columns.difference(df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    # The review pool must be generated only from the untouched
    # extraction output.
    source_counts = (
        df.groupby(
            ["source_domain", "source_reference"]
        )
        .size()
        .reset_index(name="candidate_count")
    )

    insufficient = source_counts[
        source_counts["candidate_count"] < PER_SOURCE
    ]

    if not insufficient.empty:
        raise ValueError(
            "At least one source has fewer than "
            f"{PER_SOURCE} candidates:\n"
            f"{insufficient.to_string(index=False)}"
        )

    sampled_parts: list[pd.DataFrame] = []

    ordered_sources = sorted(
        df["source_reference"].dropna().unique()
    )

    for source_reference in ordered_sources:
        source_df = df[
            df["source_reference"] == source_reference
        ].copy()

        random_state = deterministic_seed(source_reference)

        sampled = source_df.sample(
            n=PER_SOURCE,
            replace=False,
            random_state=random_state,
        ).copy()

        # Stable ordering inside each source after sampling.
        sampled = sampled.sort_values(
            "source_claim_id"
        )

        sampled_parts.append(sampled)

    review_pool = pd.concat(
        sampled_parts,
        ignore_index=True,
    )

    # New ID belongs to the review pool.
    review_pool.insert(
        0,
        "review_id",
        [
            f"EXT-REV-V1-{i:03d}"
            for i in range(1, len(review_pool) + 1)
        ],
    )

    # These remain intentionally unresolved until human review.
    review_pool["format"] = "needs_review"
    review_pool["target_bucket"] = "needs_review"
    review_pool["selection_status"] = "needs_review"

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    review_pool.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    domain_counts = (
        review_pool["source_domain"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    source_output_counts = (
        review_pool["source_reference"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    manifest = {
        "artifact": "external_claim_review_pool_v1",
        "status": "review_pool_built_not_human_labeled",
        "seed": SEED,
        "sampling_strategy": (
            "deterministic stratified sampling by source_reference"
        ),
        "candidates_per_source": PER_SOURCE,
        "input_candidate_count": int(len(df)),
        "source_count": int(
            review_pool["source_reference"].nunique()
        ),
        "review_pool_count": int(len(review_pool)),
        "domain_counts": {
            str(k): int(v)
            for k, v in domain_counts.items()
        },
        "source_counts": {
            str(k): int(v)
            for k, v in source_output_counts.items()
        },
        "human_review_required": [
            "format",
            "target_bucket",
            "selection_status",
        ],
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "ground_truth_used": False,
        "notes": [
            (
                "The raw extraction artifact is preserved unchanged."
            ),
            (
                "No claim type or model prediction was used "
                "during sampling."
            ),
            (
                "Human classification occurs only after this "
                "review pool is frozen."
            ),
        ],
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

    print("External Claim Review Pool v1")
    print("================================")
    print(f"Input candidates: {len(df)}")
    print(f"Sources: {review_pool['source_reference'].nunique()}")
    print(f"Candidates/source: {PER_SOURCE}")
    print(f"Review pool: {len(review_pool)}")
    print()
    print("By domain:")
    print(
        review_pool["source_domain"]
        .value_counts()
        .sort_index()
        .to_string()
    )
    print()
    print(f"Output: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    print()
    print("IMPORTANT:")
    print("No model predictions were used.")
    print("Do not run Claim Atomizer v0.4 yet.")
    print(
        "Human review of target_bucket and "
        "selection_status comes next."
    )


if __name__ == "__main__":
    main()