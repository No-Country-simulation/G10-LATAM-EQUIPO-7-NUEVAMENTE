from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


SEED = 20261021

BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

RAW_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_candidates_v1.csv"
)

ADJUDICATED_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_structural_review_adjudicated_v1.csv"
)

EXPANSION_V1_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_compound_expansion_pool_v1.csv"
)

EXPANSION_V2_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_compound_expansion_pool_v2.csv"
)

ORIGINAL_POOL_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_review_pool_v1.csv"
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
    / "external_claim_compound_expansion_pool_v3.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_compound_expansion_pool_manifest_v3.json"
)

TARGET_TOTAL = 10
TARGET_PER_DOMAIN = 2

EXPECTED_DOMAINS = {
    "ai",
    "backend",
    "cloud_devops",
    "data_science",
    "frontend",
}


def stable_seed(domain: str) -> int:
    value = (
        f"{SEED}:compound-expansion-v3:{domain}"
    ).encode("utf-8")

    digest = hashlib.sha256(value).hexdigest()

    return int(digest[:8], 16)


def collect_used_ids() -> set[str]:
    used_ids: set[str] = set()

    paths = [
        ORIGINAL_POOL_PATH,
        ROUND1_PATH,
        ROUND2_PATH,
        ROUND3_PATH,
        ROUND4_PATH,
        ROUND5_PATH,
        ADJUDICATED_PATH,
        EXPANSION_V1_PATH,
        EXPANSION_V2_PATH,
    ]

    for path in paths:
        if not path.exists():
            continue

        df = pd.read_csv(
            path,
            keep_default_na=False,
        )

        if "source_claim_id" not in df.columns:
            continue

        ids = (
            df["source_claim_id"]
            .astype(str)
            .str.strip()
        )

        used_ids.update(
            value
            for value in ids
            if value
        )

    return used_ids


def main() -> None:
    raw = pd.read_csv(
        RAW_PATH,
        keep_default_na=False,
    )

    required_columns = {
        "source_claim_id",
        "claim_text",
        "source_domain",
        "source_reference",
    }

    missing = required_columns - set(raw.columns)

    if missing:
        raise ValueError(
            "Missing required raw candidate columns: "
            + ", ".join(sorted(missing))
        )

    used_ids = collect_used_ids()

    available = raw[
        ~raw["source_claim_id"]
        .astype(str)
        .isin(used_ids)
    ].copy()

    available_domains = set(
        available["source_domain"]
        .dropna()
        .astype(str)
        .unique()
    )

    if available_domains != EXPECTED_DOMAINS:
        raise ValueError(
            "Unexpected available domain set. "
            f"Expected={sorted(EXPECTED_DOMAINS)}, "
            f"Found={sorted(available_domains)}"
        )

    selected_frames = []

    for domain in sorted(EXPECTED_DOMAINS):
        domain_pool = available[
            available["source_domain"] == domain
        ].copy()

        if len(domain_pool) < TARGET_PER_DOMAIN:
            raise ValueError(
                f"Not enough unused candidates for {domain}: "
                f"{len(domain_pool)} available."
            )

        sampled = domain_pool.sample(
            n=TARGET_PER_DOMAIN,
            replace=False,
            random_state=stable_seed(domain),
        ).copy()

        selected_frames.append(sampled)

    expansion = pd.concat(
        selected_frames,
        ignore_index=True,
        sort=False,
    )

    expansion = expansion.sort_values(
        [
            "source_domain",
            "source_reference",
            "source_claim_id",
        ]
    ).reset_index(drop=True)

    expansion.insert(
        0,
        "expansion_id",
        [
            f"EXT-COMP3-V1-{i:03d}"
            for i in range(1, len(expansion) + 1)
        ],
    )

    expansion["hygiene_status"] = "needs_review"
    expansion["hygiene_notes"] = ""

    expansion["target_bucket"] = "needs_review"
    expansion["relation_subtype"] = ""
    expansion["review_status"] = "pending"
    expansion["review_notes"] = ""

    # -------------------------
    # Integrity checks
    # -------------------------

    if len(expansion) != TARGET_TOTAL:
        raise ValueError(
            f"Expected {TARGET_TOTAL} candidates; "
            f"found {len(expansion)}."
        )

    if expansion["source_claim_id"].duplicated().any():
        raise ValueError(
            "Duplicate source_claim_id values found "
            "inside expansion pool v3."
        )

    overlap = (
        set(expansion["source_claim_id"])
        & used_ids
    )

    if overlap:
        raise ValueError(
            "Expansion pool v3 overlaps previously "
            f"reviewed IDs: {sorted(overlap)}"
        )

    domain_counts = (
        expansion["source_domain"]
        .value_counts()
        .sort_index()
    )

    if not (
        domain_counts == TARGET_PER_DOMAIN
    ).all():
        raise ValueError(
            "Expected exactly "
            f"{TARGET_PER_DOMAIN} candidates per domain:\n"
            + domain_counts.to_string()
        )

    # -------------------------
    # Write pool
    # -------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    expansion.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # -------------------------
    # Manifest
    # -------------------------

    manifest = {
        "artifact": (
            "external_claim_compound_expansion_pool_v3"
        ),
        "status": "blind_human_review_pending",
        "purpose": (
            "Third blind expansion because exactly one "
            "additional human-adjudicated compound claim "
            "is still required for the balanced dataset."
        ),
        "seed": SEED,
        "total_candidates": int(len(expansion)),
        "candidates_per_domain": TARGET_PER_DOMAIN,
        "domain_counts": {
            key: int(value)
            for key, value
            in domain_counts.items()
        },
        "selection_strategy": (
            "Deterministic domain-balanced sampling from "
            "unused raw external candidates."
        ),
        "previously_seen_ids_excluded": int(
            len(used_ids)
        ),
        "compound_deficit_before_expansion": 1,
        "selection_does_not_use_target_bucket": True,
        "selection_does_not_use_claim_atomizer": True,
        "selection_does_not_use_llm": True,
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "predictions_available_to_reviewer": False,
        "ground_truth_used_for_selection": False,
        "production_impact": False,
        "human_hygiene_review_required": True,
        "human_structural_review_required": True,
        "stop_condition": (
            "At least 1 additional human-adjudicated "
            "compound claim is available."
        ),
        "next_stage": (
            "human hygiene review followed by human "
            "structural bucket adjudication"
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
        "External Compound Expansion Pool v3"
    )
    print(
        "==================================="
    )

    print(
        "Previously seen source_claim_ids:",
        len(used_ids),
    )

    print(
        "Unused raw candidates:",
        len(available),
    )

    print(
        "Expansion candidates:",
        len(expansion),
    )

    print()

    print("By domain:")
    print(domain_counts.to_string())

    print()

    print(
        expansion[
            [
                "expansion_id",
                "source_claim_id",
                "source_domain",
                "source_reference",
                "claim_text",
            ]
        ].to_string(index=False)
    )

    print()

    print(f"Output: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")

    print()
    print("IMPORTANT:")
    print(
        "This pool was selected without LLM output, "
        "Claim Atomizer predictions, or human target buckets."
    )
    print(
        "Perform hygiene review before structural adjudication."
    )


if __name__ == "__main__":
    main()