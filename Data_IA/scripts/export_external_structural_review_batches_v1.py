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
    / "external_claim_structural_review_v1.csv"
)

BATCH_DIR = (
    BASE_DIR
    / "review_batches"
)

MANIFEST_PATH = (
    BASE_DIR
    / "manifest"
    / "external_claim_structural_review_batches_manifest_v1.json"
)

BATCH_SIZE = 20
EXPECTED_ROWS = 120


def main() -> None:
    df = pd.read_csv(
        INPUT_PATH,
        keep_default_na=False,
    )

    if len(df) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS} rows; found {len(df)}."
        )

    if df["external_review_id"].duplicated().any():
        raise ValueError(
            "Duplicate external_review_id values found."
        )

    BATCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    batch_files = []

    for start in range(0, len(df), BATCH_SIZE):
        batch_number = (start // BATCH_SIZE) + 1
        end = min(start + BATCH_SIZE, len(df))

        batch = df.iloc[start:end].copy()

        output_path = (
            BATCH_DIR
            / f"external_structural_review_batch_{batch_number:02d}_v1.csv"
        )

        batch.to_csv(
            output_path,
            index=False,
            encoding="utf-8-sig",
        )

        batch_files.append(
            {
                "batch": batch_number,
                "start_id": batch.iloc[0]["external_review_id"],
                "end_id": batch.iloc[-1]["external_review_id"],
                "rows": int(len(batch)),
                "path": str(output_path),
            }
        )

    manifest = {
        "artifact": (
            "external_claim_structural_review_batches_v1"
        ),
        "status": "human_review_batches_created",
        "input_path": str(INPUT_PATH),
        "batch_size": BATCH_SIZE,
        "batch_count": len(batch_files),
        "total_claims": len(df),
        "batches": batch_files,
        "model_used": False,
        "llm_used": False,
        "claim_atomizer_v0_4_used": False,
        "predictions_available_to_reviewer": False,
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

    print("External Structural Review Batches v1")
    print("=====================================")
    print(f"Claims: {len(df)}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Batches: {len(batch_files)}")

    print()

    for item in batch_files:
        print(
            f"Batch {item['batch']:02d}: "
            f"{item['start_id']} -> "
            f"{item['end_id']} "
            f"({item['rows']} rows)"
        )

    print()
    print(f"Batch directory: {BATCH_DIR}")
    print(f"Manifest: {MANIFEST_PATH}")
    print()
    print(
        "IMPORTANT: Review batches contain no "
        "Claim Atomizer predictions."
    )


if __name__ == "__main__":
    main()