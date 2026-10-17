"""Escribe la revisión humana de atomicidad de claims unsupported.

NO modifica producción ni ground truth.
"""

from __future__ import annotations

import csv
from pathlib import Path


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

OUTPUT_CSV = (
    RESULTS_DIR
    / "content_support_atomization_analysis_v1.csv"
)


ROWS = [
    {
        "calibration_id": "CAL-V1-004",
        "claim_id": "scene_1_narration_claim_2",
        "atomization_type": "atomic_unsupported",
        "atomic_claim_1": (
            "Los agentes de IA pueden desplegar modelos en producción "
            "de forma autónoma sin supervisión humana."
        ),
        "atomic_claim_1_support": "unsupported",
        "atomic_claim_2": "",
        "atomic_claim_2_support": "",
        "atomic_claim_3": "",
        "atomic_claim_3_support": "",
        "analysis_notes": (
            "La proposición factual completa carece de respaldo en chunks_used."
        ),
    },
    {
        "calibration_id": "CAL-V1-006",
        "claim_id": "key_point_3_claim_1",
        "atomization_type": "atomic_unsupported",
        "atomic_claim_1": (
            "El decorador cifra automáticamente todas las respuestas GET."
        ),
        "atomic_claim_1_support": "unsupported",
        "atomic_claim_2": "",
        "atomic_claim_2_support": "",
        "atomic_claim_3": "",
        "atomic_claim_3_support": "",
        "analysis_notes": (
            "Los chunks describen asociación de path y operación GET, "
            "pero no cifrado."
        ),
    },
    {
        "calibration_id": "CAL-V1-014",
        "claim_id": "question_1_explanation_claim_2",
        "atomization_type": "atomic_unsupported",
        "atomic_claim_1": (
            "Usar etiquetas HTML mejora automáticamente "
            "el posicionamiento SEO de una página."
        ),
        "atomic_claim_1_support": "unsupported",
        "atomic_claim_2": "",
        "atomic_claim_2_support": "",
        "atomic_claim_3": "",
        "atomic_claim_3_support": "",
        "analysis_notes": (
            "Los chunks no contienen afirmaciones sobre SEO."
        ),
    },
    {
        "calibration_id": "CAL-V1-015",
        "claim_id": "card_2_back_claim_2",
        "atomization_type": "mixed_compound",
        "atomic_claim_1": (
            "Los cuatro elementos mencionados son bloques "
            "fundamentales de JavaScript."
        ),
        "atomic_claim_1_support": "supported",
        "atomic_claim_2": (
            "Los cuatro bloques no tienen una secuencia clara."
        ),
        "atomic_claim_2_support": "unsupported",
        "atomic_claim_3": "",
        "atomic_claim_3_support": "",
        "analysis_notes": (
            "Combina un hecho respaldado con una afirmación "
            "adicional sobre ausencia de secuencia."
        ),
    },
    {
        "calibration_id": "CAL-V1-016",
        "claim_id": "conclusion_claim_1",
        "atomization_type": "relation_unsupported",
        "atomic_claim_1": (
            "Los eventos son ocurrencias reportadas por el sistema."
        ),
        "atomic_claim_1_support": "supported",
        "atomic_claim_2": (
            "El sistema permite responder a esas ocurrencias."
        ),
        "atomic_claim_2_support": "supported",
        "atomic_claim_3": (
            "El paradigma dirigido por eventos desacopla "
            "la ocurrencia de la lógica reactiva."
        ),
        "atomic_claim_3_support": "unsupported",
        "analysis_notes": (
            "Los hechos base están respaldados; la relación "
            "de desacoplamiento es una extrapolación."
        ),
    },
    {
        "calibration_id": "CAL-V1-018",
        "claim_id": "card_1_back_claim_2",
        "atomization_type": "atomic_unsupported",
        "atomic_claim_1": (
            "Kubernetes cifra automáticamente todo el tráfico "
            "del clúster por defecto."
        ),
        "atomic_claim_1_support": "unsupported",
        "atomic_claim_2": "",
        "atomic_claim_2_support": "",
        "atomic_claim_3": "",
        "atomic_claim_3_support": "",
        "analysis_notes": (
            "No existe evidencia de cifrado automático del tráfico."
        ),
    },
    {
        "calibration_id": "CAL-V1-020",
        "claim_id": "scene_2_narration_claim_1",
        "atomization_type": "relation_unsupported",
        "atomic_claim_1": (
            "La serie enseña conceptos básicos de la nube."
        ),
        "atomic_claim_1_support": "supported",
        "atomic_claim_2": (
            "La enseñanza de esos conceptos ocurre antes "
            "del evento o contexto referido."
        ),
        "atomic_claim_2_support": "unsupported",
        "atomic_claim_3": "",
        "atomic_claim_3_support": "",
        "analysis_notes": (
            "Este fue el falso negativo común de legacy y Gemini. "
            "El hecho principal está respaldado, pero la relación "
            "temporal 'Antes de eso' no."
        ),
    },
    {
        "calibration_id": "CAL-V1-020",
        "claim_id": "scene_2_narration_claim_2",
        "atomization_type": "relation_unsupported",
        "atomic_claim_1": (
            "La serie incluye ejercicios prácticos."
        ),
        "atomic_claim_1_support": "supported",
        "atomic_claim_2": (
            "La serie proporciona una visión general de "
            "servicios de Azure."
        ),
        "atomic_claim_2_support": "supported",
        "atomic_claim_3": (
            "Después se vuelve a los ejercicios y a los "
            "servicios de Azure."
        ),
        "atomic_claim_3_support": "unsupported",
        "analysis_notes": (
            "Los hechos base están respaldados, pero la "
            "secuencia temporal de retorno no aparece en chunks_used."
        ),
    },
]


def main() -> None:
    fieldnames = list(
        ROWS[0].keys()
    )

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
            ROWS
        )

    counts: dict[str, int] = {}

    for row in ROWS:
        category = row[
            "atomization_type"
        ]

        counts[category] = (
            counts.get(
                category,
                0,
            )
            + 1
        )

    decomposable = sum(
        count
        for category, count
        in counts.items()
        if category in {
            "mixed_compound",
            "relation_unsupported",
        }
    )

    print("=" * 72)
    print(
        "CONTENT SUPPORT ATOMIZATION ANALYSIS V1"
    )
    print("=" * 72)

    print(
        "Unsupported claims:",
        len(ROWS),
    )

    print()

    for category in [
        "atomic_unsupported",
        "mixed_compound",
        "relation_unsupported",
        "unclear_segmentation",
    ]:
        print(
            f"{category} = "
            f"{counts.get(category, 0)}"
        )

    print()

    print(
        "Structurally decomposable:",
        decomposable,
    )

    print(
        "Decomposable rate:",
        f"{decomposable / len(ROWS):.4f}",
    )

    print()

    print(
        "Output:",
        OUTPUT_CSV,
    )


if __name__ == "__main__":
    main()