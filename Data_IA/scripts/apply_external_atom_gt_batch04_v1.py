from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

BATCH_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_review_batch_04_v1.csv"
)

ATOMS_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_atoms_batch_04_v1.csv"
)


ALLOWED_ATOM_TYPES = {
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
}


DECISIONS = {
    "EXT-VAL-V1-031": {
        "atoms": [
            (
                "You can use the group_keys argument to control "
                "whether the grouped column or columns are included "
                "in the indices.",
                "factual_proposition",
            ),
            (
                "The group_keys argument defaults to True.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Control behavior and default value are independently "
            "checkable propositions. Extraction spacing is normalized."
        ),
    },

    "EXT-VAL-V1-032": {
        "atoms": [
            (
                "Transformer objects do not have a predict method.",
                "negation_or_absence",
            ),
            (
                "Transformer objects have a transform method that "
                "outputs a newly transformed sample matrix X.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Absence of predict and presence/behavior of transform "
            "are separate propositions."
        ),
    },

    "EXT-VAL-V1-033": {
        "atoms": [
            (
                "The train_test_split helper splits a dataset into "
                "train and test sets.",
                "factual_proposition",
            ),
            (
                "Scikit-learn provides other tools for model "
                "evaluation, particularly for cross-validation.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Two independently checkable statements. Extraction "
            "spacing in 'datasetinto' is normalized."
        ),
    },

    "EXT-VAL-V1-034": {
        "atoms": [
            (
                "El ejemplo implementa una comprobación básica dentro "
                "de un manejador del evento submit para comprobar si "
                "los campos de texto están vacíos.",
                "factual_proposition",
            ),
            (
                "El evento submit se lanza en un formulario cuando "
                "el formulario se envía.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Implementation behavior and the parenthetical definition "
            "of the submit event are separate propositions."
        ),
    },

    "EXT-VAL-V1-035": {
        "atoms": [
            (
                "El modelo de eventos de Node.js se basa en detectores "
                "que escuchan eventos y emisores que los emiten.",
                "factual_proposition",
            ),
            (
                "El código de este modelo es bastante diferente del "
                "modelo de eventos descrito previamente.",
                "comparative_relation",
            ),
            (
                "La función on() se usa para registrar un detector "
                "de eventos.",
                "factual_proposition",
            ),
            (
                "La función once() registra un detector que se elimina "
                "después de ejecutarse una vez.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "The claim contains a model description, an explicit "
            "comparison with prior context, and two distinct API "
            "behaviors."
        ),
    },

    "EXT-VAL-V1-036": {
        "atoms": [
            (
                "Algunas personas usan elementos <p> para separar "
                "los elementos de sus formularios.",
                "factual_proposition",
            ),
            (
                "Otras personas usan elementos <div>, <section> "
                "o <li> para separar los elementos de sus formularios.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Two contrasted usage patterns are independently "
            "checkable propositions."
        ),
    },

    "EXT-VAL-V1-037": {
        "atoms": [
            (
                "Los botones de opción y las casillas de verificación "
                "se implementan de forma muy parecida.",
                "comparative_relation",
            ),
            (
                "Los botones de opción y las casillas de verificación "
                "admiten el atributo checked para aparecer "
                "preseleccionados al cargar la página.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Implementation similarity is a comparative relation; "
            "checked support is a separate capability proposition. "
            "Extraction spacing is normalized."
        ),
    },

    "EXT-VAL-V1-038": {
        "atoms": [
            (
                "El atributo rows especifica cuántas filas de alto "
                "tendrá el área de texto de forma predeterminada.",
                "factual_proposition",
            ),
            (
                "El atributo cols especifica cuántas columnas de ancho "
                "tendrá el área de texto de forma predeterminada.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "rows and cols describe two independently checkable "
            "attribute behaviors."
        ),
    },

    "EXT-VAL-V1-039": {
        "atoms": [
            (
                "La API del DOM permite crear HTML.",
                "factual_proposition",
            ),
            (
                "La API del DOM permite eliminar HTML.",
                "factual_proposition",
            ),
            (
                "La API del DOM permite cambiar HTML.",
                "factual_proposition",
            ),
            (
                "La API del DOM permite aplicar dinámicamente nuevos "
                "estilos a una página.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "The general manipulation statement is represented by its "
            "explicit independently checkable capabilities rather than "
            "duplicating it as an additional umbrella atom."
        ),
    },

    "EXT-VAL-V1-040": {
        "atoms": [
            (
                "Cada pestaña del navegador tiene su propio entorno "
                "de ejecución separado.",
                "factual_proposition",
            ),
            (
                "Debido a que cada pestaña tiene un entorno de "
                "ejecución separado, en la mayoría de los casos el "
                "código de cada pestaña se ejecuta de forma "
                "completamente independiente.",
                "causal_relation",
            ),
            (
                "El código de una pestaña no puede afectar "
                "directamente al código de otra pestaña ni al código "
                "de otro sitio web.",
                "negation_or_absence",
            ),
        ],
        "notes": (
            "The separate execution environment, its stated consequence, "
            "and the explicit inability to directly affect another "
            "tab/site are preserved. Extraction spacing is normalized."
        ),
    },
}


EXPECTED_COUNTS = {
    "EXT-VAL-V1-031": 2,
    "EXT-VAL-V1-032": 2,
    "EXT-VAL-V1-033": 2,
    "EXT-VAL-V1-034": 2,
    "EXT-VAL-V1-035": 4,
    "EXT-VAL-V1-036": 2,
    "EXT-VAL-V1-037": 2,
    "EXT-VAL-V1-038": 2,
    "EXT-VAL-V1-039": 4,
    "EXT-VAL-V1-040": 3,
}


def main() -> None:
    df = pd.read_csv(
        BATCH_PATH,
        keep_default_na=False,
    )

    expected_ids = set(DECISIONS)
    actual_ids = set(df["external_case_id"])

    if actual_ids != expected_ids:
        raise ValueError(
            "Batch case IDs do not match decisions. "
            f"Missing={sorted(expected_ids - actual_ids)}, "
            f"Unexpected={sorted(actual_ids - expected_ids)}"
        )

    if not (
        df["target_bucket"] == "compound"
    ).all():
        raise ValueError(
            "All Batch 04 cases must belong to the compound bucket."
        )

    atom_rows = []

    for case_id, decision in DECISIONS.items():
        atoms = decision["atoms"]
        expected_count = EXPECTED_COUNTS[case_id]

        if len(atoms) != expected_count:
            raise ValueError(
                f"{case_id}: expected {expected_count} atoms, "
                f"but found {len(atoms)}."
            )

        if len(atoms) < 2:
            raise ValueError(
                f"{case_id}: compound case must contain at least 2 atoms."
            )

        for atom_index, (
            atom_text,
            atom_type,
        ) in enumerate(
            atoms,
            start=1,
        ):
            if atom_type not in ALLOWED_ATOM_TYPES:
                raise ValueError(
                    f"Invalid atom type for {case_id}: {atom_type}"
                )

            if not atom_text.strip():
                raise ValueError(
                    f"Empty atom text for {case_id}."
                )

            atom_rows.append(
                {
                    "external_case_id": case_id,
                    "atom_index": atom_index,
                    "atom_text": atom_text,
                    "atom_type": atom_type,
                    "gt_review_status": "reviewed",
                }
            )

        mask = (
            df["external_case_id"] == case_id
        )

        if int(mask.sum()) != 1:
            raise ValueError(
                f"Expected exactly one row for {case_id}; "
                f"found {int(mask.sum())}."
            )

        df.loc[
            mask,
            "expected_atom_count",
        ] = expected_count

        df.loc[
            mask,
            "gt_review_status",
        ] = "reviewed"

        df.loc[
            mask,
            "gt_notes",
        ] = decision["notes"]

    if (
        df["gt_review_status"]
        != "reviewed"
    ).any():
        raise ValueError(
            "Some Batch 04 cases remain unreviewed."
        )

    counts = pd.to_numeric(
        df["expected_atom_count"],
        errors="coerce",
    )

    if counts.isna().any():
        raise ValueError(
            "Invalid expected_atom_count values found."
        )

    atoms_df = pd.DataFrame(atom_rows)

    grouped_counts = (
        atoms_df.groupby("external_case_id")
        .size()
        .to_dict()
    )

    for case_id, expected_count in EXPECTED_COUNTS.items():
        actual_count = int(
            grouped_counts.get(case_id, 0)
        )

        if actual_count != expected_count:
            raise ValueError(
                f"{case_id}: expected {expected_count} atom rows; "
                f"found {actual_count}."
            )

    if len(atoms_df) != 25:
        raise ValueError(
            f"Expected 25 total atom rows; found {len(atoms_df)}."
        )

    df.to_csv(
        BATCH_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    atoms_df.to_csv(
        ATOMS_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "External Atom Ground Truth Batch 04 v1"
    )
    print(
        "======================================="
    )

    print()
    print(
        "Cases reviewed:",
        len(df),
    )

    print(
        "Expected atoms:",
        int(counts.sum()),
    )

    print(
        "Atom rows:",
        len(atoms_df),
    )

    print()
    print("Atom types:")
    print(
        atoms_df["atom_type"]
        .value_counts()
        .to_string()
    )

    print()
    print("Atoms per case:")
    print(
        atoms_df.groupby(
            "external_case_id"
        )
        .size()
        .to_string()
    )

    print()
    print(
        df[
            [
                "external_case_id",
                "target_bucket",
                "expected_atom_count",
                "gt_review_status",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"Updated batch: {BATCH_PATH}")
    print(f"Atoms: {ATOMS_OUTPUT_PATH}")

    print()
    print("IMPORTANT:")
    print(
        "These are human Ground Truth annotations."
    )
    print(
        "No Claim Atomizer v0.4 predictions were used."
    )


if __name__ == "__main__":
    main()