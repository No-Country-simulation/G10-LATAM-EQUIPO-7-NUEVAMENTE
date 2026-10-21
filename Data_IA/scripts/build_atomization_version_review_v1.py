"""Build side-by-side semantic review for Claim Atomizer v0.2 and v0.3."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_v1"
)

RESULTS_DIR = BASE_DIR / "results"

DATASET_FILE = (
    BASE_DIR / "atomization_dataset_v1.csv"
)

GT_FILE = (
    BASE_DIR / "atomization_ground_truth_v1.csv"
)

V02_FILE = (
    RESULTS_DIR
    / "atomization_predictions_v0_2.csv"
)

V03_FILE = (
    RESULTS_DIR
    / "atomization_predictions_v0_3.csv"
)

OUTPUT_FILE = (
    RESULTS_DIR
    / "atomization_v0_2_vs_v0_3_review.md"
)


def load_csv(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def group_rows(
    rows: list[dict[str, str]],
    *,
    order_field: str,
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in rows:
        if (
            "status" in row
            and row["status"] != "success"
        ):
            continue

        grouped[
            row["dataset_id"]
        ].append(row)

    for dataset_id in grouped:
        grouped[dataset_id].sort(
            key=lambda row: int(
                row[order_field]
            )
        )

    return grouped


def render_prediction(
    rows: list[dict[str, str]],
) -> list[str]:
    if not rows:
        return [
            "_No prediction._"
        ]

    lines = [
        (
            f"**Class:** "
            f"`{rows[0]['predicted_class']}`"
        ),
        "",
    ]

    for row in rows:
        lines.append(
            f"{row['predicted_atom_order']}. "
            f"`[{row['predicted_atom_type']}]` "
            f"{row['predicted_atom_text']}"
        )

    return lines


def main() -> None:
    dataset = {
        row["dataset_id"]: row
        for row in load_csv(
            DATASET_FILE
        )
    }

    gt = group_rows(
        load_csv(GT_FILE),
        order_field="atom_order",
    )

    v02 = group_rows(
        load_csv(V02_FILE),
        order_field=(
            "predicted_atom_order"
        ),
    )

    v03 = group_rows(
        load_csv(V03_FILE),
        order_field=(
            "predicted_atom_order"
        ),
    )

    lines: list[str] = [
        "# Claim Atomization — v0.2 vs v0.3 Review",
        "",
        "## Objetivo",
        "",
        (
            "Comparar manualmente v0.2 y v0.3 contra el "
            "ground truth congelado, priorizando preservación "
            "semántica además de estructura."
        ),
        "",
        "### Etiquetas sugeridas",
        "",
        "- `v0.2`",
        "- `v0.3`",
        "- `tie`",
        "- `neither`",
        "",
        "---",
        "",
    ]

    for dataset_id in sorted(dataset):
        source = dataset[
            dataset_id
        ]

        lines.extend(
            [
                f"## {dataset_id}",
                "",
                "### Source claim",
                "",
                source[
                    "source_claim_text"
                ],
                "",
                "### Frozen GT",
                "",
            ]
        )

        for row in gt[
            dataset_id
        ]:
            lines.append(
                f"{row['atom_order']}. "
                f"`[{row['atom_type']}]` "
                f"{row['atom_text']}"
            )

        lines.extend(
            [
                "",
                "### v0.2",
                "",
            ]
        )

        lines.extend(
            render_prediction(
                v02.get(
                    dataset_id,
                    [],
                )
            )
        )

        lines.extend(
            [
                "",
                "### v0.3",
                "",
            ]
        )

        lines.extend(
            render_prediction(
                v03.get(
                    dataset_id,
                    [],
                )
            )
        )

        lines.extend(
            [
                "",
                "### Manual comparison",
                "",
                "**preferred_version:** `PENDING`",
                "",
                "**meaning_preservation:** `PENDING`",
                "",
                "**qualifier_preservation:** `PENDING`",
                "",
                "**relation_isolation:** `PENDING`",
                "",
                "**independent_evaluability:** `PENDING`",
                "",
                "**redundancy:** `PENDING`",
                "",
                "**review_notes:** PENDING",
                "",
                "---",
                "",
            ]
        )

    OUTPUT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=" * 76)
    print(
        "CLAIM ATOMIZATION "
        "v0.2 vs v0.3 REVIEW"
    )
    print("=" * 76)

    print(
        "Source claims:",
        len(dataset),
    )

    print()

    print(
        "Output:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()