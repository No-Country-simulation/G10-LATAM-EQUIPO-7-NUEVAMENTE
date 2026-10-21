from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


SEED = 20261021
SOURCE_REFERENCE = "data_science/pandas_groupby.txt"

BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

RAW_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_candidates_v1.csv"
)

ORIGINAL_POOL_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_review_pool_hygiene_v1.csv"
)

ROUND1_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacements_v1.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacement_round2_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_hygiene_replacement_round2_manifest_v1.json"
)


def stable_seed() -> int:
    value = (
        f"{SEED}:hygiene-replacement-round2:"
        f"{SOURCE_REFERENCE}"
    ).encode("utf-8")

    digest = hashlib.sha256(value).hexdigest()

    return int(digest[:8], 16)


def main() -> None:
    raw = pd.read_csv(RAW_PATH)
    original = pd.read_csv(ORIGINAL_POOL_PATH)
    round1 = pd.read_csv(ROUND1_PATH)

    # Exclude everything already examined, including
    # candidates rejected as noise.
    used_ids = set(
        original["source_claim_id"]
        .dropna()
        .astype(str)
    )

    used_ids.update(
        round1["source_claim_id"]
        .dropna()
        .astype(str)
    )

    available = raw[
        (raw["source_reference"] == SOURCE_REFERENCE)
        & (
            ~raw["source_claim_id"]
            .astype(str)
            .isin(used_ids)
        )
    ].copy()

    if available.empty:
        raise ValueError(
            "No unused candidates remain for "
            f"{SOURCE_REFERENCE}"
        )

    candidate = available.sample(
        n=1,
        replace=False,
        random_state=stable_seed(),
    ).copy()

    candidate.insert(
        0,
        "replacement_id",
        ["EXT-REPL2-V1-001"],
    )

    candidate["hygiene_status"] = "needs_review"
    candidate["hygiene_notes"] = ""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "artifact": (
            "external_claim_hygiene_replacement_round2_v1"
        ),
        "status": (
            "replacement_candidate_not_adjudicated"
        ),
        "seed": SEED,
        "source_reference": SOURCE_REFERENCE,
        "replacement_count": 1,
        "selection_strategy": (
            "deterministic sampling from source candidates "
            "not previously reviewed in original pool or "
            "replacement round 1"
        ),
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "ground_truth_used": False,
        "human_hygiene_review_required": True,
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

    print("External Hygiene Replacement Round 2 v1")
    print("========================================")
    print(
        candidate[
            [
                "replacement_id",
                "source_claim_id",
                "source_domain",
                "source_reference",
                "claim_text",
            ]
        ].to_string(index=False)
    )

    print()
    print("Unused candidates remaining:", len(available) - 1)
    print(f"Output: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    print()
    print(
        "Do not merge this candidate until "
        "human hygiene review is complete."
    )


if __name__ == "__main__":
    main()