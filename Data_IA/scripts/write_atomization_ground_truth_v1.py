"""Writes the manually reviewed Claim Atomization v1 ground truth.

This file contains HUMAN-DEFINED expected atomizations.

It does NOT:
- call Gemini;
- modify production;
- modify calibration_v1 ground truth.
"""

from __future__ import annotations

import csv
from pathlib import Path


ATOMIZATION_DIR = Path(
    "data/evaluation/atomization_v1"
)

OUTPUT_GT = (
    ATOMIZATION_DIR
    / "atomization_ground_truth_v1.csv"
)


ROWS = [
    # ------------------------------------------------------------------
    # ATOM-V1-001
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-001",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-001-A01",
        "atom_order": 1,
        "atom_text": (
            "Los agentes de IA pueden desplegar modelos en producción "
            "de forma autónoma sin supervisión humana."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "unsupported",
        "notes": (
            "El claim ya constituye una afirmación factual evaluable; "
            "los calificadores autónoma y sin supervisión humana "
            "se conservan."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-002
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-002",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-002-A01",
        "atom_order": 1,
        "atom_text": (
            "El decorador cifra automáticamente todas las respuestas GET."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "unsupported",
        "notes": (
            "Se conservan automáticamente y todas; la evidencia describe "
            "routing GET, no cifrado."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-003
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-003",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-003-A01",
        "atom_order": 1,
        "atom_text": (
            "Usar etiquetas HTML mejora automáticamente "
            "el posicionamiento SEO de una página."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "unsupported",
        "notes": (
            "El claim ya es evaluable como una proposición; "
            "SEO no está respaldado."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-004
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-004",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-004-A01",
        "atom_order": 1,
        "atom_text": (
            "Los cuatro elementos mencionados son bloques "
            "fundamentales de JavaScript."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": (
            "Los chunks describen bucles, funciones, condicionales "
            "y eventos como bloques fundamentales."
        ),
    },
    {
        "dataset_id": "ATOM-V1-004",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-004-A02",
        "atom_order": 2,
        "atom_text": (
            "Los cuatro bloques no tienen una secuencia clara."
        ),
        "atom_type": "negation_or_absence",
        "expected_support": "unsupported",
        "notes": (
            "La ausencia de una secuencia clara no está respaldada."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-005
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-005",
        "atomization_class": "relational",
        "atom_id": "ATOM-V1-005-A01",
        "atom_order": 1,
        "atom_text": (
            "El paradigma dirigido por eventos desacopla la ocurrencia "
            "notificable de la lógica reactiva que procesa dicha señal."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "unsupported",
        "notes": (
            "Se conserva como una única relación factual. "
            "No se introducen hechos derivados de chunks_used que no "
            "formen parte del source claim."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-006
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-006",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-006-A01",
        "atom_order": 1,
        "atom_text": (
            "Kubernetes cifra automáticamente todo el tráfico "
            "del clúster por defecto."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "unsupported",
        "notes": (
            "Se preservan automáticamente, todo y por defecto."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-007
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-007",
        "atomization_class": "relational",
        "atom_id": "ATOM-V1-007-A01",
        "atom_order": 1,
        "atom_text": (
            "La serie enseña conceptos básicos de la nube."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": (
            "Proposición principal explícitamente respaldada."
        ),
    },
    {
        "dataset_id": "ATOM-V1-007",
        "atomization_class": "relational",
        "atom_id": "ATOM-V1-007-A02",
        "atom_order": 2,
        "atom_text": (
            "La enseñanza de conceptos básicos de la nube ocurre "
            "antes del evento o contexto referido."
        ),
        "atom_type": "temporal_relation",
        "expected_support": "unsupported",
        "notes": (
            "Conserva el significado factual de 'Antes de eso'."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-008
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-008",
        "atomization_class": "relational",
        "atom_id": "ATOM-V1-008-A01",
        "atom_order": 1,
        "atom_text": (
            "La serie incluye ejercicios prácticos."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },
    {
        "dataset_id": "ATOM-V1-008",
        "atomization_class": "relational",
        "atom_id": "ATOM-V1-008-A02",
        "atom_order": 2,
        "atom_text": (
            "La serie presenta servicios de Azure."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },
    {
        "dataset_id": "ATOM-V1-008",
        "atomization_class": "relational",
        "atom_id": "ATOM-V1-008-A03",
        "atom_order": 3,
        "atom_text": (
            "Después se vuelve a los ejercicios y a los servicios de Azure."
        ),
        "atom_type": "temporal_relation",
        "expected_support": "unsupported",
        "notes": (
            "La evidencia menciona ambos contenidos pero no establece "
            "la relación temporal de retorno."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-009
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-009",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-009-A01",
        "atom_order": 1,
        "atom_text": (
            "El módulo introduce los tipos de soluciones que la "
            "inteligencia artificial puede hacer posible."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },
    {
        "dataset_id": "ATOM-V1-009",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-009-A02",
        "atom_order": 2,
        "atom_text": (
            "El módulo considera prácticas de inteligencia "
            "artificial responsable."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },

    # ------------------------------------------------------------------
    # ATOM-V1-010
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-010",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-010-A01",
        "atom_order": 1,
        "atom_text": (
            "Crear solicitudes eficaces para LLM."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": (
            "Claim ya mínimo para esta tarea."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-011
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-011",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-011-A01",
        "atom_order": 1,
        "atom_text": (
            "FastAPI es una clase."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "uncertain",
        "notes": (
            "chunks_used muestra la importación pero no declara "
            "explícitamente el tipo de símbolo FastAPI. "
            "Requiere adjudicación antes de congelar el GT."
        ),
    },
    {
        "dataset_id": "ATOM-V1-011",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-011-A02",
        "atom_order": 2,
        "atom_text": (
            "FastAPI se importa desde el paquete fastapi mediante "
            "'from fastapi import FastAPI'."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": (
            "Respaldado directamente por el código del chunk."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-012
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-012",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-012-A01",
        "atom_order": 1,
        "atom_text": (
            "El módulo enseña a almacenar y manipular datos en Python."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },
    {
        "dataset_id": "ATOM-V1-012",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-012-A02",
        "atom_order": 2,
        "atom_text": (
            "El módulo incluye el uso de variables."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },
    {
        "dataset_id": "ATOM-V1-012",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-012-A03",
        "atom_order": 3,
        "atom_text": (
            "El módulo incluye operaciones numéricas."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },
    {
        "dataset_id": "ATOM-V1-012",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-012-A04",
        "atom_order": 4,
        "atom_text": (
            "El módulo incluye conversión de tipos."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },

    # ------------------------------------------------------------------
    # ATOM-V1-013
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-013",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-013-A01",
        "atom_order": 1,
        "atom_text": (
            "HTML es un lenguaje de marcado."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },
    {
        "dataset_id": "ATOM-V1-013",
        "atomization_class": "compound",
        "atom_id": "ATOM-V1-013-A02",
        "atom_order": 2,
        "atom_text": (
            "HTML indica a los navegadores web cómo estructurar "
            "las páginas que visitamos."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },

    # ------------------------------------------------------------------
    # ATOM-V1-014
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-014",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-014-A01",
        "atom_order": 1,
        "atom_text": (
            "El contenido abarca funciones, eventos, bucles "
            "y condicionales."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": (
            "La lista puede evaluarse como una unidad factual sin "
            "necesidad de generar cuatro átomos independientes."
        ),
    },

    # ------------------------------------------------------------------
    # ATOM-V1-015
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-015",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-015-A01",
        "atom_order": 1,
        "atom_text": (
            "El documento define Kubernetes como una plataforma "
            "portable y extensible de código abierto para administrar "
            "cargas de trabajo y servicios."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": "",
    },

    # ------------------------------------------------------------------
    # ATOM-V1-016
    # ------------------------------------------------------------------
    {
        "dataset_id": "ATOM-V1-016",
        "atomization_class": "atomic",
        "atom_id": "ATOM-V1-016-A01",
        "atom_order": 1,
        "atom_text": (
            "La sección presenta opciones para comenzar con Azure."
        ),
        "atom_type": "factual_proposition",
        "expected_support": "supported",
        "notes": (
            "El chunk ofrece elegir cuenta, pago por uso "
            "o prueba gratuita."
        ),
    },
]


def main() -> None:
    ATOMIZATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "dataset_id",
        "atomization_class",
        "atom_id",
        "atom_order",
        "atom_text",
        "atom_type",
        "expected_support",
        "notes",
    ]

    with OUTPUT_GT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(ROWS)

    dataset_ids = {
        row["dataset_id"]
        for row in ROWS
    }

    classes: dict[str, int] = {}

    for dataset_id in dataset_ids:
        atom_class = next(
            row["atomization_class"]
            for row in ROWS
            if row["dataset_id"]
            == dataset_id
        )

        classes[atom_class] = (
            classes.get(atom_class, 0)
            + 1
        )

    support_counts: dict[str, int] = {}

    for row in ROWS:
        label = row["expected_support"]

        support_counts[label] = (
            support_counts.get(label, 0)
            + 1
        )

    print("=" * 72)
    print(
        "CLAIM ATOMIZATION GROUND TRUTH V1"
    )
    print("=" * 72)

    print(
        "Source claims:",
        len(dataset_ids),
    )

    print(
        "Atomic claims:",
        len(ROWS),
    )

    print()

    print("Atomization classes:")

    for name in [
        "atomic",
        "compound",
        "relational",
    ]:
        print(
            f"  {name}: "
            f"{classes.get(name, 0)}"
        )

    print()

    print("Expected support:")

    for name in [
        "supported",
        "unsupported",
        "uncertain",
    ]:
        print(
            f"  {name}: "
            f"{support_counts.get(name, 0)}"
        )

    print()

    print(
        "Output:",
        OUTPUT_GT,
    )


if __name__ == "__main__":
    main()