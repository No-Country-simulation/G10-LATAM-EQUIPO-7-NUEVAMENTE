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
    / "external_atom_gt_review_batch_07_v1.csv"
)

ATOMS_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_atoms_batch_07_v1.csv"
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
    "EXT-VAL-V1-061": {
        "atom": (
            "Llama a varias funciones a la vez cuando sean "
            "independientes.",
            "conditional_relation",
        ),
        "notes": (
            "Single conditional relation. The independence condition "
            "is essential to the instruction and must remain inside "
            "the same atom."
        ),
    },

    "EXT-VAL-V1-062": {
        "atom": (
            "No es necesario que el modelo genere texto antes de "
            "las llamadas a herramientas.",
            "negation_or_absence",
        ),
        "notes": (
            "Single negated necessity proposition. The temporal phrase "
            "'antes de' is retained but the primary relation is the "
            "explicit negation already assigned during structural review."
        ),
    },

    "EXT-VAL-V1-063": {
        "atom": (
            "En este ejemplo, el uso de anyOf para esquemas "
            "condicionales y enum para la clasificación permite que "
            "la estructura de salida varíe según el contenido.",
            "causal_relation",
        ),
        "notes": (
            "Single causal/capability relation. The enabling mechanism "
            "and its effect are kept together rather than separated "
            "into disconnected factual atoms."
        ),
    },

    "EXT-VAL-V1-064": {
        "atom": (
            "Los esquemas muy grandes o con un nivel de anidamiento "
            "profundo pueden ser rechazados.",
            "conditional_relation",
        ),
        "notes": (
            "Single condition-dependent possibility. Size/depth "
            "qualifiers are preserved."
        ),
    },

    "EXT-VAL-V1-065": {
        "atom": (
            "Si no has iniciado sesión, se abrirá tu navegador para "
            "completar el proceso de autenticación.",
            "conditional_relation",
        ),
        "notes": (
            "Explicit if-then relation preserved as one atom."
        ),
    },

    "EXT-VAL-V1-066": {
        "atom": (
            "No puedes redefinir una path operation.",
            "negation_or_absence",
        ),
        "notes": (
            "Single explicit inability/negation proposition. "
            "Discourse marker is omitted."
        ),
    },

    "EXT-VAL-V1-067": {
        "atom": (
            "Fue rigurosamente probado en la fase de diseño, antes "
            "de cualquier implementación, para garantizar que "
            "funcionaría con todos los editores.",
            "temporal_relation",
        ),
        "notes": (
            "The temporal ordering 'before any implementation' is "
            "essential and is preserved. The purpose clause remains "
            "inside the same proposition rather than being split "
            "artificially."
        ),
    },

    "EXT-VAL-V1-068": {
        "atom": (
            "Si usas PyCharm como tu editor, puedes usar el "
            "Pydantic PyCharm Plugin.",
            "conditional_relation",
        ),
        "notes": (
            "Explicit condition and consequence preserved as one atom."
        ),
    },

    "EXT-VAL-V1-069": {
        "atom": (
            "When you create an object in Kubernetes, you must provide "
            "the object spec that describes its desired state, as well "
            "as some basic information about the object, such as a name.",
            "conditional_relation",
        ),
        "notes": (
            "Single conditional requirement. The two required pieces "
            "of information remain coordinated inside the same "
            "condition-dependent proposition."
        ),
    },

    "EXT-VAL-V1-070": {
        "atom": (
            "Starting with Kubernetes v1.25, the API server offers "
            "server-side field validation that detects unrecognized "
            "or duplicate fields in an object.",
            "temporal_relation",
        ),
        "notes": (
            "Version-based temporal boundary is essential to the "
            "proposition. Extraction spacing is normalized."
        ),
    },
}


EXPECTED_TYPES = {
    "EXT-VAL-V1-061": "conditional_relation",
    "EXT-VAL-V1-062": "negation_or_absence",
    "EXT-VAL-V1-063": "causal_relation",
    "EXT-VAL-V1-064": "conditional_relation",
    "EXT-VAL-V1-065": "conditional_relation",
    "EXT-VAL-V1-066": "negation_or_absence",
    "EXT-VAL-V1-067": "temporal_relation",
    "EXT-VAL-V1-068": "conditional_relation",
    "EXT-VAL-V1-069": "conditional_relation",
    "EXT-VAL-V1-070": "temporal_relation",
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
            "All Batch 07 cases must belong to the relational bucket."
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
            "Some Batch 07 cases remain unreviewed."
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
            "All Batch 07 relational cases must have "
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
        "External Atom Ground Truth Batch 07 v1"
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