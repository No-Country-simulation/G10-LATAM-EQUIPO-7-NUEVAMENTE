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
    / "external_atom_gt_review_batch_08_v1.csv"
)

ATOMS_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_atoms_batch_08_v1.csv"
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
    "EXT-VAL-V1-071": {
        "atom": (
            "No limita el tipo de aplicaciones que soporta.",
            "negation_or_absence",
        ),
        "notes": (
            "Single explicit negation. The omitted contextual subject "
            "is preserved rather than inferred."
        ),
    },

    "EXT-VAL-V1-072": {
        "atom": (
            "Generar una imagen de contenedor al momento de la "
            "compilación permite tener un entorno consistente desde "
            "desarrollo hasta producción.",
            "causal_relation",
        ),
        "notes": (
            "Single enabling/effect relation between build-time "
            "container image generation and environment consistency."
        ),
    },

    "EXT-VAL-V1-073": {
        "atom": (
            "If a string matches both a column name and an index "
            "level name, a ValueError will be raised.",
            "conditional_relation",
        ),
        "notes": (
            "Explicit if-then condition preserved as one atom."
        ),
    },

    "EXT-VAL-V1-074": {
        "atom": (
            "The groupby operation in pandas drops the name field "
            "of the columns Index object after the operation.",
            "temporal_relation",
        ),
        "notes": (
            "The post-operation temporal qualifier is essential "
            "to the proposition."
        ),
    },

    "EXT-VAL-V1-075": {
        "atom": (
            "Using a pipeline helps prevent data leakage, meaning "
            "testing data being disclosed in training data.",
            "causal_relation",
        ),
        "notes": (
            "Single prevention/effect relation. The explanatory "
            "definition of data leakage remains within the same atom."
        ),
    },

    "EXT-VAL-V1-076": {
        "atom": (
            "If you apply a preprocessing step to the whole dataset "
            "without using a pipeline and then perform cross-validation, "
            "you break the fundamental assumption of independence "
            "between training and testing data.",
            "conditional_relation",
        ),
        "notes": (
            "Explicit condition and consequence preserved together. "
            "The no-pipeline qualifier is essential."
        ),
    },

    "EXT-VAL-V1-077": {
        "atom": (
            "Cuando el usuario no ha enviado los datos correctamente, "
            "como desarrollador quieres evitar el envío al servidor "
            "y mostrar un mensaje de error que indique qué está mal "
            "y qué hay que hacer para corregirlo.",
            "conditional_relation",
        ),
        "notes": (
            "Condition-dependent desired behavior preserved as one "
            "relational proposition."
        ),
    },

    "EXT-VAL-V1-078": {
        "atom": (
            "Cuando los usuarios con discapacidad visual usan un "
            "lector de pantalla para leer e interactuar con una página "
            "web, el lector lee en voz alta el texto de la etiqueta "
            "asociada al llegar a cada control.",
            "temporal_relation",
        ),
        "notes": (
            "The when/arrival timing relation is essential and "
            "preserved inside one atom."
        ),
    },

    "EXT-VAL-V1-079": {
        "atom": (
            "El código del lado del servidor genera dinámicamente "
            "contenido nuevo en el servidor, por ejemplo extrayendo "
            "datos de una base de datos, mientras que JavaScript del "
            "lado del cliente genera dinámicamente contenido nuevo "
            "dentro del navegador, por ejemplo creando una tabla HTML, "
            "llenándola con datos solicitados al servidor y mostrándola "
            "en una página web.",
            "comparative_relation",
        ),
        "notes": (
            "Server-side and client-side dynamic content generation "
            "are explicitly contrasted and must remain together. "
            "Extraction spacing is normalized."
        ),
    },

    "EXT-VAL-V1-080": {
        "atom": (
            "Mientras que CSS usa elementos <link> para aplicar hojas "
            "de estilo externas y elementos <style> para aplicar hojas "
            "de estilo internas al HTML, JavaScript necesita el "
            "elemento <script> en HTML.",
            "comparative_relation",
        ),
        "notes": (
            "Explicit comparison between CSS and JavaScript HTML "
            "integration is preserved as one atom. Extraction spacing "
            "is normalized."
        ),
    },
}


EXPECTED_TYPES = {
    "EXT-VAL-V1-071": "negation_or_absence",
    "EXT-VAL-V1-072": "causal_relation",
    "EXT-VAL-V1-073": "conditional_relation",
    "EXT-VAL-V1-074": "temporal_relation",
    "EXT-VAL-V1-075": "causal_relation",
    "EXT-VAL-V1-076": "conditional_relation",
    "EXT-VAL-V1-077": "conditional_relation",
    "EXT-VAL-V1-078": "temporal_relation",
    "EXT-VAL-V1-079": "comparative_relation",
    "EXT-VAL-V1-080": "comparative_relation",
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
        df["target_bucket"] == "relational"
    ).all():
        raise ValueError(
            "All Batch 08 cases must belong to the relational bucket."
        )

    atom_rows = []

    for case_id, decision in DECISIONS.items():
        atom_text, atom_type = decision["atom"]

        if atom_type not in ALLOWED_ATOM_TYPES:
            raise ValueError(
                f"Invalid atom type for {case_id}: {atom_type}"
            )

        if atom_type != EXPECTED_TYPES[case_id]:
            raise ValueError(
                f"{case_id}: expected atom type "
                f"{EXPECTED_TYPES[case_id]}, found {atom_type}."
            )

        mask = (
            df["external_case_id"]
            == case_id
        )

        if int(mask.sum()) != 1:
            raise ValueError(
                f"Expected exactly one row for {case_id}; "
                f"found {int(mask.sum())}."
            )

        structural_subtype = str(
            df.loc[
                mask,
                "relation_subtype",
            ].iloc[0]
        ).strip()

        if structural_subtype != atom_type:
            raise ValueError(
                f"{case_id}: structural subtype "
                f"{structural_subtype!r} does not match "
                f"GT atom type {atom_type!r}."
            )

        if not atom_text.strip():
            raise ValueError(
                f"Empty atom text for {case_id}."
            )

        atom_rows.append(
            {
                "external_case_id": case_id,
                "atom_index": 1,
                "atom_text": atom_text,
                "atom_type": atom_type,
                "gt_review_status": "reviewed",
            }
        )

        df.loc[
            mask,
            "expected_atom_count",
        ] = 1

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
            "Some Batch 08 cases remain unreviewed."
        )

    counts = pd.to_numeric(
        df["expected_atom_count"],
        errors="coerce",
    )

    if counts.isna().any():
        raise ValueError(
            "Invalid expected_atom_count values found."
        )

    if (counts != 1).any():
        raise ValueError(
            "All Batch 08 relational cases must have "
            "expected_atom_count = 1."
        )

    atoms_df = pd.DataFrame(atom_rows)

    if len(atoms_df) != 10:
        raise ValueError(
            f"Expected 10 atom rows; found {len(atoms_df)}."
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
        "External Atom Ground Truth Batch 08 v1"
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
    print(
        df[
            [
                "external_case_id",
                "target_bucket",
                "relation_subtype",
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
        "Relational qualifiers were preserved inside "
        "their propositions."
    )
    print(
        "No Claim Atomizer v0.4 predictions were used."
    )


if __name__ == "__main__":
    main()