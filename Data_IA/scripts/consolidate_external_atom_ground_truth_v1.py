from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

FROZEN_DATASET_PATH = (
    BASE_DIR
    / "dataset"
    / "external_claim_balanced_dataset_v1.csv"
)

REVIEW_BATCH_DIR = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
)

CASE_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "external_atom_ground_truth_cases_v1.csv"
)

ATOM_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "external_atom_ground_truth_atoms_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_atom_ground_truth_manifest_v1.json"
)


EXPECTED_CASES = 80
EXPECTED_ATOMS = 88
EXPECTED_BATCHES = 8

EXPECTED_BUCKET_COUNTS = {
    "atomic": 20,
    "compound": 20,
    "non_propositional": 20,
    "relational": 20,
}

ALLOWED_ATOM_TYPES = {
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
}


def batch_review_path(
    batch_number: int,
) -> Path:
    return (
        REVIEW_BATCH_DIR
        / (
            "external_atom_gt_review_"
            f"batch_{batch_number:02d}_v1.csv"
        )
    )


def batch_atoms_path(
    batch_number: int,
) -> Path:
    return (
        REVIEW_BATCH_DIR
        / (
            "external_atom_gt_atoms_"
            f"batch_{batch_number:02d}_v1.csv"
        )
    )


def load_frozen_dataset() -> pd.DataFrame:
    if not FROZEN_DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Missing frozen dataset: {FROZEN_DATASET_PATH}"
        )

    df = pd.read_csv(
        FROZEN_DATASET_PATH,
        keep_default_na=False,
    )

    if len(df) != EXPECTED_CASES:
        raise ValueError(
            f"Frozen dataset must contain {EXPECTED_CASES} cases; "
            f"found {len(df)}."
        )

    if df["external_case_id"].duplicated().any():
        raise ValueError(
            "Duplicate external_case_id values in frozen dataset."
        )

    return df


def load_review_batches() -> pd.DataFrame:
    frames = []

    for batch_number in range(
        1,
        EXPECTED_BATCHES + 1,
    ):
        path = batch_review_path(batch_number)

        if not path.exists():
            raise FileNotFoundError(
                f"Missing review batch {batch_number:02d}: {path}"
            )

        df = pd.read_csv(
            path,
            keep_default_na=False,
        )

        if len(df) != 10:
            raise ValueError(
                f"Batch {batch_number:02d} must contain 10 cases; "
                f"found {len(df)}."
            )

        df["gt_batch"] = batch_number
        frames.append(df)

    cases = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )

    return cases


def load_atom_batches() -> pd.DataFrame:
    frames = []

    expected_columns = [
        "external_case_id",
        "atom_index",
        "atom_text",
        "atom_type",
        "gt_review_status",
    ]

    for batch_number in range(
        1,
        EXPECTED_BATCHES + 1,
    ):
        path = batch_atoms_path(batch_number)

        if not path.exists():
            raise FileNotFoundError(
                f"Missing atom batch {batch_number:02d}: {path}"
            )

        df = pd.read_csv(
            path,
            keep_default_na=False,
        )

        missing = (
            set(expected_columns)
            - set(df.columns)
        )

        if missing:
            raise ValueError(
                f"Atom batch {batch_number:02d} missing columns: "
                + ", ".join(sorted(missing))
            )

        df = df[
            expected_columns
        ].copy()

        df["gt_batch"] = batch_number
        frames.append(df)

    atoms = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )

    return atoms


