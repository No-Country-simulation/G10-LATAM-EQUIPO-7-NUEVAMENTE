"""Anota el ground truth humano de los claims high-priority.

Este script actualiza únicamente:

content_support_claim_ground_truth_v1.csv

con las etiquetas humanas revisadas contra chunks_used.

Regla:
- supported: respaldado explícitamente o por equivalencia semántica clara;
- unsupported: introduce información factual no respaldada;
- uncertain: la evidencia no permite decidir con suficiente confianza.

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
    # --------------------------------------------------------
    # CAL-V1-004
    # --------------------------------------------------------
    (
        "CAL-V1-004",
        "scene_1_narration_claim_1",
    ): (
        "supported",
        "El chunk respalda los conceptos básicos de agentes "
        "y soluciones de inteligencia artificial agente.",
    ),
    (
        "CAL-V1-004",
        "scene_1_narration_claim_2",
    ): (
        "unsupported",
        "Los chunks no respaldan despliegue autónomo de "
        "modelos ni ausencia de supervisión humana.",
    ),

    # --------------------------------------------------------
    # CAL-V1-006
    # --------------------------------------------------------
    (
        "CAL-V1-006",
        "summary_claim_1",
    ): (
        "supported",
        "El chunk indica que @app.get('/') asocia la "
        "función inferior con requests GET al path '/'.",
    ),
    (
        "CAL-V1-006",
        "key_point_1_claim_1",
    ): (
        "supported",
        "El path '/' está explícitamente respaldado.",
    ),
    (
        "CAL-V1-006",
        "key_point_2_claim_1",
    ): (
        "supported",
        "La operación GET está explícitamente respaldada.",
    ),
    (
        "CAL-V1-006",
        "key_point_3_claim_1",
    ): (
        "unsupported",
        "Los chunks no mencionan cifrado automático de "
        "respuestas GET.",
    ),
    (
        "CAL-V1-006",
        "conclusion_claim_1",
    ): (
        "supported",
        "Es una reformulación del vínculo entre la función, "
        "el path '/' y la operación GET descrito en chunks_used.",
    ),

    # --------------------------------------------------------
    # CAL-V1-014
    # --------------------------------------------------------
    (
        "CAL-V1-014",
        "question_1_answer_claim_1",
    ): (
        "supported",
        "El chunk indica que los elementos HTML pueden marcar "
        "partes del contenido para que aparezcan o actúen "
        "de cierta manera.",
    ),
    (
        "CAL-V1-014",
        "question_1_explanation_claim_1",
    ): (
        "supported",
        "Es una reformulación directa del contenido del chunk.",
    ),
    (
        "CAL-V1-014",
        "question_1_explanation_claim_2",
    ): (
        "unsupported",
        "El chunk no contiene información sobre mejora "
        "automática del posicionamiento SEO.",
    ),

    # --------------------------------------------------------
    # CAL-V1-016
    # --------------------------------------------------------
    (
        "CAL-V1-016",
        "summary_claim_1",
    ): (
        "supported",
        "El chunk describe eventos como ocurrencias durante "
        "la ejecución que son reportadas para permitir una "
        "respuesta; la frase es una reformulación técnica.",
    ),
    (
        "CAL-V1-016",
        "key_point_1_claim_1",
    ): (
        "supported",
        "El chunk presenta explícitamente el click en un botón "
        "como evento que puede iniciar una acción.",
    ),
    (
        "CAL-V1-016",
        "key_point_2_claim_1",
    ): (
        "supported",
        "El chunk respalda que la respuesta al evento puede "
        "mostrar información en un elemento de interfaz.",
    ),
    (
        "CAL-V1-016",
        "conclusion_claim_1",
    ): (
        "unsupported",
        "El chunk no establece explícitamente un desacoplamiento "
        "entre ocurrencia notificable y lógica reactiva; es una "
        "extrapolación respecto de la evidencia disponible.",
    ),

    # --------------------------------------------------------
    # CAL-V1-018
    # --------------------------------------------------------
    (
        "CAL-V1-018",
        "card_1_back_claim_1",
    ): (
        "supported",
        "El chunk enumera Kubernetes como plataforma de "
        "contenedores, microservicios y plataforma portable "
        "de nube.",
    ),
    (
        "CAL-V1-018",
        "card_1_back_claim_2",
    ): (
        "unsupported",
        "Los chunks no afirman que Kubernetes cifre "
        "automáticamente todo el tráfico del clúster.",
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

    for key, annotation in (
        ANNOTATIONS.items()
    ):
        calibration_id, claim_id = key
        label, notes = annotation

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
            "ERROR: algunos claim_id "
            "no fueron encontrados:"
        )

        for item in missing:
            print(
                "-",
                item[0],
                item[1],
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
        1
        for (
            label,
            _,
        ) in ANNOTATIONS.values()
        if label == "supported"
    )

    unsupported = sum(
        1
        for (
            label,
            _,
        ) in ANNOTATIONS.values()
        if label == "unsupported"
    )

    uncertain = sum(
        1
        for (
            label,
            _,
        ) in ANNOTATIONS.values()
        if label == "uncertain"
    )

    print("=" * 70)
    print(
        "HIGH PRIORITY CLAIM GT ANNOTATION"
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
        "File:",
        GT_FILE,
    )


if __name__ == "__main__":
    main()