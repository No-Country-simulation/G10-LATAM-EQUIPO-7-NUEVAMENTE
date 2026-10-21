from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


SEED = 20261021

BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

BASE_REVIEW_PATH = (
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

EXPANSION_V3_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_compound_expansion_pool_v3.csv"
)

CONSOLIDATED_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_structural_review_all_v1.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_balanced_dataset_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_balanced_dataset_manifest_v1.json"
)


BUCKETS = [
    "atomic",
    "compound",
    "relational",
    "non_propositional",
]

TARGET_PER_BUCKET = 20
EXPECTED_TOTAL_REVIEWED = 166
EXPECTED_FINAL_TOTAL = 80


def stable_rank(
    bucket: str,
    domain: str,
    source_claim_id: str,
) -> str:
    value = (
        f"{SEED}:balanced-v1:"
        f"{bucket}:{domain}:{source_claim_id}"
    ).encode("utf-8")

    return hashlib.sha256(value).hexdigest()


def effective_text(row: pd.Series) -> str:
    cleaned = str(
        row.get("cleaned_claim_text", "")
    ).strip()

    if cleaned:
        return cleaned

    claim_text_final = str(
        row.get("claim_text_final", "")
    ).strip()

    if claim_text_final:
        return claim_text_final

    return str(
        row.get("claim_text", "")
    ).strip()


def prepare_base() -> pd.DataFrame:
    df = pd.read_csv(
        BASE_REVIEW_PATH,
        keep_default_na=False,
    )

    df["review_origin"] = "base_120"

    return df


def prepare_expansion(
    path: Path,
    origin: str,
) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        keep_default_na=False,
    )

    df = df[
        df["hygiene_status"].isin(
            {"keep", "keep_cleaned"}
        )
    ].copy()

    if (
        df["review_status"]
        != "reviewed"
    ).any():
        raise ValueError(
            f"{origin} contains unreviewed valid cases."
        )

    df["review_origin"] = origin

    return df


def normalize_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    normalized = df.copy()

    normalized["claim_text_final"] = (
        normalized.apply(
            effective_text,
            axis=1,
        )
    )

    if "external_review_id" not in normalized.columns:
        normalized["external_review_id"] = ""

    if "expansion_id" not in normalized.columns:
        normalized["expansion_id"] = ""

    if "hygiene_status" not in normalized.columns:
        normalized["hygiene_status"] = "keep"

    if "hygiene_notes" not in normalized.columns:
        normalized["hygiene_notes"] = ""

    return normalized


def validate_all(
    df: pd.DataFrame,
) -> None:
    if len(df) != EXPECTED_TOTAL_REVIEWED:
        raise ValueError(
            f"Expected {EXPECTED_TOTAL_REVIEWED} "
            f"human-reviewed valid cases; found {len(df)}."
        )

    if df["source_claim_id"].duplicated().any():
        duplicated = df.loc[
            df["source_claim_id"].duplicated(
                keep=False
            ),
            [
                "source_claim_id",
                "review_origin",
                "claim_text_final",
            ],
        ]

        raise ValueError(
            "Duplicate source_claim_id values:\n"
            + duplicated.to_string(index=False)
        )

    if (
        df["review_status"]
        != "reviewed"
    ).any():
        raise ValueError(
            "Some consolidated cases are not reviewed."
        )

    unexpected = (
        set(df["target_bucket"])
        - set(BUCKETS)
    )

    if unexpected:
        raise ValueError(
            "Unexpected target buckets: "
            + ", ".join(sorted(unexpected))
        )

    relational = (
        df["target_bucket"]
        == "relational"
    )

    if (
        relational
        & (
            df["relation_subtype"]
            .astype(str)
            .str.strip()
            == ""
        )
    ).any():
        raise ValueError(
            "Relational cases missing relation_subtype."
        )

    if (
        (~relational)
        & (
            df["relation_subtype"]
            .astype(str)
            .str.strip()
            != ""
        )
    ).any():
        raise ValueError(
            "Non-relational cases must not have "
            "relation_subtype."
        )

    if (
        df["claim_text_final"]
        .astype(str)
        .str.strip()
        .eq("")
        .any()
    ):
        raise ValueError(
            "Empty claim_text_final values found."
        )


def select_bucket(
    df: pd.DataFrame,
    bucket: str,
) -> pd.DataFrame:
    pool = df[
        df["target_bucket"] == bucket
    ].copy()

    if len(pool) < TARGET_PER_BUCKET:
        raise ValueError(
            f"Bucket {bucket} has only {len(pool)} cases."
        )

    pool["_stable_rank"] = pool.apply(
        lambda row: stable_rank(
            bucket,
            str(row["source_domain"]),
            str(row["source_claim_id"]),
        ),
        axis=1,
    )

    # Stable ordering inside each domain.
    pools_by_domain = {}

    for domain, domain_df in pool.groupby(
        "source_domain",
        sort=True,
    ):
        pools_by_domain[domain] = (
            domain_df
            .sort_values(
                [
                    "_stable_rank",
                    "source_claim_id",
                ]
            )
            .reset_index(drop=True)
        )

    domains = sorted(
        pools_by_domain.keys()
    )

    positions = {
        domain: 0
        for domain in domains
    }

    selected_rows = []

    # Round-robin across domains to encourage
    # source-domain diversity without requiring
    # an artificial fixed quota.
    while len(selected_rows) < TARGET_PER_BUCKET:
        progress = False

        for domain in domains:
            if len(selected_rows) >= TARGET_PER_BUCKET:
                break

            position = positions[domain]
            domain_pool = pools_by_domain[domain]

            if position >= len(domain_pool):
                continue

            selected_rows.append(
                domain_pool.iloc[position]
            )

            positions[domain] += 1
            progress = True

        if not progress:
            raise ValueError(
                f"Unable to select "
                f"{TARGET_PER_BUCKET} cases "
                f"for bucket {bucket}."
            )

    selected = pd.DataFrame(
        selected_rows
    ).copy()

    return selected


