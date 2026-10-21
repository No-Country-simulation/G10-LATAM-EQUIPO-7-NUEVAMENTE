"""Builds the source-claim dataset for Claim Atomization v1.

This script only selects source claims.

It does NOT:
- atomize claims;
- call Gemini;
- modify production;
- change existing human support labels.

The expected atomization will be created manually in a separate GT file.
"""

from __future__ import annotations

import csv
from pathlib import Path


CALIBRATION_RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

ATOMIZATION_DIR = Path(
    "data/evaluation/atomization_v1"
)

INPUT_GT = (
    CALIBRATION_RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)

OUTPUT_DATASET = (
    ATOMIZATION_DIR
    / "atomization_dataset_v1.csv"
)


# All 8 known unsupported claims are intentionally included.
UNSUPPORTED_SELECTION = [
    ("CAL-V1-004", "scene_1_narration_claim_2"),
    ("CAL-V1-006", "key_point_3_claim_1"),
    ("CAL-V1-014", "question_1_explanation_claim_2"),
    ("CAL-V1-015", "card_2_back_claim_2"),
    ("CAL-V1-016", "conclusion_claim_1"),
    ("CAL-V1-018", "card_1_back_claim_2"),
    ("CAL-V1-020", "scene_2_narration_claim_1"),
    ("CAL-V1-020", "scene_2_narration_claim_2"),
]


# Supported controls covering different formats and structures.
SUPPORTED_SELECTION = [
    ("CAL-V1-001", "question_1_explanation_claim_1"),
    ("CAL-V1-003", "key_point_1_claim_1"),
    ("CAL-V1-005", "card_1_back_claim_1"),
    ("CAL-V1-009", "summary_claim_1"),
    ("CAL-V1-013", "scene_1_narration_claim_1"),
    ("CAL-V1-015", "card_1_back_claim_1"),
    ("CAL-V1-017", "question_1_explanation_claim_1"),
    ("CAL-V1-019", "key_point_2_claim_1"),
]


def load_rows() -> list[dict[str, str]]:
    with INPUT_GT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def make_key(
    calibration_id: str,
    claim_id: str,
) -> tuple[str, str]:
    return (
        calibration_id,
        claim_id,
    )


def main() -> None:
    ATOMIZATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = load_rows()

    by_key = {
        make_key(
            row["calibration_id"],
            row["claim_id"],
        ): row
        for row in rows
    }

    selections = []

    for calibration_id, claim_id in UNSUPPORTED_SELECTION:
        selections.append(
            (
                calibration_id,
                claim_id,
                "unsupported_case",
            )
        )

    for calibration_id, claim_id in SUPPORTED_SELECTION:
        selections.append(
            (
                calibration_id,
                claim_id,
                "supported_control",
            )
        )

    output_rows = []

    missing = []

    for index, (
        calibration_id,
        claim_id,
        selection_reason,
    ) in enumerate(
        selections,
        start=1,
    ):
        key = make_key(
            calibration_id,
            claim_id,
        )

        source = by_key.get(key)

        if source is None:
            missing.append(key)
            continue

        output_rows.append(
            {
                "dataset_id": (
                    f"ATOM-V1-{index:03d}"
                ),
                "calibration_id": calibration_id,
                "source_claim_id": claim_id,
                "format": source["format"],
                "source_claim_text": (
                    source["claim_text"]
                ),
                "human_support_label": (
                    source[
                        "human_support_label"
                    ]
                ),
                "selection_reason": (
                    selection_reason
                ),
            }
        )

    if missing:
        print(
            "ERROR: source claims not found:"
        )

        for item in missing:
            print(
                "-",
                item[0],
                item[1],
            )

        raise SystemExit(1)

    fieldnames = [
        "dataset_id",
        "calibration_id",
        "source_claim_id",
        "format",
        "source_claim_text",
        "human_support_label",
        "selection_reason",
    ]

    with OUTPUT_DATASET.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            output_rows
        )

    supported = sum(
        row["human_support_label"]
        == "supported"
        for row in output_rows
    )

    unsupported = sum(
        row["human_support_label"]
        == "unsupported"
        for row in output_rows
    )

    print("=" * 72)
    print(
        "CLAIM ATOMIZATION DATASET V1"
    )
    print("=" * 72)

    print(
        "Source claims:",
        len(output_rows),
    )

    print(
        "Supported:",
        supported,
    )

    print(
        "Unsupported:",
        unsupported,
    )

    print()

    print(
        "Output:",
        OUTPUT_DATASET,
    )

    print()

    print(
        "No atomization ground truth "
        "was generated automatically."
    )


if __name__ == "__main__":
    main()