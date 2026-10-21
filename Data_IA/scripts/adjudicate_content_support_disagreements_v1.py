"""Aplica adjudicación humana final a desacuerdos humano vs Gemini.

NO modifica producción.

Actualiza únicamente human_support_label y human_notes
en content_support_claim_ground_truth_v1.csv.
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


ADJUDICATIONS = {
    (
        "CAL-V1-003",
        "conclusion_claim_1",
    ): (
        "uncertain",
        (
            "El claim parece referirse al objetivo de crear "
            "solicitudes eficaces para LLM, pero su redacción "
            "es autorreferencial y ambigua; chunks_used no "
            "permite establecer una equivalencia semántica "
            "suficientemente clara."
        ),
    ),

    (
        "CAL-V1-015",
        "card_2_back_claim_2",
    ): (
        "unsupported",
        (
            "Los chunks respaldan que existen cuatro bloques "
            "fundamentales, pero no respaldan la afirmación "
            "adicional de que estén 'sin una secuencia clara'."
        ),
    ),

    (
        "CAL-V1-019",
        "key_point_2_claim_1",
    ): (
        "supported",
        (
            "El chunk incluye una sección 'Introducción a Azure' "
            "con opciones para elegir cuenta, pagar por uso o "
            "probar Azure gratis, lo que respalda el claim."
        ),
    ),

    (
        "CAL-V1-020",
        "scene_2_narration_claim_2",
    ): (
        "unsupported",
        (
            "Los chunks mencionan ejercicios prácticos y "
            "servicios de Azure, pero no establecen que se "
            "vuelva a ellos posteriormente ni esa secuencia "
            "temporal concreta."
        ),
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
    ) in ADJUDICATIONS.items():

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

    print("=" * 70)
    print(
        "CONTENT SUPPORT DISAGREEMENT ADJUDICATION V1"
    )
    print("=" * 70)

    print(
        "Updated claims:",
        updated,
    )

    print()
    print(
        "CAL-V1-003 conclusion_claim_1 -> uncertain"
    )

    print(
        "CAL-V1-015 card_2_back_claim_2 -> unsupported"
    )

    print(
        "CAL-V1-019 key_point_2_claim_1 -> supported"
    )

    print(
        "CAL-V1-020 scene_2_narration_claim_2 -> unsupported"
    )

    print()
    print(
        "File:",
        GT_FILE,
    )


if __name__ == "__main__":
    main()