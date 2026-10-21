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
    / "external_atom_gt_review_batch_03_v1.csv"
)

ATOMS_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_atoms_batch_03_v1.csv"
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
    "EXT-VAL-V1-021": {
        "atoms": [
            (
                "En este ejemplo, se muestra cómo definir una función "
                "que genera un gráfico de barras a partir de datos "
                "estructurados.",
                "factual_proposition",
            ),
            (
                "El modelo puede usar herramientas externas para "
                "realizar cálculos o crear recursos visuales.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Two independently meaningful propositions: the example "
            "shows a bar-chart-generating function, and it demonstrates "
            "the model's ability to use external tools."
        ),
    },

    "EXT-VAL-V1-022": {
        "atoms": [
            (
                "El bloque de texto de salida contiene una cadena "
                "JSON válida.",
                "factual_proposition",
            ),
            (
                "La cadena JSON del bloque de salida se ajusta "
                "exactamente al esquema solicitado.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "JSON validity and exact schema conformance are separate "
            "independently checkable properties."
        ),
    },

    "EXT-VAL-V1-023": {
        "atoms": [
            (
                "Las restricciones minLength y maxLength no se aplican "
                "durante la decodificación restringida.",
                "negation_or_absence",
            ),
            (
                "El servidor ignora las restricciones minLength "
                "y maxLength.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Two independently checkable claims. The obvious extraction "
            "spacing error in 'noadmitidas' is not propagated to atom text."
        ),
    },

    "EXT-VAL-V1-024": {
        "atoms": [
            (
                "Enviar un body con un request GET tiene un comportamiento "
                "indefinido en las especificaciones.",
                "factual_proposition",
            ),
            (
                "FastAPI soporta enviar un body con un request GET solo "
                "para casos de uso muy complejos o extremos.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Specification behavior and FastAPI support are separate "
            "propositions. Obvious extraction spacing error is normalized."
        ),
    },

    "EXT-VAL-V1-025": {
        "atoms": [
            (
                "FastAPI reconocerá cada uno de ellos.",
                "factual_proposition",
            ),
            (
                "FastAPI tomará los datos del lugar correcto.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Two coordinated propositions. The contextual referent "
            "'ellos' is preserved rather than inferred."
        ),
    },

    "EXT-VAL-V1-026": {
        "atoms": [
            (
                "El Master de Kubernetes es un conjunto de tres daemons.",
                "factual_proposition",
            ),
            (
                "Los tres daemons del Master de Kubernetes se ejecutan "
                "en un único nodo del clúster.",
                "factual_proposition",
            ),
            (
                "Ese nodo se denomina nodo master.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Definition, execution location, and node naming are three "
            "independently checkable propositions."
        ),
    },

    "EXT-VAL-V1-027": {
        "atoms": [
            (
                "Los Controladores se basan en los objetos básicos.",
                "factual_proposition",
            ),
            (
                "Los Controladores proporcionan funcionalidades "
                "adicionales sobre los objetos básicos.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Two coordinated independently checkable propositions."
        ),
    },

    "EXT-VAL-V1-028": {
        "atoms": [
            (
                "Las Annotations permiten asignar información arbitraria "
                "a un recurso.",
                "factual_proposition",
            ),
            (
                "Asignar información mediante Annotations puede facilitar "
                "los flujos de trabajo.",
                "causal_relation",
            ),
            (
                "Asignar información mediante Annotations puede hacer más "
                "fácil que las herramientas administrativas inspeccionen "
                "el estado.",
                "causal_relation",
            ),
        ],
        "notes": (
            "One capability proposition plus two explicit purpose/effect "
            "relations from the source claim."
        ),
    },

    "EXT-VAL-V1-029": {
        "atoms": [
            (
                "Son más fáciles de construir que una máquina virtual.",
                "comparative_relation",
            ),
            (
                "No están acoplados a la infraestructura ni al sistema "
                "de archivos del anfitrión.",
                "negation_or_absence",
            ),
            (
                "Debido a que no están acoplados a la infraestructura "
                "ni al sistema de archivos del anfitrión, pueden llevarse "
                "entre nubes y distribuciones de sistema operativo.",
                "causal_relation",
            ),
        ],
        "notes": (
            "Comparison, absence of coupling, and explicit causal relation "
            "are preserved as separate atoms. The omitted subject is not "
            "inferred."
        ),
    },

    "EXT-VAL-V1-030": {
        "atoms": [
            (
                "Passing a list of column labels selects multiple columns.",
                "factual_proposition",
            ),
            (
                "Selecting multiple columns can be useful for getting "
                "a subset or rearranging columns.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Selection behavior and stated utility are treated as two "
            "independently meaningful propositions."
        ),
    },
}


EXPECTED_COUNTS = {
    "EXT-VAL-V1-021": 2,
    "EXT-VAL-V1-022": 2,
    "EXT-VAL-V1-023": 2,
    "EXT-VAL-V1-024": 2,
    "EXT-VAL-V1-025": 2,
    "EXT-VAL-V1-026": 3,
    "EXT-VAL-V1-027": 2,
    "EXT-VAL-V1-028": 3,
    "EXT-VAL-V1-029": 3,
    "EXT-VAL-V1-030": 2,
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
            "All Batch 03 cases must belong to the compound bucket."
        )

    atom_rows = []

    for case_id, decision in DECISIONS.items():
        atoms = decision["atoms"]

        expected_count = EXPECTED_COUNTS[case_id]

        if len(atoms) != expected_count:
            raise ValueError(
                f"{case_id}: expected {expected_count} atoms, "
                f"but decision contains {len(atoms)}."
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
            "Some Batch 03 cases remain unreviewed."
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

    if len(atoms_df) != 23:
        raise ValueError(
            f"Expected 23 total atom rows; found {len(atoms_df)}."
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
        "External Atom Ground Truth Batch 03 v1"
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