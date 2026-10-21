"""Build manual review packet for Claim Atomization holdout v1.

The packet is used to define atomization ground truth BEFORE
running any automatic atomizer on the holdout.

Important:
- no Gemini calls;
- no model predictions;
- no factual-support evaluation;
- no production changes.
"""

from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1/holdout_v1"
)

DATASET_FILE = (
    BASE_DIR
    / "atomization_holdout_dataset_v1.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "atomization_holdout_review_packet_v1.md"
)


def load_csv(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def main() -> None:
    rows = load_csv(
        DATASET_FILE
    )

    lines: list[str] = [
        "# Claim Atomization Holdout v1 — Manual Review Packet",
        "",
        "## Objetivo",
        "",
        (
            "Definir manualmente el ground truth de atomización "
            "del holdout antes de ejecutar cualquier atomizador automático."
        ),
        "",
        (
            "Este holdout no debe usarse para modificar prompts, "
            "reglas o modelos antes de su evaluación final."
        ),
        "",
        "## Reglas",
        "",
        "- No usar outputs de Gemini.",
        "- No usar resultados de v0.1, v0.2 o v0.3.",
        "- No inventar información que no esté en el source claim.",
        "- Preservar todos los calificadores factuales relevantes.",
        "- No dividir por longitud ni puntuación solamente.",
        "- Dividir únicamente proposiciones o relaciones evaluables por separado.",
        "- Mantener listas simples con predicado compartido cuando corresponda.",
        "- Cada átomo debe ser comprensible y evaluable de forma independiente.",
        "",
        "## Clases permitidas",
        "",
        "- `atomic`",
        "- `compound`",
        "- `relational`",
        "",
        "## Tipos de átomo permitidos",
        "",
        "- `factual_proposition`",
        "- `temporal_relation`",
        "- `causal_relation`",
        "- `conditional_relation`",
        "- `comparative_relation`",
        "- `negation_or_absence`",
        "- `scope_or_quantifier`",
        "",
        "## Nota metodológica",
        "",
        (
            "`human_support_label` se conserva únicamente como metadata "
            "del claim original. No debe utilizarse para decidir cómo "
            "atomizar el texto."
        ),
        "",
        "---",
        "",
    ]

    for index, row in enumerate(
        rows,
        start=1,
    ):
        lines.extend(
            [
                (
                    f"## {index}. "
                    f"{row['holdout_id']} — "
                    f"{row['calibration_id']}"
                ),
                "",
                (
                    f"**source_claim_id:** "
                    f"`{row['source_claim_id']}`"
                ),
                "",
                (
                    f"**format:** "
                    f"`{row['format']}`"
                ),
                "",
                (
                    f"**human_support_label:** "
                    f"`{row['human_support_label']}`"
                ),
                "",
                (
                    f"**annotation_priority:** "
                    f"`{row['annotation_priority']}`"
                ),
                "",
                "### Source claim",
                "",
                row[
                    "source_claim_text"
                ],
                "",
                "### Ground truth de atomización",
                "",
                "**atomization_class:** `PENDING`",
                "",
                "**atom_count:** `PENDING`",
                "",
            ]
        )

        for atom_number in range(
            1,
            7,
        ):
            lines.extend(
                [
                    (
                        f"#### Atom "
                        f"{atom_number}"
                    ),
                    "",
                    (
                        "**atom_text:** "
                        "PENDING"
                    ),
                    "",
                    (
                        "**atom_type:** "
                        "`PENDING`"
                    ),
                    "",
                ]
            )

        lines.extend(
            [
                (
                    "**review_notes:** "
                    "PENDING"
                ),
                "",
                "---",
                "",
            ]
        )

    OUTPUT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=" * 80)
    print(
        "CLAIM ATOMIZATION HOLDOUT V1 — "
        "MANUAL REVIEW PACKET"
    )
    print("=" * 80)

    print(
        "Source claims:",
        len(rows),
    )

    print()

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    print(
        "No model outputs were used."
    )


if __name__ == "__main__":
    main()