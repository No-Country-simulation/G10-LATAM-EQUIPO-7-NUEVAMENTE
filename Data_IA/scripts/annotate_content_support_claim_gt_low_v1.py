"""Anota ground truth humano de claims low-priority.

Basado exclusivamente en chunks_used.

NO modifica producción.
"""

from __future__ import annotations

import csv
from pathlib import Path


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

GT_FILE = (
    RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)


ANNOTATIONS = {
    (
        "CAL-V1-001",
        "question_1_answer_claim_1",
    ): (
        "supported",
        "Los tipos de soluciones de IA y las prácticas de IA responsable aparecen explícitamente en chunks_used.",
    ),

    (
        "CAL-V1-001",
        "question_1_explanation_claim_1",
    ): (
        "supported",
        "Es una reformulación directa de los objetivos indicados en el chunk.",
    ),

    (
        "CAL-V1-003",
        "key_point_1_claim_1",
    ): (
        "supported",
        "Crear solicitudes eficaces para LLM aparece explícitamente como objetivo de aprendizaje.",
    ),

    (
        "CAL-V1-003",
        "key_point_3_claim_1",
    ): (
        "supported",
        "Los conceptos LLM y solicitudes eficaces están explícitamente presentes en chunks_used.",
    ),

    (
        "CAL-V1-003",
        "summary_claim_2",
    ): (
        "supported",
        "Los modelos de lenguaje grande (LLM) aparecen explícitamente en el chunk.",
    ),

    (
        "CAL-V1-003",
        "summary_claim_3",
    ): (
        "supported",
        "Las solicitudes aparecen explícitamente como contenido del módulo.",
    ),

    (
        "CAL-V1-003",
        "summary_claim_4",
    ): (
        "supported",
        "Crear solicitudes aparece explícitamente dentro de los objetivos de aprendizaje.",
    ),

    (
        "CAL-V1-009",
        "key_point_1_claim_1",
    ): (
        "supported",
        "Almacenar y actualizar valores mediante variables aparece explícitamente en los objetivos.",
    ),

    (
        "CAL-V1-009",
        "key_point_2_claim_1",
    ): (
        "supported",
        "Realizar operaciones aritméticas con números aparece explícitamente en los objetivos.",
    ),

    (
        "CAL-V1-009",
        "key_point_3_claim_1",
    ): (
        "supported",
        "Convertir entre tipos de datos mediante funciones integradas aparece explícitamente.",
    ),

    (
        "CAL-V1-009",
        "summary_claim_1",
    ): (
        "supported",
        "Resume de forma fiel variables, operaciones numéricas y conversión de tipos descritos en chunks_used.",
    ),

    (
        "CAL-V1-011",
        "question_1_answer_claim_1",
    ): (
        "supported",
        "La agregación de datos aparece explícitamente como concepto y objetivo del módulo.",
    ),

    (
        "CAL-V1-011",
        "question_1_explanation_claim_1",
    ): (
        "supported",
        "La agregación de datos está explícitamente respaldada por chunks_used.",
    ),

    (
        "CAL-V1-012",
        "card_1_back_claim_1",
    ): (
        "supported",
        "Agregación, agrupación y visualizaciones de datos aparecen explícitamente en los objetivos.",
    ),

    (
        "CAL-V1-013",
        "scene_1_narration_claim_1",
    ): (
        "supported",
        "Es una reformulación directa de la definición de HTML presente en el chunk.",
    ),

    (
        "CAL-V1-015",
        "card_1_back_claim_1",
    ): (
        "supported",
        "Funciones, eventos, bucles y condicionales aparecen explícitamente en chunks_used.",
    ),

    (
        "CAL-V1-017",
        "question_1_answer_claim_1",
    ): (
        "supported",
        "Coincide directamente con la definición de Kubernetes del chunk.",
    ),

    (
        "CAL-V1-017",
        "question_1_explanation_claim_1",
    ): (
        "supported",
        "Reproduce directamente la definición de Kubernetes incluida en la evidencia.",
    ),

    (
        "CAL-V1-020",
        "scene_1_narration_claim_1",
    ): (
        "supported",
        "El chunk menciona explícitamente una visión general de servicios de Azure y ejercicios prácticos para implementar los primeros servicios.",
    ),

    (
        "CAL-V1-020",
        "scene_2_narration_claim_1",
    ): (
        "unsupported",
        "El chunk respalda que la serie enseña conceptos básicos de la nube, pero no establece la relación temporal 'Antes de eso'.",
    ),
}


def main() -> None:
    with GT_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

        if not rows:
            raise RuntimeError(
                "Ground truth manifest is empty."
            )

        fieldnames = list(
            rows[0].keys()
        )

    updated = 0
    missing = []

    for (
        calibration_id,
        claim_id,
    ), (
        label,
        notes,
    ) in ANNOTATIONS.items():

        match = next(
            (
                row
                for row in rows
                if (
                    row["calibration_id"]
                    == calibration_id
                    and row["claim_id"]
                    == claim_id
                )
            ),
            None,
        )

        if match is None:
            missing.append(
                (
                    calibration_id,
                    claim_id,
                )
            )
            continue

        match[
            "human_support_label"
        ] = label

        match[
            "human_notes"
        ] = notes

        updated += 1

    if missing:
        print(
            "ERROR: claims no encontrados:"
        )

        for (
            calibration_id,
            claim_id,
        ) in missing:
            print(
                "-",
                calibration_id,
                claim_id,
            )

        print()
        print(
            "No se modificó el archivo."
        )

        return

    with GT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    supported = sum(
        label == "supported"
        for label, _ in (
            ANNOTATIONS.values()
        )
    )

    unsupported = sum(
        label == "unsupported"
        for label, _ in (
            ANNOTATIONS.values()
        )
    )

    uncertain = sum(
        label == "uncertain"
        for label, _ in (
            ANNOTATIONS.values()
        )
    )

    total_annotated = sum(
        bool(
            row[
                "human_support_label"
            ].strip()
        )
        for row in rows
    )

    print("=" * 70)
    print(
        "LOW PRIORITY CLAIM GT ANNOTATION"
    )
    print("=" * 70)

    print(
        "Updated claims:",
        updated,
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
        "Uncertain:",
        uncertain,
    )

    print()

    print(
        "Total annotated:",
        total_annotated,
    )

    print()

    print(
        "File:",
        GT_FILE,
    )


if __name__ == "__main__":
    main()