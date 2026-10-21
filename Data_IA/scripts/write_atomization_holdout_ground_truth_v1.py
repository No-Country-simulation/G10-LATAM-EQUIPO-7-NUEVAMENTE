"""Write frozen Claim Atomization Holdout v1 ground truth.

This ground truth was manually defined BEFORE any automatic
atomizer was run on the holdout.

Important:
- no Gemini outputs were used;
- no v0.1/v0.2/v0.3 predictions were used;
- human_support_label was not used to determine atomization;
- non-propositional inputs are retained but excluded from
  primary atomization metrics.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1/holdout_v1"
)

OUTPUT_FILE = (
    BASE_DIR
    / "atomization_holdout_ground_truth_v1.csv"
)


ROWS = [
    # ==============================================================
    # HOLDOUT-V1-001
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-001",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-001-A01",
        "atom_order": 1,
        "atom_text": (
            "El objetivo es el objetivo de solicitudes para LLM "
            "que el módulo espera considerar."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Redacción ambigua, pero constituye una sola "
            "proposición. No se infiere significado adicional."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-002
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-002",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-002-A01",
        "atom_order": 1,
        "atom_text": (
            "La respuesta es agregación porque agregación "
            "es el concepto preguntado."
        ),
        "atom_type": "causal_relation",
        "review_notes": (
            "La justificación causal forma una sola unidad "
            "factual evaluable."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-003
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-003",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-003-A01",
        "atom_order": 1,
        "atom_text": (
            "El módulo la describe."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Claim dependiente de contexto. Se conserva el "
            "pronombre original sin inventar su referente."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-004
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-004",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Lista nominal sin predicado factual explícito."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-005
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-005",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-005-A01",
        "atom_order": 1,
        "atom_text": (
            "La aplicación encapsula una funcionalidad web concreta."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
    {
        "holdout_id": "HOLDOUT-V1-005",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-005-A02",
        "atom_order": 2,
        "atom_text": (
            "El proyecto actúa como agregado configuracional "
            "capaz de contener múltiples aplicaciones."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Dos predicados factuales independientes."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-006
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-006",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Token/etiqueta nominal aislada: 'LLM'."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-007
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-007",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-007-A01",
        "atom_order": 1,
        "atom_text": (
            "Al crear proyectos Django conviene evitar nombres "
            "que coincidan con componentes integrados de Python "
            "o Django, como django o test."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
    {
        "holdout_id": "HOLDOUT-V1-007",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-007-A02",
        "atom_order": 2,
        "atom_text": (
            "Usar nombres que coincidan con componentes integrados "
            "de Python o Django puede producir conflictos."
        ),
        "atom_type": "causal_relation",
        "review_notes": (
            "La recomendación y su justificación causal pueden "
            "evaluarse por separado."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-008
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-008",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-008-A01",
        "atom_order": 1,
        "atom_text": (
            "Esas cuatro estructuras aparecen en el módulo."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "El cuantificador 'cuatro' permanece dentro del mismo hecho."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-009
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-009",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Sintagma nominal sin predicado: 'Agregación de datos'."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-010
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-010",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-010-A01",
        "atom_order": 1,
        "atom_text": (
            "La operación HTTP utilizada es GET."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ==============================================================
    # HOLDOUT-V1-011
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-011",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-011-A01",
        "atom_order": 1,
        "atom_text": (
            "Sus elementos permiten marcar distintas partes del "
            "contenido para que aparezcan o actúen de una manera "
            "determinada."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Aparecer/actuar comparten el mismo predicado funcional."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-012
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-012",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-012-A01",
        "atom_order": 1,
        "atom_text": (
            "Una representación conceptual previa del aprendizaje "
            "automático resulta instrumental."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
    {
        "holdout_id": "HOLDOUT-V1-012",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-012-A02",
        "atom_order": 2,
        "atom_text": (
            "Poseer una representación conceptual previa del "
            "aprendizaje automático no constituye una condición "
            "normativa de acceso al itinerario formativo."
        ),
        "atom_type": "negation_or_absence",
        "review_notes": (
            "Utilidad y obligatoriedad son afirmaciones independientes."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-013
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-013",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-013-A01",
        "atom_order": 1,
        "atom_text": (
            "Las etiquetas HTML pueden marcar diferentes partes "
            "del contenido para que aparezcan o actúen de cierta manera."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ==============================================================
    # HOLDOUT-V1-014
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-014",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Sintagma nominal aislado: 'Solicitudes'."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-015
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-015",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-015-A01",
        "atom_order": 1,
        "atom_text": (
            "La serie incluye ejercicios prácticos para implementar "
            "primeros servicios."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
    {
        "holdout_id": "HOLDOUT-V1-015",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-015-A02",
        "atom_order": 2,
        "atom_text": (
            "La serie ofrece una visión general de servicios de Azure."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Dos capacidades distintas de la serie."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-016
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-016",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Fragmento introducido por 'Como' sin sujeto/predicado "
            "principal explícito."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-017
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-017",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "HOLDOUT-V1-017-A01",
        "atom_order": 1,
        "atom_text": (
            "La relación se entiende como una separación entre una "
            "unidad funcional reutilizable y el contenedor "
            "configuracional del sitio."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "La caracterización completa forma una única proposición."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-018
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-018",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Lista de términos/frases sin predicado factual explícito."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-019
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-019",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-019-A01",
        "atom_order": 1,
        "atom_text": (
            "El módulo aborda la persistencia simbólica y la "
            "mutabilidad de valores mediante variables."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
    {
        "holdout_id": "HOLDOUT-V1-019",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-019-A02",
        "atom_order": 2,
        "atom_text": (
            "El módulo aborda la operatoria aritmética."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
    {
        "holdout_id": "HOLDOUT-V1-019",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "HOLDOUT-V1-019-A03",
        "atom_order": 3,
        "atom_text": (
            "El módulo aborda la coerción explícita entre "
            "representaciones tipadas usando funciones integradas "
            "de Python."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Tres contenidos técnicamente independientes."
        ),
    },

    # ==============================================================
    # HOLDOUT-V1-020
    # ==============================================================
    {
        "holdout_id": "HOLDOUT-V1-020",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Lista fragmentaria con marcador temporal, pero sin "
            "predicado factual suficiente para reconstruir una "
            "proposición sin inventar contexto."
        ),
    },
]


def main() -> None:
    BASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "holdout_id",
        "review_status",
        "atomization_class",
        "atom_id",
        "atom_order",
        "atom_text",
        "atom_type",
        "review_notes",
    ]

    with OUTPUT_FILE.open(
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

    source_ids = {
        row["holdout_id"]
        for row in ROWS
    }

    valid_ids = {
        row["holdout_id"]
        for row in ROWS
        if row["review_status"]
        == "valid_claim"
    }

    non_propositional_ids = {
        row["holdout_id"]
        for row in ROWS
        if row["review_status"]
        == "non_propositional"
    }

    valid_atoms = [
        row
        for row in ROWS
        if row["review_status"]
        == "valid_claim"
    ]

    class_by_claim = {}

    for row in valid_atoms:
        class_by_claim[
            row["holdout_id"]
        ] = row[
            "atomization_class"
        ]

    class_counts = Counter(
        class_by_claim.values()
    )

    atom_type_counts = Counter(
        row["atom_type"]
        for row in valid_atoms
    )

    print("=" * 80)
    print(
        "CLAIM ATOMIZATION HOLDOUT GROUND TRUTH V1"
    )
    print("=" * 80)

    print(
        "Selected holdout claims:",
        len(source_ids),
    )

    print(
        "Valid claims:",
        len(valid_ids),
    )

    print(
        "Non-propositional:",
        len(non_propositional_ids),
    )

    print(
        "Expected atoms:",
        len(valid_atoms),
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
            f"{class_counts[name]}"
        )

    print()

    print("Atom types:")

    for name in [
        "factual_proposition",
        "temporal_relation",
        "causal_relation",
        "conditional_relation",
        "comparative_relation",
        "negation_or_absence",
        "scope_or_quantifier",
    ]:
        print(
            f"  {name}: "
            f"{atom_type_counts[name]}"
        )

    print()

    print(
        "Output:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()