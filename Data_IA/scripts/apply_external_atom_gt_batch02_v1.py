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
    / "external_atom_gt_review_batch_02_v1.csv"
)

ATOMS_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_atoms_batch_02_v1.csv"
)


DECISIONS = {
    "EXT-VAL-V1-011": {
        "atoms": [
            (
                "El Plano de Control de Kubernetes usa las mismas "
                "APIs que usan los desarrolladores y usuarios "
                "finales.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single proposition. Discourse marker 'Además' "
            "is omitted without changing factual content."
        ),
    },
    "EXT-VAL-V1-012": {
        "atoms": [
            (
                "Kubernetes funciona en Ubuntu, RHEL, CoreOS, "
                "un datacenter físico, Google Kubernetes Engine "
                "y otros entornos.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single portability proposition with examples kept "
            "inside the same atom."
        ),
    },
    "EXT-VAL-V1-013": {
        "atoms": [
            (
                "Operations in general exclude missing data.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single factual proposition."
        ),
    },
    "EXT-VAL-V1-014": {
        "atoms": [
            (
                "The result of an aggregation is, or at least is "
                "treated as, a scalar value for each column in "
                "a group.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single proposition; original qualification "
            "'or at least is treated as' is preserved."
        ),
    },
    "EXT-VAL-V1-015": {
        "atoms": [
            (
                "pandas allows you to provide multiple lambdas.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single capability proposition."
        ),
    },
    "EXT-VAL-V1-016": {
        "atoms": [
            (
                "Scikit-learn provides tools to automatically find "
                "the best parameter combinations via "
                "cross-validation.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single capability proposition; parenthetical "
            "mechanism is preserved."
        ),
    },
    "EXT-VAL-V1-017": {
        "atoms": [
            (
                "Puedes ver el ejemplo completo funcionando "
                "en vivo.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "The factual proposition is retained. The imperative "
            "'pruébalo ahí' is not an independently checkable atom."
        ),
    },
    "EXT-VAL-V1-018": {
        "atoms": [
            (
                "La documentación sobre el evento connect de HTTP "
                "en Node.js ofrece un buen ejemplo.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single descriptive proposition."
        ),
    },
    "EXT-VAL-V1-019": {
        "atoms": [
            (
                "El tipo text muestra un campo de texto básico "
                "que acepta cualquier valor.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single proposition describing the text input type."
        ),
    },
    "EXT-VAL-V1-020": {
        "atoms": [
            (
                "Las API son conjuntos de bloques de código ya "
                "hechos que permiten a un desarrollador implementar "
                "programas que de otro modo serían difíciles o "
                "imposibles de implementar.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single definitional proposition."
        ),
    },
}


ALLOWED_ATOM_TYPES = {
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
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

    atom_rows = []

    for case_id, decision in DECISIONS.items():
        atoms = decision["atoms"]

        if len(atoms) != 1:
            raise ValueError(
                f"{case_id} must have exactly one atom."
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
                    f"Invalid atom type for {case_id}: "
                    f"{atom_type}"
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
            df["external_case_id"]
            == case_id
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
            "Some Batch 02 cases remain unreviewed."
        )

    counts = pd.to_numeric(
        df["expected_atom_count"],
        errors="coerce",
    )

    if (counts != 1).any():
        raise ValueError(
            "All Batch 02 atomic cases must have "
            "expected_atom_count = 1."
        )

    atoms_df = pd.DataFrame(atom_rows)

    if len(atoms_df) != 10:
        raise ValueError(
            f"Expected 10 atom rows; found {len(atoms_df)}."
        )

    if (
        atoms_df["external_case_id"]
        .duplicated()
        .any()
    ):
        raise ValueError(
            "Duplicate atom rows found for an atomic case."
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
        "External Atom Ground Truth Batch 02 v1"
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