def validate_case_level(
    cases: pd.DataFrame,
    frozen: pd.DataFrame,
) -> None:
    if len(cases) != EXPECTED_CASES:
        raise ValueError(
            f"Expected {EXPECTED_CASES} Ground Truth cases; "
            f"found {len(cases)}."
        )

    if cases["external_case_id"].duplicated().any():
        duplicates = cases.loc[
            cases["external_case_id"].duplicated(
                keep=False
            ),
            [
                "external_case_id",
                "gt_batch",
            ],
        ]

        raise ValueError(
            "Duplicate Ground Truth case IDs:\n"
            + duplicates.to_string(index=False)
        )

    if (
        cases["gt_review_status"]
        != "reviewed"
    ).any():
        pending = cases.loc[
            cases["gt_review_status"]
            != "reviewed",
            [
                "external_case_id",
                "gt_batch",
                "gt_review_status",
            ],
        ]

        raise ValueError(
            "Ground Truth contains non-reviewed cases:\n"
            + pending.to_string(index=False)
        )

    counts = pd.to_numeric(
        cases["expected_atom_count"],
        errors="coerce",
    )

    if counts.isna().any():
        invalid = cases.loc[
            counts.isna(),
            [
                "external_case_id",
                "expected_atom_count",
            ],
        ]

        raise ValueError(
            "Invalid expected_atom_count values:\n"
            + invalid.to_string(index=False)
        )

    cases["expected_atom_count"] = (
        counts.astype(int)
    )

    # Frozen dataset membership must match exactly.
    frozen_ids = set(
        frozen["external_case_id"]
    )

    gt_ids = set(
        cases["external_case_id"]
    )

    if frozen_ids != gt_ids:
        raise ValueError(
            "Ground Truth case IDs do not match frozen dataset. "
            f"Missing={sorted(frozen_ids - gt_ids)}, "
            f"Unexpected={sorted(gt_ids - frozen_ids)}"
        )

    # Preserve frozen claim text exactly.
    comparison = cases[
        [
            "external_case_id",
            "claim_text_final",
            "target_bucket",
            "relation_subtype",
        ]
    ].merge(
        frozen[
            [
                "external_case_id",
                "claim_text_final",
                "target_bucket",
                "relation_subtype",
            ]
        ],
        on="external_case_id",
        how="inner",
        suffixes=("_gt", "_frozen"),
    )

    for column in [
        "claim_text_final",
        "target_bucket",
        "relation_subtype",
    ]:
        mismatch = (
            comparison[f"{column}_gt"]
            != comparison[f"{column}_frozen"]
        )

        if mismatch.any():
            bad = comparison.loc[
                mismatch,
                [
                    "external_case_id",
                    f"{column}_gt",
                    f"{column}_frozen",
                ],
            ]

            raise ValueError(
                f"Ground Truth changed frozen field {column}:\n"
                + bad.to_string(index=False)
            )

    bucket_counts = (
        cases["target_bucket"]
        .value_counts()
        .to_dict()
    )

    if bucket_counts != EXPECTED_BUCKET_COUNTS:
        raise ValueError(
            "Unexpected Ground Truth bucket counts. "
            f"Expected={EXPECTED_BUCKET_COUNTS}, "
            f"Found={bucket_counts}"
        )

    # Structural consistency.
    atomic = (
        cases["target_bucket"]
        == "atomic"
    )

    compound = (
        cases["target_bucket"]
        == "compound"
    )

    non_prop = (
        cases["target_bucket"]
        == "non_propositional"
    )

    relational = (
        cases["target_bucket"]
        == "relational"
    )

    if (
        cases.loc[
            atomic,
            "expected_atom_count",
        ]
        != 1
    ).any():
        raise ValueError(
            "Every atomic case must have exactly 1 expected atom."
        )

    if (
        cases.loc[
            compound,
            "expected_atom_count",
        ]
        < 2
    ).any():
        raise ValueError(
            "Every compound case must have at least 2 expected atoms."
        )

    if (
        cases.loc[
            non_prop,
            "expected_atom_count",
        ]
        != 0
    ).any():
        raise ValueError(
            "Every non-propositional case must have 0 expected atoms."
        )

    if (
        cases.loc[
            relational,
            "expected_atom_count",
        ]
        != 1
    ).any():
        raise ValueError(
            "Every relational case must have exactly 1 expected atom "
            "under external Ground Truth v1."
        )


