"""Genera paquete para analizar atomicidad de claims unsupported.

Este script NO modifica producción ni ground truth.

Objetivo:
- seleccionar todos los claims con human_support_label == unsupported;
- recuperar chunks_used;
- recuperar, cuando exista, el resultado semántico experimental;
- mostrar legacy routing;
- preparar una revisión humana de atomicidad.

La finalidad es detectar claims compuestos que contienen:
- un núcleo factual soportado;
- más una subafirmación, relación, condición o calificador no soportado.

NO:
- cambia etiquetas;
- llama a Gemini;
- modifica /evaluate/v2;
- propone todavía lógica productiva.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

CASES_DIR = Path(
    "data/evaluation/calibration_v1/cases"
)

GROUND_TRUTH = (
    RESULTS_DIR
    / "content_support_claim_ground_truth_v1.csv"
)

SEMANTIC_REVIEW = (
    RESULTS_DIR
    / "content_support_semantic_review_results_v1.csv"
)

SEMANTIC_AUTOACCEPTED = (
    RESULTS_DIR
    / "content_support_semantic_autoaccepted_results_v1.csv"
)

OUTPUT_MD = (
    RESULTS_DIR
    / "content_support_unsupported_atomization_review_v1.md"
)


def load_csv(
    path: Path,
) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def make_key(
    row: dict[str, str],
) -> tuple[str, str]:
    return (
        row["calibration_id"],
        row["claim_id"],
    )


def load_case(
    calibration_id: str,
) -> dict:
    path = (
        CASES_DIR
        / f"{calibration_id}.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Case not found: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main() -> None:
    gt_rows = load_csv(
        GROUND_TRUTH
    )

    semantic_rows = (
        load_csv(SEMANTIC_REVIEW)
        + load_csv(SEMANTIC_AUTOACCEPTED)
    )

    semantic_by_key = {
        make_key(row): row
        for row in semantic_rows
        if (
            row.get(
                "semantic_status",
                ""
            )
            == "success"
        )
    }

    unsupported_rows = [
        row
        for row in gt_rows
        if (
            row[
                "human_support_label"
            ]
            .strip()
            .lower()
            == "unsupported"
        )
    ]

    unsupported_rows.sort(
        key=lambda row: (
            row["calibration_id"],
            row["claim_id"],
        )
    )

    lines: list[str] = []

    lines.append(
        "# Content Support — Unsupported Atomization Review v1"
    )
    lines.append("")

    lines.append(
        "## Objetivo"
    )
    lines.append("")

    lines.append(
        "Analizar los claims humanos `unsupported` para determinar "
        "si el fallo de soporte pertenece al claim completo o a una "
        "subafirmación específica."
    )
    lines.append("")

    lines.append(
        "`chunks_used` es la única evidencia factual válida."
    )
    lines.append("")

    lines.append(
        "No se modifica el ground truth en esta etapa."
    )
    lines.append("")

    lines.append(
        "## Categorías de atomicidad"
    )
    lines.append("")

    lines.append(
        "- `atomic_unsupported`: una sola afirmación factual "
        "y esa afirmación no está respaldada."
    )

    lines.append(
        "- `mixed_compound`: combina contenido respaldado y "
        "una subafirmación no respaldada."
    )

    lines.append(
        "- `relation_unsupported`: los hechos base están "
        "respaldados, pero una relación temporal, causal, "
        "comparativa, condicional o lógica no lo está."
    )

    lines.append(
        "- `unclear_segmentation`: no puede dividirse de forma "
        "fiable sin alterar el significado."
    )

    lines.append("")
    lines.append("---")
    lines.append("")

    for index, row in enumerate(
        unsupported_rows,
        start=1,
    ):
        calibration_id = (
            row["calibration_id"]
        )

        claim_id = (
            row["claim_id"]
        )

        case_data = load_case(
            calibration_id
        )

        chunks_used = (
            case_data[
                "evaluation_request"
            ][
                "chunks_used"
            ]
        )

        semantic = semantic_by_key.get(
            make_key(row)
        )

        lines.append(
            f"## {index}. "
            f"{calibration_id} — "
            f"`{claim_id}`"
        )
        lines.append("")

        lines.append(
            f"**Formato:** `{row['format']}`"
        )
        lines.append("")

        lines.append(
            f"**Legacy ratio:** "
            f"`{row['legacy_ratio']}`"
        )

        lines.append(
            f"**Legacy needs review:** "
            f"`{row['legacy_needs_review']}`"
        )

        lines.append("")

        lines.append(
            "### Claim original"
        )
        lines.append("")
        lines.append(
            row["claim_text"]
        )
        lines.append("")

        lines.append(
            "### Ground truth humano"
        )
        lines.append("")
        lines.append(
            "`unsupported`"
        )
        lines.append("")

        lines.append(
            "**Human notes:**"
        )
        lines.append("")
        lines.append(
            row["human_notes"]
        )
        lines.append("")

        lines.append(
            "### Resultado semántico"
        )
        lines.append("")

        if semantic is None:
            lines.append(
                "No disponible."
            )

        else:
            lines.append(
                f"**semantic_supported:** "
                f"`{semantic['semantic_supported']}`"
            )
            lines.append("")

            lines.append(
                "**semantic_reason:**"
            )
            lines.append("")
            lines.append(
                semantic[
                    "semantic_reason"
                ]
            )

        lines.append("")

        lines.append(
            "### Evidencia — chunks_used"
        )
        lines.append("")

        for chunk in chunks_used:
            chunk_id = (
                chunk.get(
                    "chunk_id",
                    "unknown",
                )
            )

            lines.append(
                f"#### `{chunk_id}`"
            )
            lines.append("")
            lines.append("```text")
            lines.append(
                chunk.get(
                    "text",
                    ""
                )
            )
            lines.append("```")
            lines.append("")

        lines.append(
            "### Revisión de atomicidad"
        )
        lines.append("")

        lines.append(
            "**atomization_type:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**atomic_claim_1:** PENDING"
        )
        lines.append("")

        lines.append(
            "**atomic_claim_1_support:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**atomic_claim_2:** PENDING"
        )
        lines.append("")

        lines.append(
            "**atomic_claim_2_support:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**atomic_claim_3:** PENDING"
        )
        lines.append("")

        lines.append(
            "**atomic_claim_3_support:** `PENDING`"
        )
        lines.append("")

        lines.append(
            "**analysis_notes:** PENDING"
        )
        lines.append("")

        lines.append("---")
        lines.append("")

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    legacy_reviewed = sum(
        (
            row[
                "legacy_needs_review"
            ]
            .strip()
            .lower()
            == "true"
        )
        for row in unsupported_rows
    )

    legacy_missed = (
        len(unsupported_rows)
        - legacy_reviewed
    )

    semantic_available = sum(
        make_key(row)
        in semantic_by_key
        for row in unsupported_rows
    )

    print("=" * 74)
    print(
        "CONTENT SUPPORT UNSUPPORTED "
        "ATOMIZATION REVIEW V1"
    )
    print("=" * 74)

    print(
        "Unsupported claims:",
        len(unsupported_rows),
    )

    print(
        "Legacy routed to review:",
        legacy_reviewed,
    )

    print(
        "Legacy missed:",
        legacy_missed,
    )

    print(
        "Semantic results available:",
        semantic_available,
    )

    print()
    print(
        "Output:",
        OUTPUT_MD,
    )

    print()
    print(
        "No labels or production code were modified."
    )


if __name__ == "__main__":
    main()