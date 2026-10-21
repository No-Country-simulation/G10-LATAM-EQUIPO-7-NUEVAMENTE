"""Genera paquete Markdown para revisar claims low-priority.

Este script NO modifica producción ni las etiquetas humanas.

Objetivo:
- leer content_support_claim_ground_truth_v1.csv;
- seleccionar claims con annotation_priority == low;
- recuperar chunks_used del caso original;
- generar un documento Markdown con:
    - calibration_id
    - claim_id
    - claim_text
    - ratios legacy/normalized
    - decisiones actuales de routing
    - chunks_used
    - espacio para anotación humana

La anotación debe usar exclusivamente chunks_used como evidencia factual.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

CASES_DIR = Path(
    "data/evaluation/calibration_v1/cases"
)

INPUT_GT = (
    RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)

OUTPUT_MD = (
    RESULTS_DIR
    / "content_support_low_review_packet_v1.md"
)


def load_case(
    calibration_id: str,
) -> dict:
    path = (
        CASES_DIR
        / f"{calibration_id}.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el caso: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main() -> None:
    with INPUT_GT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    low_rows = [
        row
        for row in rows
        if (
            row[
                "annotation_priority"
            ]
            .strip()
            .lower()
            == "low"
        )
    ]

    low_rows.sort(
        key=lambda row: (
            row["calibration_id"],
            row["claim_id"],
        )
    )

    lines: list[str] = []

    lines.append(
        "# Content Support — Low Priority Review Packet v1"
    )
    lines.append("")

    lines.append(
        "## Regla de anotación"
    )
    lines.append("")

    lines.append(
        "`chunks_used` es la única evidencia factual válida."
    )
    lines.append("")

    lines.append(
        "Etiquetas permitidas:"
    )
    lines.append("")

    lines.append(
        "- `supported`: el claim está respaldado explícitamente "
        "o mediante equivalencia semántica clara."
    )

    lines.append(
        "- `unsupported`: introduce información nueva, "
        "contradictoria o una extrapolación no demostrada."
    )

    lines.append(
        "- `uncertain`: la evidencia no permite decidir "
        "con suficiente confianza."
    )

    lines.append("")
    lines.append("---")
    lines.append("")

    current_case = None
    case_data = None

    for index, row in enumerate(
        low_rows,
        start=1,
    ):
        calibration_id = row[
            "calibration_id"
        ]

        if calibration_id != current_case:
            current_case = (
                calibration_id
            )

            case_data = load_case(
                calibration_id
            )

        chunks_used = (
            case_data[
                "evaluation_request"
            ][
                "chunks_used"
            ]
        )

        lines.append(
            f"## {index}. "
            f"{calibration_id} — "
            f"`{row['claim_id']}`"
        )
        lines.append("")

        lines.append(
            f"**Formato:** `{row['format']}`"
        )
        lines.append("")

        lines.append(
            f"**Legacy ratio:** "
            f"`{row['legacy_ratio']}`"
        )

        lines.append(
            f"**Legacy needs review:** "
            f"`{row['legacy_needs_review']}`"
        )

        lines.append(
            f"**Normalized ratio:** "
            f"`{row['normalized_ratio']}`"
        )

        lines.append(
            f"**Normalized needs review:** "
            f"`{row['normalized_needs_review']}`"
        )

        lines.append("")

        lines.append(
            "### Claim"
        )
        lines.append("")

        lines.append(
            row["claim_text"]
        )
        lines.append("")

        lines.append(
            "### Chunks usados como evidencia"
        )
        lines.append("")

        for chunk in chunks_used:
            chunk_id = (
                chunk.get(
                    "chunk_id",
                    "unknown",
                )
            )

            chunk_text = (
                chunk.get(
                    "text",
                    ""
                )
            )

            lines.append(
                f"#### `{chunk_id}`"
            )
            lines.append("")

            lines.append(
                "```text"
            )

            lines.append(
                chunk_text
            )

            lines.append(
                "```"
            )

            lines.append("")

        lines.append(
            "### Anotación humana"
        )
        lines.append("")

        lines.append(
            "**human_support_label:** "
            "`PENDING`"
        )

        lines.append("")

        lines.append(
            "**human_notes:** "
            "PENDING"
        )

        lines.append("")
        lines.append("---")
        lines.append("")

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    unique_cases = {
        row["calibration_id"]
        for row in low_rows
    }

    print("=" * 70)
    print(
        "CONTENT SUPPORT LOW REVIEW PACKET V1"
    )
    print("=" * 70)

    print(
        "Low claims:",
        len(low_rows),
    )

    print(
        "Cases represented:",
        len(unique_cases),
    )

    print()

    print(
        "Output:",
        OUTPUT_MD,
    )

    print()

    print(
        "No ground-truth labels were modified."
    )


if __name__ == "__main__":
    main()