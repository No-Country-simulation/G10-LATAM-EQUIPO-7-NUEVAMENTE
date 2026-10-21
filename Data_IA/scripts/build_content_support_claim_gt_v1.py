"""Construye manifest para ground truth humano a nivel de claim.

Este script NO modifica producción.

Toma los claims producidos por:
content_support_router_full_v1_claims.csv

y genera un archivo preparado para anotación humana.

Las etiquetas humanas deben completarse posteriormente como:

- supported
- unsupported
- uncertain

Objetivo:
medir precision/recall del router a nivel de claim antes de
integrar cualquier routing léxico o semántico en producción.
"""

from __future__ import annotations

import csv
from pathlib import Path


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

INPUT_CSV = (
    RESULTS_DIR
    / "content_support_router_full_v1_claims.csv"
)

OUTPUT_CSV = (
    RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)


PRIORITY_CASES = {
    "CAL-V1-004",
    "CAL-V1-006",
    "CAL-V1-014",
    "CAL-V1-016",
    "CAL-V1-018",
}


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {
        "true",
        "1",
        "yes",
    }


def main() -> None:
    with INPUT_CSV.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    factual_rows = [
        row
        for row in rows
        if row["factual_role"]
        == "factual_content"
    ]

    output_rows = []

    for row in factual_rows:
        calibration_id = row[
            "calibration_id"
        ]

        legacy_review = parse_bool(
            row["legacy_needs_review"]
        )

        normalized_review = parse_bool(
            row["normalized_needs_review"]
        )

        priority = (
            "high"
            if calibration_id
            in PRIORITY_CASES
            else (
                "medium"
                if legacy_review
                or normalized_review
                else "low"
            )
        )

        output_rows.append(
            {
                "calibration_id": (
                    calibration_id
                ),
                "format": (
                    row["format"]
                ),
                "claim_id": (
                    row["claim_id"]
                ),
                "claim_text": (
                    row["claim_text"]
                ),
                "legacy_ratio": (
                    row["legacy_ratio"]
                ),
                "legacy_needs_review": (
                    row[
                        "legacy_needs_review"
                    ]
                ),
                "normalized_ratio": (
                    row["normalized_ratio"]
                ),
                "normalized_needs_review": (
                    row[
                        "normalized_needs_review"
                    ]
                ),
                "annotation_priority": (
                    priority
                ),
                "human_support_label": "",
                "human_notes": "",
            }
        )

    priority_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    output_rows.sort(
        key=lambda row: (
            priority_order[
                row[
                    "annotation_priority"
                ]
            ],
            row["calibration_id"],
            row["claim_id"],
        )
    )

    fieldnames = [
        "calibration_id",
        "format",
        "claim_id",
        "claim_text",
        "legacy_ratio",
        "legacy_needs_review",
        "normalized_ratio",
        "normalized_needs_review",
        "annotation_priority",
        "human_support_label",
        "human_notes",
    ]

    with OUTPUT_CSV.open(
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

    high = sum(
        row["annotation_priority"]
        == "high"
        for row in output_rows
    )

    medium = sum(
        row["annotation_priority"]
        == "medium"
        for row in output_rows
    )

    low = sum(
        row["annotation_priority"]
        == "low"
        for row in output_rows
    )

    print("=" * 70)
    print(
        "CONTENT SUPPORT CLAIM GT MANIFEST"
    )
    print("=" * 70)

    print(
        "Factual claims:",
        len(output_rows),
    )

    print(
        "High priority:",
        high,
    )

    print(
        "Medium priority:",
        medium,
    )

    print(
        "Low priority:",
        low,
    )

    print()
    print(
        "Output:",
        OUTPUT_CSV,
    )

    print()
    print(
        "Allowed human labels:"
    )

    print(
        "- supported"
    )

    print(
        "- unsupported"
    )

    print(
        "- uncertain"
    )


if __name__ == "__main__":
    main()