def validate_atoms(
    cases: pd.DataFrame,
    atoms: pd.DataFrame,
) -> None:
    if len(atoms) != EXPECTED_ATOMS:
        raise ValueError(
            f"Expected {EXPECTED_ATOMS} total atom rows; "
            f"found {len(atoms)}."
        )

    if atoms["external_case_id"].eq("").any():
        raise ValueError(
            "Atom rows with empty external_case_id found."
        )

    if atoms["atom_text"].astype(str).str.strip().eq("").any():
        raise ValueError(
            "Empty atom_text values found."
        )

    unexpected_types = (
        set(atoms["atom_type"])
        - ALLOWED_ATOM_TYPES
    )

    if unexpected_types:
        raise ValueError(
            "Unexpected atom types: "
            + ", ".join(sorted(unexpected_types))
        )

    if (
        atoms["gt_review_status"]
        != "reviewed"
    ).any():
        raise ValueError(
            "All atom rows must have gt_review_status=reviewed."
        )

    atom_indices = pd.to_numeric(
        atoms["atom_index"],
        errors="coerce",
    )

    if atom_indices.isna().any():
        raise ValueError(
            "Invalid atom_index values found."
        )

    atoms["atom_index"] = (
        atom_indices.astype(int)
    )

    if (
        atoms["atom_index"]
        < 1
    ).any():
        raise ValueError(
            "atom_index must start at 1."
        )

    duplicate_keys = atoms.duplicated(
        subset=[
            "external_case_id",
            "atom_index",
        ],
        keep=False,
    )

    if duplicate_keys.any():
        bad = atoms.loc[
            duplicate_keys,
            [
                "external_case_id",
                "atom_index",
                "atom_text",
            ],
        ]

        raise ValueError(
            "Duplicate case/index atom rows:\n"
            + bad.to_string(index=False)
        )

    case_ids = set(
        cases["external_case_id"]
    )

    atom_case_ids = set(
        atoms["external_case_id"]
    )

    unexpected_atom_cases = (
        atom_case_ids - case_ids
    )

    if unexpected_atom_cases:
        raise ValueError(
            "Atom rows reference unknown cases: "
            + ", ".join(
                sorted(unexpected_atom_cases)
            )
        )

    actual_counts = (
        atoms.groupby(
            "external_case_id"
        )
        .size()
        .to_dict()
    )

    for _, row in cases.iterrows():
        case_id = row["external_case_id"]

        expected_count = int(
            row["expected_atom_count"]
        )

        actual_count = int(
            actual_counts.get(
                case_id,
                0,
            )
        )

        if actual_count != expected_count:
            raise ValueError(
                f"{case_id}: expected "
                f"{expected_count} atom rows, "
                f"found {actual_count}."
            )

        if expected_count > 0:
            case_atoms = (
                atoms.loc[
                    atoms["external_case_id"]
                    == case_id
                ]
                .sort_values(
                    "atom_index"
                )
            )

            expected_indices = list(
                range(
                    1,
                    expected_count + 1,
                )
            )

            actual_indices = (
                case_atoms["atom_index"]
                .tolist()
            )

            if (
                actual_indices
                != expected_indices
            ):
                raise ValueError(
                    f"{case_id}: atom indices must be "
                    f"{expected_indices}, found "
                    f"{actual_indices}."
                )

    # For relational cases with one atom,
    # atom type must equal structural subtype.
    relational_cases = cases.loc[
        cases["target_bucket"]
        == "relational",
        [
            "external_case_id",
            "relation_subtype",
        ],
    ]

    relational_atoms = (
        relational_cases.merge(
            atoms[
                [
                    "external_case_id",
                    "atom_type",
                ]
            ],
            on="external_case_id",
            how="left",
        )
    )

    mismatch = (
        relational_atoms[
            "relation_subtype"
        ]
        != relational_atoms[
            "atom_type"
        ]
    )

    if mismatch.any():
        bad = relational_atoms.loc[
            mismatch,
            [
                "external_case_id",
                "relation_subtype",
                "atom_type",
            ],
        ]

        raise ValueError(
            "Relational atom type does not match "
            "frozen relation subtype:\n"
            + bad.to_string(index=False)
        )


