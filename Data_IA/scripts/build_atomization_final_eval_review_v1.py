"""Build blind human review packet for atomization final_eval_v1.

Important:
- reads ONLY the frozen final-eval dataset;
- does NOT read v0.4 predictions;
- does NOT expose model outputs;
- intended for human annotation after predictions were frozen.
"""

from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1/final_eval_v1"
)

DATASET_FILE = (
    BASE_DIR
    / "atomization_final_eval_dataset_v1.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "atomization_final_eval_review_packet_v1.md"
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

    if len(rows) != 23:
        raise RuntimeError(
            "Expected 23 final-eval items, "
            f"found {len(rows)}."
        )

    lines: list[str] = [
        "# Claim Atomization Final Eval v1 — Blind Human Review",
        "",
        "## Objetivo",
        "",
        (
            "Crear el ground truth humano del conjunto final de "
            "evaluación después de congelar las predicciones de v0.4."
        ),
        "",
        (
            "Este paquete fue generado únicamente desde el dataset "
            "fuente. No contiene predicciones del atomizador."
        ),
        "",
        "## Reglas de anotación",
        "",
        "- No consultar las predicciones de v0.4.",
        "- No consultar resultados de v0.1, v0.2 o v0.3.",
        "- No inventar sujeto, predicado, objeto ni contexto ausente.",
        "- Preservar calificadores factuales relevantes.",
        "- No dividir por longitud o puntuación solamente.",
        "- Separar solo hechos o relaciones evaluables por separado.",
        "- Mantener listas simples con predicado compartido cuando corresponda.",
        "- Cada átomo debe ser comprensible y evaluable de forma independiente.",
        "- Si el texto no expresa una proposición factual suficiente, usar `non_propositional`.",
        "",
        "## review_status permitido",
        "",
        "- `valid_claim`",
        "- `non_propositional`",
        "",
        "## atomization_class permitido",
        "",
        "- `atomic`",
        "- `compound`",
        "- `relational`",
        "",
        "## atom_type permitido",
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
            "`human_support_label` se muestra únicamente como metadata "
            "del dataset original. No debe utilizarse para decidir la "
            "estructura de atomización."
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
                    f"{row['final_eval_id']} — "
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
                "### Human annotation",
                "",
                "**review_status:** `PENDING`",
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

    print("=" * 84)
    print(
        "CLAIM ATOMIZATION FINAL EVAL V1 "
        "— BLIND HUMAN REVIEW PACKET"
    )
    print("=" * 84)

    print(
        "Source items:",
        len(rows),
    )

    print()

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    print(
        "Model predictions used: False"
    )


if __name__ == "__main__":
    main()