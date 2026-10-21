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
    / "external_atom_gt_review_batch_01_v1.csv"
)

ATOMS_OUTPUT_PATH = (
    BASE_DIR
    / "ground_truth"
    / "review_batches"
    / "external_atom_gt_atoms_batch_01_v1.csv"
)


DECISIONS = {
    "EXT-VAL-V1-001": {
        "atoms": [
            (
                "El MCP remoto solo funciona con servidores "
                "HTTP transmitibles.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single independently checkable proposition."
        ),
    },
    "EXT-VAL-V1-002": {
        "atoms": [
            (
                "Puedes copiarla desde la página Claves de API.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single proposition. Contextual pronoun is preserved "
            "because its referent is not present in the claim."
        ),
    },
    "EXT-VAL-V1-003": {
        "atoms": [
            (
                "Los resultados estructurados funcionan con "
                "Pydantic (Python) y Zod (JavaScript).",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single compatibility proposition; framework examples "
            "remain part of the same factual statement."
        ),
    },
    "EXT-VAL-V1-004": {
        "atoms": [
            (
                "Puedes configurar los modelos de Gemini para que "
                "generen respuestas que se adhieran a un esquema "
                "JSON proporcionado.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single capability proposition."
        ),
    },
    "EXT-VAL-V1-005": {
        "atoms": [
            (
                "Puedes configurar dónde está tu app en un archivo "
                "pyproject.toml.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Trailing example introducer removed without changing "
            "the factual content."
        ),
    },
    "EXT-VAL-V1-006": {
        "atoms": [
            (
                "Este decorador le dice a FastAPI que la función "
                "de abajo corresponde al path / con una operación "
                "GET.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single proposition. Contextual demonstrative is "
            "preserved because the decorator itself is omitted "
            "from the claim."
        ),
    },
    "EXT-VAL-V1-007": {
        "atoms": [
            (
                "Puedes retornar un dict, list o valores singulares "
                "como str, int, etc.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single proposition describing allowed return value "
            "forms."
        ),
    },
    "EXT-VAL-V1-008": {
        "atoms": [
            (
                "Puedes declarar el tipo de un parámetro de path "
                "en la función usando anotaciones de tipos estándar "
                "de Python.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single capability proposition."
        ),
    },
    "EXT-VAL-V1-009": {
        "atoms": [
            (
                "En Kubernetes, un Deployment es un objeto que "
                "puede representar una aplicación ejecutándose "
                "en el clúster.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single descriptive proposition."
        ),
    },
    "EXT-VAL-V1-010": {
        "atoms": [
            (
                "Esa plantilla describe los Pods que el controlador "
                "StatefulSet creará para satisfacer la especificación "
                "del StatefulSet.",
                "factual_proposition",
            ),
        ],
        "notes": (
            "Single proposition. Contextual demonstrative is "
            "preserved rather than replacing it with an inferred "
            "referent."
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

        if not atoms:
            raise ValueError(
                f"{case_id} is atomic but has no atoms."
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
        ] = len(atoms)

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
            "Some Batch 01 cases remain unreviewed."
        )

    if (
        pd.to_numeric(
            df["expected_atom_count"],
            errors="coerce",
        )
        != 1
    ).any():
        raise ValueError(
            "All Batch 01 atomic cases must have "
            "expected_atom_count = 1."
        )

    atoms_df = pd.DataFrame(atom_rows)

    atom_counts = (
        atoms_df.groupby(
            "external_case_id"
        )
        .size()
    )

    for case_id in expected_ids:
        if int(atom_counts.get(case_id, 0)) != 1:
            raise ValueError(
                f"{case_id} does not have exactly one atom."
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
        "External Atom Ground Truth Batch 01 v1"
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
        int(
            pd.to_numeric(
                df["expected_atom_count"]
            ).sum()
        ),
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