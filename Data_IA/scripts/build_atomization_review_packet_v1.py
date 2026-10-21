"""Builds the manual review packet for Claim Atomization v1.

The packet contains:
- source claim metadata;
- existing human support label;
- chunks_used from the original calibration case;
- empty fields for manual atomization ground truth.

This script does NOT:
- atomize claims automatically;
- call Gemini;
- modify existing calibration ground truth;
- modify production code.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ATOMIZATION_DIR = Path(
    "data/evaluation/atomization_v1"
)

CALIBRATION_CASES_DIR = Path(
    "data/evaluation/calibration_v1/cases"
)

INPUT_DATASET = (
    ATOMIZATION_DIR
    / "atomization_dataset_v1.csv"
)

OUTPUT_PACKET = (
    ATOMIZATION_DIR
    / "atomization_review_packet_v1.md"
)


ATOM_TYPES = [
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
]


def load_dataset() -> list[dict[str, str]]:
    with INPUT_DATASET.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def load_case(
    calibration_id: str,
) -> dict:
    path = (
        CALIBRATION_CASES_DIR
        / f"{calibration_id}.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Calibration case not found: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def extract_chunks(
    case_data: dict,
) -> list[dict]:
    return (
        case_data[
            "evaluation_request"
        ][
            "chunks_used"
        ]
    )


def main() -> None:
    rows = load_dataset()

    lines: list[str] = []

    lines.append(
        "# Claim Atomization v1 — Manual Review Packet"
    )
    lines.append("")

    lines.append("## Objetivo")
    lines.append("")

    lines.append(
        "Definir manualmente el ground truth de atomización "
        "antes de probar cualquier atomizador automático."
    )
    lines.append("")

    lines.append(
        "`chunks_used` es la única evidencia válida para "
        "asignar `expected_support` a cada átomo."
    )
    lines.append("")

    lines.append(
        "La atomización debe preservar todo el significado "
        "factual del claim original."
    )
    lines.append("")

    lines.append("## Reglas")
    lines.append("")

    lines.append(
        "- No inventar información que no exista en el source claim."
    )

    lines.append(
        "- No eliminar calificadores relevantes como "
        "`automáticamente`, `todos`, `antes`, `después`, "
        "`sin`, `por defecto`, etc."
    )

    lines.append(
        "- No dividir por longitud; dividir por proposiciones "
        "o relaciones factuales independientes."
    )

    lines.append(
        "- Un claim ya atómico debe conservarse como un solo átomo."
    )

    lines.append(
        "- Cada átomo debe poder evaluarse de forma independiente."
    )

    lines.append(
        "- `expected_support` puede ser "
        "`supported`, `unsupported` o `uncertain`."
    )

    lines.append("")

    lines.append(
        "Tipos permitidos:"
    )
    lines.append("")

    for atom_type in ATOM_TYPES:
        lines.append(
            f"- `{atom_type}`"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    for index, row in enumerate(
        rows,
        start=1,
    ):
        calibration_id = (
            row["calibration_id"]
        )

        case_data = load_case(
            calibration_id
        )

        chunks = extract_chunks(
            case_data
        )

        lines.append(
            f"## {index}. "
            f"{row['dataset_id']} — "
            f"{calibration_id}"
        )
        lines.append("")

        lines.append(
            f"**source_claim_id:** "
            f"`{row['source_claim_id']}`"
        )
        lines.append("")

        lines.append(
            f"**format:** "
            f"`{row['format']}`"
        )
        lines.append("")

        lines.append(
            f"**human_support_label:** "
            f"`{row['human_support_label']}`"
        )
        lines.append("")

        lines.append(
            f"**selection_reason:** "
            f"`{row['selection_reason']}`"
        )
        lines.append("")

        lines.append(
            "### Source claim"
        )
        lines.append("")

        lines.append(
            row["source_claim_text"]
        )
        lines.append("")

        lines.append(
            "### Evidencia — chunks_used"
        )
        lines.append("")

        for chunk in chunks:
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

            lines.append("```text")
            lines.append(chunk_text)
            lines.append("```")
            lines.append("")

        lines.append(
            "### Ground truth de atomización"
        )
        lines.append("")

        lines.append(
            "**atomization_class:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**atom_count:** `PENDING`"
        )
        lines.append("")

        for atom_number in range(
            1,
            5,
        ):
            lines.append(
                f"#### Atom {atom_number}"
            )
            lines.append("")

            lines.append(
                f"**atom_text:** PENDING"
            )
            lines.append("")

            lines.append(
                f"**atom_type:** `PENDING`"
            )
            lines.append("")

            lines.append(
                f"**expected_support:** `PENDING`"
            )
            lines.append("")

        lines.append(
            "**review_notes:** PENDING"
        )
        lines.append("")

        lines.append("---")
        lines.append("")

    OUTPUT_PACKET.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    supported = sum(
        row["human_support_label"]
        == "supported"
        for row in rows
    )

    unsupported = sum(
        row["human_support_label"]
        == "unsupported"
        for row in rows
    )

    formats = sorted(
        {
            row["format"]
            for row in rows
        }
    )

    print("=" * 72)
    print(
        "CLAIM ATOMIZATION REVIEW PACKET V1"
    )
    print("=" * 72)

    print(
        "Source claims:",
        len(rows),
    )

    print(
        "Supported:",
        supported,
    )

    print(
        "Unsupported:",
        unsupported,
    )

    print(
        "Formats:",
        ", ".join(formats),
    )

    print()

    print(
        "Output:",
        OUTPUT_PACKET,
    )

    print()

    print(
        "No atomization labels were generated automatically."
    )


if __name__ == "__main__":
    main()