def main() -> None:
    frames = [
        normalize_columns(
            prepare_base()
        ),
        normalize_columns(
            prepare_expansion(
                EXPANSION_V1_PATH,
                "compound_expansion_v1",
            )
        ),
        normalize_columns(
            prepare_expansion(
                EXPANSION_V2_PATH,
                "compound_expansion_v2",
            )
        ),
        normalize_columns(
            prepare_expansion(
                EXPANSION_V3_PATH,
                "compound_expansion_v3",
            )
        ),
    ]

    all_reviewed = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )

    validate_all(all_reviewed)

    all_reviewed = all_reviewed.sort_values(
        [
            "target_bucket",
            "source_domain",
            "source_reference",
            "source_claim_id",
        ]
    ).reset_index(drop=True)

    # Preserve the full reviewed universe.
    CONSOLIDATED_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_reviewed.to_csv(
        CONSOLIDATED_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    reviewed_counts = (
        all_reviewed["target_bucket"]
        .value_counts()
        .reindex(
            BUCKETS,
            fill_value=0,
        )
    )

    selected_frames = []

    for bucket in BUCKETS:
        selected_frames.append(
            select_bucket(
                all_reviewed,
                bucket,
            )
        )

    selected = pd.concat(
        selected_frames,
        ignore_index=True,
        sort=False,
    )

    if len(selected) != EXPECTED_FINAL_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_FINAL_TOTAL} "
            f"selected cases; found {len(selected)}."
        )

    if selected["source_claim_id"].duplicated().any():
        raise ValueError(
            "Duplicate selected source_claim_id values."
        )

    selected_counts = (
        selected["target_bucket"]
        .value_counts()
        .reindex(
            BUCKETS,
            fill_value=0,
        )
    )

    if not (
        selected_counts
        == TARGET_PER_BUCKET
    ).all():
        raise ValueError(
            "Final bucket counts are not balanced:\n"
            + selected_counts.to_string()
        )

    selected = selected.sort_values(
        [
            "target_bucket",
            "source_domain",
            "source_reference",
            "source_claim_id",
        ]
    ).reset_index(drop=True)

    selected.insert(
        0,
        "external_case_id",
        [
            f"EXT-VAL-V1-{i:03d}"
            for i in range(
                1,
                len(selected) + 1,
            )
        ],
    )

    selected["selection_status"] = "selected"

    # Remove internal ranking helper if present.
    selected = selected.drop(
        columns=["_stable_rank"],
        errors="ignore",
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    selected.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    domain_counts = (
        selected["source_domain"]
        .value_counts()
        .sort_index()
    )

    bucket_domain_counts = (
        selected.groupby(
            [
                "target_bucket",
                "source_domain",
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    relational_subtypes = (
        selected.loc[
            selected["target_bucket"]
            == "relational",
            "relation_subtype",
        ]
        .value_counts()
        .sort_index()
    )

    manifest = {
        "artifact": (
            "external_claim_balanced_dataset_v1"
        ),
        "status": (
            "selected_human_balanced_dataset_"
            "before_atom_level_ground_truth"
        ),
        "seed": SEED,
        "reviewed_universe_size": int(
            len(all_reviewed)
        ),
        "reviewed_bucket_counts": {
            key: int(value)
            for key, value
            in reviewed_counts.items()
        },
        "selected_total": int(
            len(selected)
        ),
        "selected_per_bucket": TARGET_PER_BUCKET,
        "selected_bucket_counts": {
            key: int(value)
            for key, value
            in selected_counts.items()
        },
        "selection_strategy": (
            "Deterministic stable-hash ordering with "
            "round-robin selection across source domains "
            "within each human-adjudicated structural bucket."
        ),
        "selected_domain_counts": {
            key: int(value)
            for key, value
            in domain_counts.items()
        },
        "selected_relation_subtypes": {
            key: int(value)
            for key, value
            in relational_subtypes.items()
        },
        "human_structural_review_complete": True,
        "atom_level_ground_truth_complete": False,
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "predictions_available_to_reviewer": False,
        "production_impact": False,
        "next_stage": (
            "verify overlap against historical internal "
            "atomization corpus, freeze selected dataset, "
            "then create human atom-level ground truth"
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
        "External Balanced Dataset v1"
    )
    print(
        "============================"
    )

    print()
    print(
        "Reviewed universe:",
        len(all_reviewed),
    )

    print()
    print("Reviewed bucket counts:")
    print(
        reviewed_counts.to_string()
    )

    print()
    print(
        "Selected:",
        len(selected),
    )

    print()
    print("Selected bucket counts:")
    print(
        selected_counts.to_string()
    )

    print()
    print("Selected domain counts:")
    print(
        domain_counts.to_string()
    )

    print()
    print("Bucket x domain:")
    print(
        bucket_domain_counts.to_string()
    )

    print()
    print("Selected relational subtypes:")

    if relational_subtypes.empty:
        print("None")
    else:
        print(
            relational_subtypes.to_string()
        )

    print()
    print(
        f"Consolidated: {CONSOLIDATED_PATH}"
    )
    print(
        f"Selected: {OUTPUT_PATH}"
    )
    print(
        f"Manifest: {MANIFEST_PATH}"
    )

    print()
    print("IMPORTANT:")
    print(
        "The 80-case dataset is structurally balanced "
        "using human labels only."
    )
    print(
        "Claim Atomizer v0.4 has still not been used."
    )
    print(
        "Do not run predictions yet."
    )


if __name__ == "__main__":
    main()