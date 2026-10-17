"""Construye benchmark semántico para claims autoaceptados por legacy.

Selecciona claims con:
- human_support_label supported/unsupported
- legacy_needs_review == False

Objetivo:
evaluar si el gate léxico deja escapar unsupported claims y comprobar
cómo se comporta Gemini sobre el conjunto que legacy habría autoaceptado.

NO llama a Gemini.
NO modifica producción.
"""

from __future__ import annotations

import csv
from pathlib import Path


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

INPUT_GT = (
    RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)

OUTPUT_MANIFEST = (
    RESULTS_DIR
    / "content_support_semantic_autoaccepted_manifest_v1.csv"
)


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {
        "true",
        "1",
        "yes",
    }


def main() -> None:
    with INPUT_GT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    selected = []

    for row in rows:
        human_label = (
            row[
                "human_support_label"
            ]
            .strip()
            .lower()
        )

        if human_label not in {
            "supported",
            "unsupported",
        }:
            continue

        legacy_needs_review = parse_bool(
            row[
                "legacy_needs_review"
            ]
        )

        if legacy_needs_review:
            continue

        selected.append(
            {
                "calibration_id": (
                    row[
                        "calibration_id"
                    ]
                ),
                "format": (
                    row[
                        "format"
                    ]
                ),
                "claim_id": (
                    row[
                        "claim_id"
                    ]
                ),
                "claim_text": (
                    row[
                        "claim_text"
                    ]
                ),
                "legacy_ratio": (
                    row[
                        "legacy_ratio"
                    ]
                ),
                "legacy_needs_review": (
                    row[
                        "legacy_needs_review"
                    ]
                ),
                "human_support_label": (
                    human_label
                ),
                "human_notes": (
                    row[
                        "human_notes"
                    ]
                ),
                "semantic_status": "",
                "semantic_supported": "",
                "semantic_reason": "",
                "semantic_model": "",
                "semantic_prompt_version": "",
                "semantic_latency_ms": "",
                "semantic_error_code": "",
                "semantic_error_message": "",
            }
        )

    selected.sort(
        key=lambda row: (
            row["calibration_id"],
            row["claim_id"],
        )
    )

    supported = sum(
        row["human_support_label"]
        == "supported"
        for row in selected
    )

    unsupported = sum(
        row["human_support_label"]
        == "unsupported"
        for row in selected
    )

    fieldnames = [
        "calibration_id",
        "format",
        "claim_id",
        "claim_text",
        "legacy_ratio",
        "legacy_needs_review",
        "human_support_label",
        "human_notes",
        "semantic_status",
        "semantic_supported",
        "semantic_reason",
        "semantic_model",
        "semantic_prompt_version",
        "semantic_latency_ms",
        "semantic_error_code",
        "semantic_error_message",
    ]

    with OUTPUT_MANIFEST.open(
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
            selected
        )

    print("=" * 72)
    print(
        "CONTENT SUPPORT SEMANTIC AUTOACCEPTED MANIFEST V1"
    )
    print("=" * 72)

    print(
        "Selected claims:",
        len(selected),
    )

    print(
        "Human supported:",
        supported,
    )

    print(
        "Human unsupported:",
        unsupported,
    )

    print()
    print(
        "Output:",
        OUTPUT_MANIFEST,
    )

    print()
    print(
        "These are claims legacy would NOT "
        "send to semantic review."
    )


if __name__ == "__main__":
    main()