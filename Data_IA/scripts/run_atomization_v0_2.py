"""Runs experimental Claim Atomization v0.2 predictions.

Reads the same frozen source claims used by v0.1.

Does NOT:
- read the ground truth;
- read chunks_used;
- evaluate factual support;
- modify production.

Results are stored separately from v0.1 for direct comparison.
"""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

from data_ai.evaluation.gemini_claim_atomizer_v0_2 import (
    GeminiClaimAtomizerV02,
)


ATOMIZATION_DIR = Path(
    "data/evaluation/atomization_v1"
)

RESULTS_DIR = (
    ATOMIZATION_DIR
    / "results"
)

INPUT_DATASET = (
    ATOMIZATION_DIR
    / "atomization_dataset_v1.csv"
)

OUTPUT_PREDICTIONS = (
    RESULTS_DIR
    / "atomization_predictions_v0_2.csv"
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


def write_rows(
    rows: list[dict[str, str | int]],
) -> None:
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "dataset_id",
        "calibration_id",
        "source_claim_id",
        "format",
        "source_claim_text",
        "predicted_class",
        "predicted_atom_count",
        "predicted_atom_order",
        "predicted_atom_text",
        "predicted_atom_type",
        "model",
        "prompt_version",
        "latency_ms",
        "status",
        "error_message",
    ]

    with OUTPUT_PREDICTIONS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    api_key = (
        os.getenv(
            "DATA_IA_GEMINI_API_KEY",
            "",
        )
        .strip()
    )

    model = (
        os.getenv(
            "DATA_IA_GEMINI_MODEL",
            "",
        )
        .strip()
    )

    if not api_key:
        raise RuntimeError(
            "DATA_IA_GEMINI_API_KEY is not configured."
        )

    if not model:
        raise RuntimeError(
            "DATA_IA_GEMINI_MODEL is not configured."
        )

    provider = GeminiClaimAtomizerV02(
        api_key=api_key,
        model=model,
    )

    source_rows = load_csv(
        INPUT_DATASET
    )

    output_rows: list[
        dict[str, str | int]
    ] = []

    print("=" * 76)
    print(
        "CLAIM ATOMIZATION v0.2 — "
        "GEMINI PREDICTIONS"
    )
    print("=" * 76)

    print(
        "Source claims:",
        len(source_rows),
    )

    print(
        "Model:",
        model,
    )

    for index, row in enumerate(
        source_rows,
        start=1,
    ):
        print()
        print("-" * 76)

        print(
            f"[{index}/{len(source_rows)}] "
            f"{row['dataset_id']} "
            f"{row['source_claim_id']}"
        )

        started_at = time.perf_counter()

        try:
            result = provider.atomize(
                source_claim_id=(
                    row[
                        "source_claim_id"
                    ]
                ),
                claim_text=(
                    row[
                        "source_claim_text"
                    ]
                ),
                format=row["format"],
            )

            latency_ms = int(
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            print(
                "CLASS:",
                result.atomization_class,
            )

            print(
                "ATOMS:",
                len(result.atoms),
            )

            for atom_order, atom in enumerate(
                result.atoms,
                start=1,
            ):
                print(
                    f"  {atom_order}. "
                    f"[{atom.atom_type}] "
                    f"{atom.text}"
                )

                output_rows.append(
                    {
                        "dataset_id": (
                            row["dataset_id"]
                        ),
                        "calibration_id": (
                            row["calibration_id"]
                        ),
                        "source_claim_id": (
                            row["source_claim_id"]
                        ),
                        "format": row["format"],
                        "source_claim_text": (
                            row[
                                "source_claim_text"
                            ]
                        ),
                        "predicted_class": (
                            result.atomization_class
                        ),
                        "predicted_atom_count": (
                            len(result.atoms)
                        ),
                        "predicted_atom_order": (
                            atom_order
                        ),
                        "predicted_atom_text": (
                            atom.text
                        ),
                        "predicted_atom_type": (
                            atom.atom_type
                        ),
                        "model": provider.model,
                        "prompt_version": (
                            provider.prompt_version
                        ),
                        "latency_ms": (
                            latency_ms
                        ),
                        "status": "success",
                        "error_message": "",
                    }
                )

        except Exception as exc:
            latency_ms = int(
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            print(
                "FAILED:",
                str(exc),
            )

            output_rows.append(
                {
                    "dataset_id": (
                        row["dataset_id"]
                    ),
                    "calibration_id": (
                        row["calibration_id"]
                    ),
                    "source_claim_id": (
                        row["source_claim_id"]
                    ),
                    "format": row["format"],
                    "source_claim_text": (
                        row[
                            "source_claim_text"
                        ]
                    ),
                    "predicted_class": "",
                    "predicted_atom_count": 0,
                    "predicted_atom_order": 0,
                    "predicted_atom_text": "",
                    "predicted_atom_type": "",
                    "model": provider.model,
                    "prompt_version": (
                        provider.prompt_version
                    ),
                    "latency_ms": (
                        latency_ms
                    ),
                    "status": "failed",
                    "error_message": str(
                        exc
                    ),
                }
            )

        write_rows(
            output_rows
        )

    success_source_ids = {
        row["dataset_id"]
        for row in output_rows
        if row["status"]
        == "success"
    }

    failed_source_ids = {
        row["dataset_id"]
        for row in output_rows
        if row["status"]
        == "failed"
    }

    print()
    print("=" * 76)
    print("SUMMARY")
    print("=" * 76)

    print(
        "Successful source claims:",
        len(success_source_ids),
    )

    print(
        "Failed source claims:",
        len(failed_source_ids),
    )

    print()

    print(
        "Output:",
        OUTPUT_PREDICTIONS,
    )


if __name__ == "__main__":
    main()