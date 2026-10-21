"""Genera paquete de adjudicación para desacuerdos humano vs Gemini.

NO modifica etiquetas ni código productivo.

Selecciona exclusivamente casos donde:
- semantic_status == success
- human_support_label es supported/unsupported
- semantic_supported != human_support_label

Incluye chunks_used para revisión manual.
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

INPUT_RESULTS = (
    RESULTS_DIR
    / "content_support_semantic_review_results_v1.csv"
)

OUTPUT_MD = (
    RESULTS_DIR
    / "content_support_semantic_disagreement_review_v1.md"
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
            f"Case not found: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main() -> None:
    with INPUT_RESULTS.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    disagreements = [
        row
        for row in rows
        if (
            row[
                "semantic_status"
            ].strip()
            == "success"
            and row[
                "human_support_label"
            ].strip()
            in {
                "supported",
                "unsupported",
            }
            and row[
                "semantic_supported"
            ].strip()
            != row[
                "human_support_label"
            ].strip()
        )
    ]

    lines: list[str] = []

    lines.append(
        "# Content Support — Semantic Disagreement Review v1"
    )
    lines.append("")

    lines.append(
        "## Regla de adjudicación"
    )
    lines.append("")

    lines.append(
        "`chunks_used` es la única evidencia factual válida."
    )
    lines.append("")

    lines.append(
        "No modificar la etiqueta para hacerla coincidir "
        "automáticamente con Gemini."
    )
    lines.append("")

    lines.append(
        "Opciones finales:"
    )
    lines.append("")
    lines.append("- `supported`")
    lines.append("- `unsupported`")
    lines.append("- `uncertain`")
    lines.append("")

    lines.append("---")
    lines.append("")

    for index, row in enumerate(
        disagreements,
        start=1,
    ):
        calibration_id = (
            row[
                "calibration_id"
            ]
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
            "### Claim"
        )
        lines.append("")
        lines.append(
            row[
                "claim_text"
            ]
        )
        lines.append("")

        lines.append(
            "### Ground truth actual"
        )
        lines.append("")
        lines.append(
            f"`{row['human_support_label']}`"
        )
        lines.append("")

        lines.append(
            "### Gemini"
        )
        lines.append("")
        lines.append(
            f"`{row['semantic_supported']}`"
        )
        lines.append("")

        lines.append(
            "### Razón de Gemini"
        )
        lines.append("")
        lines.append(
            row[
                "semantic_reason"
            ]
        )
        lines.append("")

        lines.append(
            "### Evidencia — chunks_used"
        )
        lines.append("")

        for chunk in chunks_used:
            lines.append(
                f"#### `{chunk.get('chunk_id', 'unknown')}`"
            )
            lines.append("")
            lines.append("```text")
            lines.append(
                chunk.get(
                    "text",
                    ""
                )
            )
            lines.append("```")
            lines.append("")

        lines.append(
            "### Adjudicación"
        )
        lines.append("")
        lines.append(
            "**final_label:** `PENDING`"
        )
        lines.append("")
        lines.append(
            "**reason:** PENDING"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=" * 70)
    print(
        "CONTENT SUPPORT SEMANTIC "
        "DISAGREEMENT REVIEW V1"
    )
    print("=" * 70)

    print(
        "Disagreements:",
        len(disagreements),
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