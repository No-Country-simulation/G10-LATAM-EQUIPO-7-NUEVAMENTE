"""Builds manual semantic-preservation review for Claim Atomization v1.

Compares:
- original source claim;
- frozen ground-truth atoms;
- Gemini v0.1 predicted atoms;
- structural evaluation.

This script does NOT:
- call Gemini;
- change the frozen ground truth;
- modify production;
- automatically judge semantic quality.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ATOMIZATION_DIR = Path(
    "data/evaluation/atomization_v1"
)

RESULTS_DIR = (
    ATOMIZATION_DIR
    / "results"
)

DATASET_FILE = (
    ATOMIZATION_DIR
    / "atomization_dataset_v1.csv"
)

GT_FILE = (
    ATOMIZATION_DIR
    / "atomization_ground_truth_v1.csv"
)

PREDICTIONS_FILE = (
    RESULTS_DIR
    / "atomization_predictions_v1.csv"
)

STRUCTURE_FILE = (
    RESULTS_DIR
    / "atomization_structure_cases_v1.csv"
)

OUTPUT_MD = (
    RESULTS_DIR
    / "atomization_semantic_review_v1.md"
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


def group_rows(
    rows: list[dict[str, str]],
    key: str,
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in rows:
        grouped[
            row[key]
        ].append(row)

    return grouped


def main() -> None:
    dataset_rows = load_csv(
        DATASET_FILE
    )

    gt_rows = load_csv(
        GT_FILE
    )

    prediction_rows = load_csv(
        PREDICTIONS_FILE
    )

    structure_rows = load_csv(
        STRUCTURE_FILE
    )

    dataset_by_id = {
        row["dataset_id"]: row
        for row in dataset_rows
    }

    gt_by_id = group_rows(
        gt_rows,
        "dataset_id",
    )

    pred_by_id = group_rows(
        [
            row
            for row in prediction_rows
            if row["status"]
            == "success"
        ],
        "dataset_id",
    )

    structure_by_id = {
        row["dataset_id"]: row
        for row in structure_rows
    }

    lines: list[str] = []

    lines.append(
        "# Claim Atomization v1 — Semantic Preservation Review"
    )
    lines.append("")

    lines.append("## Objetivo")
    lines.append("")

    lines.append(
        "Evaluar manualmente si las predicciones de ClaimAtomizer v0.1 "
        "preservan el significado factual completo del source claim."
    )
    lines.append("")

    lines.append(
        "Esta revisión es independiente de la evaluación de factual support."
    )
    lines.append("")

    lines.append("## Criterios")
    lines.append("")

    lines.append(
        "- `meaning_preserved`: la suma de los átomos conserva todo "
        "el significado factual del claim."
    )

    lines.append(
        "- `qualifiers_preserved`: no se pierden ni debilitan "
        "calificadores como automáticamente, todos, antes, después, "
        "sin, por defecto, etc."
    )

    lines.append(
        "- `no_invented_information`: ningún átomo introduce "
        "información que no estaba en el source claim."
    )

    lines.append(
        "- `relations_isolated`: las relaciones factuales relevantes "
        "quedan separadas cuando deben evaluarse independientemente."
    )

    lines.append(
        "- `atoms_independently_evaluable`: cada átomo puede evaluarse "
        "sin depender de otro átomo para entender su proposición."
    )

    lines.append(
        "- `redundancy`: indica si el modelo produjo átomos "
        "semánticamente redundantes."
    )

    lines.append("")
    lines.append(
        "Resultado manual sugerido:"
    )
    lines.append("")

    lines.append(
        "- `good`: atomización utilizable sin cambios importantes."
    )
    lines.append(
        "- `acceptable`: significado preservado pero con "
        "sobre-atomización o redundancia."
    )
    lines.append(
        "- `bad`: pérdida, invención, contaminación o "
        "descomposición semánticamente incorrecta."
    )

    lines.append("")
    lines.append("---")
    lines.append("")

    for dataset_id in sorted(
        dataset_by_id
    ):
        source = dataset_by_id[
            dataset_id
        ]

        gt = sorted(
            gt_by_id[
                dataset_id
            ],
            key=lambda row: int(
                row["atom_order"]
            ),
        )

        predictions = sorted(
            pred_by_id.get(
                dataset_id,
                [],
            ),
            key=lambda row: int(
                row[
                    "predicted_atom_order"
                ]
            ),
        )

        structure = structure_by_id[
            dataset_id
        ]

        lines.append(
            f"## {dataset_id}"
        )
        lines.append("")

        lines.append(
            f"**Calibration:** "
            f"`{source['calibration_id']}`"
        )
        lines.append("")

        lines.append(
            f"**Source claim ID:** "
            f"`{source['source_claim_id']}`"
        )
        lines.append("")

        lines.append(
            f"**Format:** "
            f"`{source['format']}`"
        )
        lines.append("")

        lines.append(
            f"**Human source support:** "
            f"`{source['human_support_label']}`"
        )
        lines.append("")

        lines.append(
            "### Source claim"
        )
        lines.append("")

        lines.append(
            source[
                "source_claim_text"
            ]
        )
        lines.append("")

        lines.append(
            "### Structural result"
        )
        lines.append("")

        lines.append(
            f"- expected class: "
            f"`{structure['expected_class']}`"
        )

        lines.append(
            f"- predicted class: "
            f"`{structure['predicted_class']}`"
        )

        lines.append(
            f"- expected atoms: "
            f"`{structure['expected_count']}`"
        )

        lines.append(
            f"- predicted atoms: "
            f"`{structure['predicted_count']}`"
        )

        lines.append(
            f"- exact structure: "
            f"`{structure['exact_structure']}`"
        )

        lines.append(
            f"- structural error: "
            f"`{structure['atomization_error']}`"
        )

        lines.append("")

        lines.append(
            "### Frozen ground truth"
        )
        lines.append("")

        for row in gt:
            lines.append(
                f"{row['atom_order']}. "
                f"`[{row['atom_type']}]` "
                f"{row['atom_text']}"
            )

            lines.append(
                f"   - expected support: "
                f"`{row['expected_support']}`"
            )

        lines.append("")

        lines.append(
            "### Gemini v0.1 prediction"
        )
        lines.append("")

        if not predictions:
            lines.append(
                "_No successful prediction._"
            )

        for row in predictions:
            lines.append(
                f"{row['predicted_atom_order']}. "
                f"`[{row['predicted_atom_type']}]` "
                f"{row['predicted_atom_text']}"
            )

        lines.append("")

        lines.append(
            "### Manual semantic review"
        )
        lines.append("")

        lines.append(
            "**meaning_preserved:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**qualifiers_preserved:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**no_invented_information:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**relations_isolated:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**atoms_independently_evaluable:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**redundancy:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**semantic_quality:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**review_notes:** PENDING"
        )
        lines.append("")

        lines.append("---")
        lines.append("")

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=" * 80)
    print(
        "CLAIM ATOMIZATION V1 — "
        "SEMANTIC REVIEW PACKET"
    )
    print("=" * 80)

    print(
        "Source claims:",
        len(dataset_by_id),
    )

    print()

    print(
        "Output:",
        OUTPUT_MD,
    )

    print()

    print(
        "No ground-truth or prediction files were modified."
    )


if __name__ == "__main__":
    main()