from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


BASE_DIR = Path(
    "data/evaluation"
)

EXTERNAL_PATH = (
    BASE_DIR
    / "atomization_external_v1"
    / "dataset"
    / "external_claim_balanced_dataset_v1.csv"
)

HISTORICAL_PATHS = {
    "development": (
        BASE_DIR
        / "atomization_v1"
        / "atomization_dataset_v1.csv"
    ),
    "validation": (
        BASE_DIR
        / "atomization_v1"
        / "holdout_v1"
        / "atomization_holdout_dataset_v1.csv"
    ),
    "final_eval": (
        BASE_DIR
        / "atomization_v1"
        / "final_eval_v1"
        / "atomization_final_eval_dataset_v1.csv"
    ),
}

OUTPUT_PATH = (
    BASE_DIR
    / "atomization_external_v1"
    / "results"
    / "external_overlap_audit_v1.csv"
)

MANIFEST_PATH = (
    BASE_DIR
    / "atomization_external_v1"
    / "manifest"
    / "external_overlap_audit_manifest_v1.json"
)

EXPECTED_HISTORICAL_TOTAL = 59
EXPECTED_EXTERNAL_TOTAL = 80


TEXT_COLUMN_CANDIDATES = [
    "claim_text_final",
    "source_claim_text",
    "claim_text",
    "source_text",
    "original_claim",
    "claim",
    "text",
    "input_text",
]


def normalize_text(value: str) -> str:
    text = str(value)

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = text.lower()

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    # Normalize spacing before punctuation.
    text = re.sub(
        r"\s+([,.;:!?])",
        r"\1",
        text,
    )

    return text.strip()


def detect_text_column(
    df: pd.DataFrame,
    label: str,
) -> str:
    for column in TEXT_COLUMN_CANDIDATES:
        if column in df.columns:
            return column

    raise ValueError(
        f"Could not detect text column for {label}. "
        f"Available columns: {list(df.columns)}"
    )


def load_historical() -> pd.DataFrame:
    frames = []

    for partition, path in HISTORICAL_PATHS.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Missing historical dataset: {path}"
            )

        df = pd.read_csv(
            path,
            keep_default_na=False,
        )

        text_column = detect_text_column(
            df,
            partition,
        )

        subset = pd.DataFrame(
            {
                "historical_partition": partition,
                "historical_row": range(
                    1,
                    len(df) + 1,
                ),
                "historical_text": df[text_column]
                .astype(str),
            }
        )

        subset["normalized_text"] = (
            subset["historical_text"]
            .map(normalize_text)
        )

        frames.append(subset)

        print(
            f"{partition}: "
            f"{len(subset)} cases "
            f"(text column: {text_column})"
        )

    historical = pd.concat(
        frames,
        ignore_index=True,
    )

    return historical


def load_external() -> pd.DataFrame:
    if not EXTERNAL_PATH.exists():
        raise FileNotFoundError(
            f"Missing external dataset: {EXTERNAL_PATH}"
        )

    df = pd.read_csv(
        EXTERNAL_PATH,
        keep_default_na=False,
    )

    text_column = detect_text_column(
        df,
        "external",
    )

    if "external_case_id" not in df.columns:
        raise ValueError(
            "External dataset is missing external_case_id."
        )

    external = pd.DataFrame(
        {
            "external_case_id": df[
                "external_case_id"
            ].astype(str),
            "source_claim_id": df[
                "source_claim_id"
            ].astype(str),
            "external_text": df[
                text_column
            ].astype(str),
        }
    )

    external["normalized_text"] = (
        external["external_text"]
        .map(normalize_text)
    )

    print(
        f"external: {len(external)} cases "
        f"(text column: {text_column})"
    )

    return external


def main() -> None:
    print(
        "External Atomization Overlap Audit v1"
    )
    print(
        "====================================="
    )
    print()

    historical = load_historical()

    print()

    external = load_external()

    print()

    # -------------------------
    # Basic counts
    # -------------------------

    if len(historical) != EXPECTED_HISTORICAL_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_HISTORICAL_TOTAL} "
            f"historical cases; found {len(historical)}."
        )

    if len(external) != EXPECTED_EXTERNAL_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_EXTERNAL_TOTAL} "
            f"external cases; found {len(external)}."
        )

    # -------------------------
    # Empty normalized text
    # -------------------------

    if (
        historical["normalized_text"]
        .eq("")
        .any()
    ):
        raise ValueError(
            "Historical dataset contains empty "
            "normalized text."
        )

    if (
        external["normalized_text"]
        .eq("")
        .any()
    ):
        raise ValueError(
            "External dataset contains empty "
            "normalized text."
        )

    # -------------------------
    # Internal duplicate checks
    # -------------------------

    historical_duplicate_count = int(
        historical["normalized_text"]
        .duplicated()
        .sum()
    )

    external_duplicate_count = int(
        external["normalized_text"]
        .duplicated()
        .sum()
    )

    # -------------------------
    # Exact normalized overlap
    # -------------------------

    overlap = external.merge(
        historical,
        on="normalized_text",
        how="inner",
    )

    overlap_count = len(overlap)

    # -------------------------
    # Write audit artifact
    # -------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if overlap.empty:
        audit_output = pd.DataFrame(
            columns=[
                "external_case_id",
                "source_claim_id",
                "external_text",
                "historical_partition",
                "historical_row",
                "historical_text",
                "normalized_text",
            ]
        )
    else:
        audit_output = overlap[
            [
                "external_case_id",
                "source_claim_id",
                "external_text",
                "historical_partition",
                "historical_row",
                "historical_text",
                "normalized_text",
            ]
        ].copy()

    audit_output.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "artifact": (
            "external_overlap_audit_v1"
        ),
        "status": (
            "pass"
            if overlap_count == 0
            and external_duplicate_count == 0
            else "review_required"
        ),
        "historical_partitions": {
            partition: str(path)
            for partition, path
            in HISTORICAL_PATHS.items()
        },
        "historical_total": int(
            len(historical)
        ),
        "external_total": int(
            len(external)
        ),
        "historical_normalized_duplicates": (
            historical_duplicate_count
        ),
        "external_normalized_duplicates": (
            external_duplicate_count
        ),
        "exact_normalized_overlap": int(
            overlap_count
        ),
        "normalization": (
            "Unicode NFKC, lowercase, whitespace "
            "collapse, punctuation-spacing normalization"
        ),
        "semantic_near_duplicate_check": False,
        "claim_atomizer_v0_4_used": False,
        "llm_used": False,
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

    # -------------------------
    # Console summary
    # -------------------------

    print("Historical cases:", len(historical))
    print("External selected:", len(external))
    print(
        "Historical normalized duplicates:",
        historical_duplicate_count,
    )
    print(
        "External normalized duplicates:",
        external_duplicate_count,
    )
    print(
        "Exact normalized overlap:",
        overlap_count,
    )

    print()

    if overlap.empty:
        print(
            "PASS: No exact normalized overlap "
            "between the 80 external cases and "
            "the 59 historical cases."
        )
    else:
        print(
            "REVIEW REQUIRED: Overlapping cases found."
        )
        print()
        print(
            overlap[
                [
                    "external_case_id",
                    "historical_partition",
                    "external_text",
                ]
            ].to_string(index=False)
        )

    print()
    print(f"Audit CSV: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")

    print()
    print("IMPORTANT:")
    print(
        "This audit checks exact normalized text overlap."
    )
    print(
        "It does not claim semantic or near-duplicate "
        "independence."
    )
    print(
        "Claim Atomizer v0.4 has not been used."
    )


if __name__ == "__main__":
    main()