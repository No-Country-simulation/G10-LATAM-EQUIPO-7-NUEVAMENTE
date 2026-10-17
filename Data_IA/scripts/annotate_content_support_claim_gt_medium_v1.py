"""Anota ground truth humano de claims medium-priority.

Basado exclusivamente en chunks_used del review packet v1.

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
    ("CAL-V1-002", "card_1_back_claim_1"): (
        "supported",
        "El chunk indica que el conocimiento conceptual de ML puede ser útil, aunque no es necesario.",
    ),

    ("CAL-V1-003", "conclusion_claim_1"): (
        "supported",
        "Reformula el objetivo del módulo de considerar cómo crear solicitudes eficaces para LLM.",
    ),
    ("CAL-V1-003", "key_point_2_claim_1"): (
        "supported",
        "El chunk incluye explícitamente los modelos de lenguaje grande (LLM) como contenido del módulo.",
    ),
    ("CAL-V1-003", "summary_claim_1"): (
        "supported",
        "Coincide con el objetivo de aprendizaje sobre crear solicitudes eficaces para LLM.",
    ),
    ("CAL-V1-003", "summary_claim_5"): (
        "supported",
        "El objetivo aparece dentro de la lista de habilidades u objetivos de aprendizaje del módulo.",
    ),

    ("CAL-V1-005", "card_1_back_claim_1"): (
        "supported",
        "El chunk contiene explícitamente 'from fastapi import FastAPI'.",
    ),

    ("CAL-V1-007", "scene_1_narration_claim_1"): (
        "supported",
        "El chunk indica que deben evitarse nombres de proyectos iguales a componentes integrados de Python o Django, incluyendo django y test.",
    ),

    ("CAL-V1-008", "question_1_answer_claim_1"): (
        "supported",
        "El chunk define una app como aplicación que realiza una función y un project como colección de configuración y apps que puede contener múltiples aplicaciones.",
    ),
    ("CAL-V1-008", "question_1_explanation_claim_1"): (
        "supported",
        "Es una reformulación semántica de la diferencia entre app y project descrita en chunks_used.",
    ),

    ("CAL-V1-009", "conclusion_claim_1"): (
        "supported",
        "Almacenar y actualizar valores mediante variables aparece explícitamente como objetivo de aprendizaje.",
    ),

    ("CAL-V1-010", "scene_1_narration_claim_1"): (
        "supported",
        "La formulación técnica corresponde a variables, operaciones aritméticas y conversión de tipos descritas en el chunk.",
    ),

    ("CAL-V1-011", "question_1_explanation_claim_2"): (
        "uncertain",
        "El pronombre 'la' no tiene un antecedente identificable dentro del claim aislado; chunks_used no permite resolver inequívocamente la referencia.",
    ),
    ("CAL-V1-011", "question_1_explanation_claim_3"): (
        "supported",
        "Agregación, agrupación y visualizaciones aparecen explícitamente entre los contenidos y objetivos del módulo.",
    ),
    ("CAL-V1-011", "question_1_explanation_claim_4"): (
        "uncertain",
        "El concepto agregación está respaldado, pero determinar que es 'la respuesta' requiere el contexto de la pregunta y no solamente chunks_used.",
    ),

    ("CAL-V1-013", "scene_1_narration_claim_2"): (
        "supported",
        "Es semánticamente equivalente al chunk sobre marcar diferentes partes del contenido para que aparezcan o actúen de cierta manera.",
    ),

    ("CAL-V1-015", "card_1_back_claim_2"): (
        "supported",
        "Los cuatro conceptos indicados aparecen explícitamente en el módulo.",
    ),
    ("CAL-V1-015", "card_2_back_claim_1"): (
        "supported",
        "Enumera eventos, funciones, condicionales y bucles, todos respaldados por chunks_used; 'después' se interpreta como formulación discursiva.",
    ),
    ("CAL-V1-015", "card_2_back_claim_2"): (
        "supported",
        "Los cuatro elementos aparecen como bloques fundamentales y los chunks no establecen una secuencia obligatoria.",
    ),

    ("CAL-V1-019", "conclusion_claim_1"): (
        "supported",
        "La existencia de requisitos previos antes de los módulos de la ruta respalda la referencia a preparación previa.",
    ),
    ("CAL-V1-019", "key_point_1_claim_1"): (
        "supported",
        "El chunk indica explícitamente conocimientos básicos de términos y conceptos de TI como requisito previo.",
    ),
    ("CAL-V1-019", "key_point_2_claim_1"): (
        "supported",
        "La sección de introducción presenta opciones de cuenta, pago por uso y prueba gratuita para comenzar con Azure.",
    ),
    ("CAL-V1-019", "summary_claim_1"): (
        "supported",
        "Reformula directamente el requisito previo indicado en chunks_used.",
    ),

    ("CAL-V1-020", "scene_2_narration_claim_2"): (
        "supported",
        "Chunks_used menciona tanto ejercicios prácticos como servicios de Azure; la transición temporal se considera narrativa.",
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
        for (
            label,
            _,
        ) in ANNOTATIONS.values()
    )

    unsupported = sum(
        label == "unsupported"
        for (
            label,
            _,
        ) in ANNOTATIONS.values()
    )

    uncertain = sum(
        label == "uncertain"
        for (
            label,
            _,
        ) in ANNOTATIONS.values()
    )

    print("=" * 70)
    print(
        "MEDIUM PRIORITY CLAIM GT ANNOTATION"
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
        "Total annotated so far:",
        sum(
            bool(
                row[
                    "human_support_label"
                ].strip()
            )
            for row in rows
        ),
    )

    print()
    print(
        "File:",
        GT_FILE,
    )


if __name__ == "__main__":
    main()