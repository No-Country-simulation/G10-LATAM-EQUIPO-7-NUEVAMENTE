"""Write blind human ground truth for atomization final_eval_v1.

Methodological guarantees:
- v0.4 predictions were frozen before this annotation;
- this GT was produced from the blind human review packet;
- model predictions were not consulted;
- human_support_label was not used to determine structure;
- non-propositional inputs are preserved as metadata rows.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1/final_eval_v1"
)

OUTPUT_FILE = (
    BASE_DIR
    / "atomization_final_eval_ground_truth_v1.csv"
)


ROWS = [
    # ----------------------------------------------------------
    # FINAL-V1-001
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-001",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Sintagma nominal coordinado sin predicado factual "
            "explícito."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-002
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-002",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-002-A01",
        "atom_order": 1,
        "atom_text": (
            "Los LLM forman parte del módulo."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-003
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-003",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-003-A01",
        "atom_order": 1,
        "atom_text": (
            "El módulo espera considerar cómo crear "
            "solicitudes eficaces para los LLM."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Una sola afirmación sobre el contenido esperado "
            "del módulo."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-004
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-004",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Frase infinitiva sin sujeto ni afirmación factual "
            "completa."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-005
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-005",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-005-A01",
        "atom_order": 1,
        "atom_text": (
            "El objetivo aparece como una habilidad del módulo."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-006
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-006",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-006-A01",
        "atom_order": 1,
        "atom_text": (
            "El módulo incluye conceptos básicos de agentes de IA "
            "y soluciones de inteligencia artificial agéntica."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "Los dos contenidos comparten el mismo predicado "
            "'incluye' y se mantienen juntos."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-007
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-007",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-007-A01",
        "atom_order": 1,
        "atom_text": (
            "@app.get('/') vincula una función con solicitudes GET "
            "dirigidas al path raíz."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-008
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-008",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-008-A01",
        "atom_order": 1,
        "atom_text": (
            "El path configurado es '/'."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-009
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-009",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-009-A01",
        "atom_order": 1,
        "atom_text": (
            "El decorador @app.get('/') indica que la función "
            "situada debajo manejará solicitudes GET dirigidas "
            "al path raíz '/'."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "La relación decorador-función-ruta constituye una "
            "sola afirmación funcional."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-010
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-010",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-010-A01",
        "atom_order": 1,
        "atom_text": (
            "Una habilidad central del módulo es almacenar y "
            "actualizar valores mediante variables."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-011
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-011",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Frase infinitiva que nombra una habilidad, sin "
            "predicado factual explícito."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-012
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-012",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Frase infinitiva sin afirmación factual completa."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-013
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-013",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Frase infinitiva sin sujeto ni predicado factual "
            "completo."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-014
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-014",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Sintagma nominal sin predicado factual explícito."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-015
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-015",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Fragmento mixto con sujeto y objetos omitidos; "
            "reconstruirlo requeriría inventar contexto."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-016
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-016",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Frase infinitiva que expresa una acción pero no una "
            "proposición factual completa."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-017
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-017",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-017-A01",
        "atom_order": 1,
        "atom_text": (
            "Una interacción de click sobre un botón puede actuar "
            "como disparador de una rutina de respuesta."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-018
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-018",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-018-A01",
        "atom_order": 1,
        "atom_text": (
            "La reacción asociada puede materializar información "
            "en un elemento de interfaz."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-019
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-019",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "FINAL-V1-019-A01",
        "atom_order": 1,
        "atom_text": (
            "Los eventos constituyen ocurrencias observables "
            "del runtime."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
    {
        "final_eval_id": "FINAL-V1-019",
        "review_status": "valid_claim",
        "atomization_class": "compound",
        "atom_id": "FINAL-V1-019-A02",
        "atom_order": 2,
        "atom_text": (
            "La notificación de los eventos habilita mecanismos "
            "reactivos de respuesta."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "La cláusula relativa aporta una segunda afirmación "
            "independientemente evaluable."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-020
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-020",
        "review_status": "non_propositional",
        "atomization_class": "",
        "atom_id": "",
        "atom_order": "",
        "atom_text": "",
        "atom_type": "",
        "review_notes": (
            "Sintagma nominal descriptivo sin sujeto/predicado "
            "principal explícito."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-021
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-021",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-021-A01",
        "atom_order": 1,
        "atom_text": (
            "El foco aquí está en la preparación previa del "
            "estudiante antes de avanzar en la ruta."
        ),
        "atom_type": "factual_proposition",
        "review_notes": (
            "La expresión temporal funciona como parte del "
            "contenido de la preparación, no como una relación "
            "separada entre dos eventos explícitos."
        ),
    },

    # ----------------------------------------------------------
    # FINAL-V1-022
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-022",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-022-A01",
        "atom_order": 1,
        "atom_text": (
            "Se mencionan conocimientos básicos de TI como "
            "requisito previo."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },

    # ----------------------------------------------------------
    # FINAL-V1-023
    # ----------------------------------------------------------
    {
        "final_eval_id": "FINAL-V1-023",
        "review_status": "valid_claim",
        "atomization_class": "atomic",
        "atom_id": "FINAL-V1-023-A01",
        "atom_order": 1,
        "atom_text": (
            "La ruta indica como requisito previo contar con "
            "conocimientos básicos de términos y conceptos de TI."
        ),
        "atom_type": "factual_proposition",
        "review_notes": "",
    },
]


def main() -> None:
    fieldnames = [
        "final_eval_id",
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
        row["final_eval_id"]
        for row in ROWS
    }

    valid_ids = {
        row["final_eval_id"]
        for row in ROWS
        if row["review_status"]
        == "valid_claim"
    }

    non_prop_ids = {
        row["final_eval_id"]
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

    class_by_claim = {
        row["final_eval_id"]:
        row["atomization_class"]
        for row in valid_atoms
    }

    class_counts = Counter(
        class_by_claim.values()
    )

    atom_type_counts = Counter(
        row["atom_type"]
        for row in valid_atoms
    )

    print("=" * 84)
    print(
        "CLAIM ATOMIZATION FINAL EVAL "
        "GROUND TRUTH V1"
    )
    print("=" * 84)

    print(
        "Final-eval items:",
        len(source_ids),
    )

    print(
        "Valid claims:",
        len(valid_ids),
    )

    print(
        "Non-propositional:",
        len(non_prop_ids),
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