def main() -> None:
    print(
        "External Atom Ground Truth Consolidation v1"
    )
    print(
        "=========================================="
    )
    print()

    frozen = load_frozen_dataset()

    cases = load_review_batches()

    atoms = load_atom_batches()

    validate_case_level(
        cases,
        frozen,
    )

    validate_atoms(
        cases,
        atoms,
    )

    # Canonical ordering.
    cases = cases.sort_values(
        "external_case_id"
    ).reset_index(drop=True)

    atoms = atoms.sort_values(
        [
            "external_case_id",
            "atom_index",
        ]
    ).reset_index(drop=True)

    CASE_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cases.to_csv(
        CASE_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    atoms.to_csv(
        ATOM_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    bucket_counts = (
        cases["target_bucket"]
        .value_counts()
        .reindex(
            [
                "atomic",
                "compound",
                "relational",
                "non_propositional",
            ]
        )
    )

    atom_type_counts = (
        atoms["atom_type"]
        .value_counts()
        .sort_index()
    )

    atoms_by_bucket = (
        cases.groupby(
            "target_bucket"
        )["expected_atom_count"]
        .sum()
        .reindex(
            [
                "atomic",
                "compound",
                "relational",
                "non_propositional",
            ]
        )
    )

    relational_subtypes = (
        cases.loc[
            cases["target_bucket"]
            == "relational",
            "relation_subtype",
        ]
        .value_counts()
        .sort_index()
    )

    manifest = {
        "artifact": (
            "external_atom_ground_truth_v1"
        ),
        "status": "frozen_candidate",
        "source_dataset": str(
            FROZEN_DATASET_PATH
        ),
        "case_ground_truth": str(
            CASE_OUTPUT_PATH
        ),
        "atom_ground_truth": str(
            ATOM_OUTPUT_PATH
        ),
        "total_cases": int(
            len(cases)
        ),
        "total_atoms": int(
            len(atoms)
        ),
        "bucket_counts": {
            key: int(value)
            for key, value
            in bucket_counts.items()
        },
        "atoms_by_bucket": {
            key: int(value)
            for key, value
            in atoms_by_bucket.items()
        },
        "atom_type_counts": {
            key: int(value)
            for key, value
            in atom_type_counts.items()
        },
        "relational_subtype_counts": {
            key: int(value)
            for key, value
            in relational_subtypes.items()
        },
        "review_status": "complete",
        "human_ground_truth": True,
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "predictions_available_to_reviewer": False,
        "frozen_dataset_modified": False,
        "production_impact": False,
        "limitations": [
            (
                "Ground Truth was created with assistant-assisted "
                "human adjudication."
            ),
            (
                "The selected relational set contains no "
                "scope_or_quantifier structural cases."
            ),
            (
                "Atom text may normalize obvious extraction spacing "
                "errors but does not modify the frozen source claims."
            ),
        ],
        "next_stage": (
            "freeze Ground Truth in Git before running "
            "Claim Atomizer v0.4 predictions"
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
        "Cases:",
        len(cases),
    )

    print(
        "Atoms:",
        len(atoms),
    )

    print()

    print("Buckets:")
    print(
        bucket_counts.to_string()
    )

    print()
    print("Atoms by bucket:")
    print(
        atoms_by_bucket.to_string()
    )

    print()
    print("Atom types:")
    print(
        atom_type_counts.to_string()
    )

    print()
    print("Relational subtypes:")
    print(
        relational_subtypes.to_string()
    )

    print()
    print(
        "Reviewed cases:",
        int(
            (
                cases["gt_review_status"]
                == "reviewed"
            ).sum()
        ),
    )

    print(
        "Pending cases:",
        int(
            (
                cases["gt_review_status"]
                != "reviewed"
            ).sum()
        ),
    )

    print()
    print(
        f"Case Ground Truth: {CASE_OUTPUT_PATH}"
    )
    print(
        f"Atom Ground Truth: {ATOM_OUTPUT_PATH}"
    )
    print(
        f"Manifest: {MANIFEST_PATH}"
    )

    print()
    print("PASS:")
    print(
        "All 80 human Ground Truth cases are complete "
        "and internally consistent."
    )
    print(
        "All expected atom counts match the long-form "
        "atom Ground Truth."
    )

    print()
    print("IMPORTANT:")
    print(
        "Claim Atomizer v0.4 has still not been run "
        "on this benchmark."
    )
    print(
        "Freeze this Ground Truth in Git before "
        "generating predictions."
    )


if __name__ == "__main__":
    main()