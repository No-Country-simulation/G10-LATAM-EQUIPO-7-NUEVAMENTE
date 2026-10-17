"""Construye el manifest de revisión semántica por claim.

Este script NO modifica producción.

Objetivo:
- leer el ground truth humano a nivel de claim;
- seleccionar únicamente claims con:
    legacy_needs_review = True
- conservar la etiqueta humana para benchmark;
- preparar columnas vacías para completar con evaluación semántica;
- generar un manifest reproducible para el runner Gemini experimental.

Este manifest se usará para responder:

¿Puede la revisión semántica resolver los falsos positivos
del router léxico sin dejar escapar claims realmente unsupported?

NO:
- llama a Gemini;
- modifica quality_evaluator.py;
- modifica /evaluate/v2;
- calcula verdict de producción.
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
    / "content_support_semantic_review_manifest_v1.csv"
)


ALLOWED_HUMAN_LABELS = {
    "supported",
    "unsupported",
}


def parse_bool(
    value: str,
) -> bool:
    """Convierte valores de CSV a bool."""

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

    selected_rows = []

    for row in rows:
        human_label = (
            row[
                "human_support_label"
            ]
            .strip()
            .lower()
        )

        if (
            human_label
            not in ALLOWED_HUMAN_LABELS
        ):
            continue

        legacy_needs_review = (
            parse_bool(
                row[
                    "legacy_needs_review"
                ]
            )
        )

        if not legacy_needs_review:
            continue

        selected_rows.append(
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

    selected_rows.sort(
        key=lambda row: (
            row[
                "calibration_id"
            ],
            row[
                "claim_id"
            ],
        )
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
            selected_rows
        )

    supported = sum(
        row[
            "human_support_label"
        ] == "supported"
        for row in selected_rows
    )

    unsupported = sum(
        row[
            "human_support_label"
        ] == "unsupported"
        for row in selected_rows
    )

    print("=" * 70)
    print(
        "CONTENT SUPPORT SEMANTIC REVIEW MANIFEST V1"
    )
    print("=" * 70)

    print(
        "Selected claims:",
        len(selected_rows),
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
        "Expected benchmark composition:"
    )

    print(
        f"- false positives to resolve: "
        f"{supported}"
    )

    print(
        f"- true positives to preserve: "
        f"{unsupported}"
    )

    print()
    print(
        "Output:",
        OUTPUT_MANIFEST,
    )

    print()
    print(
        "Semantic fields remain empty."
    )

    print(
        "Next step: run experimental "
        "claim-level semantic review."
    )


if __name__ == "__main__":
    main()