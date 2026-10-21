from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


SEED = 20261021
TARGET_PER_SOURCE = 8

BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

RAW_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_candidates_v1.csv"
)

HYGIENE_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_review_pool_hygiene_v1.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_hygiene_replacements_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_hygiene_replacements_manifest_v1.json"
)


def stable_seed(source_reference: str) -> int:
    value = (
        f"{SEED}:hygiene-replacement:"
        f"{source_reference}"
    ).encode("utf-8")

    digest = hashlib.sha256(value).hexdigest()

    return int(digest[:8], 16)


def main() -> None:
    raw = pd.read_csv(RAW_PATH)
    hygiene = pd.read_csv(HYGIENE_PATH)

    valid_statuses = {
        "keep",
        "keep_cleaned",
    }

    valid = hygiene[
        hygiene["hygiene_status"].isin(valid_statuses)
    ].copy()

    # Determine how many replacements are required
    # for each original source.
    valid_counts = (
        valid.groupby("source_reference")
        .size()
        .to_dict()
    )

    sources = sorted(
        hygiene["source_reference"]
        .dropna()
        .unique()
    )

    needs: dict[str, int] = {}

    for source_reference in sources:
        current = int(
            valid_counts.get(source_reference, 0)
        )

        missing = TARGET_PER_SOURCE - current

        if missing > 0:
            needs[source_reference] = missing

    print("Replacement requirements")
    print("========================")

    for source_reference, missing in needs.items():
        print(
            f"{source_reference}: {missing}"
        )

    print()
    print(
        "Total replacements needed:",
        sum(needs.values()),
    )

    # Exclude every candidate that was already present
    # in the original review pool, including those later
    # rejected as noise.
    used_ids = set(
        hygiene["source_claim_id"]
        .dropna()
        .astype(str)
    )

    replacement_parts: list[pd.DataFrame] = []

    for source_reference, missing in needs.items():
        available = raw[
            (raw["source_reference"] == source_reference)
            & (
                ~raw["source_claim_id"]
                .astype(str)
                .isin(used_ids)
            )
        ].copy()

        if len(available) < missing:
            raise ValueError(
                f"Not enough remaining candidates for "
                f"{source_reference}. "
                f"Need {missing}, available "
                f"{len(available)}."
            )

        # Deterministic selection from candidates that
        # were never included in the first review pool.
        sampled = available.sample(
            n=missing,
            replace=False,
            random_state=stable_seed(
                source_reference
            ),
        ).copy()

        sampled = sampled.sort_values(
            "source_claim_id"
        )

        replacement_parts.append(sampled)

    replacements = pd.concat(
        replacement_parts,
        ignore_index=True,
    )

    replacements.insert(
        0,
        "replacement_id",
        [
            f"EXT-REPL-V1-{i:03d}"
            for i in range(
                1,
                len(replacements) + 1,
            )
        ],
    )

    replacements["hygiene_status"] = (
        "needs_review"
    )

    replacements["hygiene_notes"] = ""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    replacements.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "artifact": (
            "external_claim_hygiene_replacements_v1"
        ),
        "status": (
            "replacement_candidates_not_adjudicated"
        ),
        "seed": SEED,
        "target_per_source": TARGET_PER_SOURCE,
        "replacement_count": int(
            len(replacements)
        ),
        "replacement_needs": {
            str(k): int(v)
            for k, v in needs.items()
        },
        "selection_strategy": (
            "deterministic per-source sampling "
            "from candidates not present in the "
            "original review pool"
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
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("Replacement candidates")
    print("======================")
    print(
        replacements[
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
    print(f"Output: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    print()
    print(
        "IMPORTANT: Do not merge replacements "
        "into the review pool until hygiene "
        "review is complete."
    )


if __name__ == "__main__":
    main()