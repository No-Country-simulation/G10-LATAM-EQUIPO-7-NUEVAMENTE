"""Run frozen Claim Atomizer v0.4 on untouched final_eval_v1.

Methodological rules:
- v0.4 is already frozen in Git.
- final_eval_v1 is already frozen in Git.
- this script does not inspect or alter ground truth.
- claim texts and atom contents are not printed to console.
- predictions are persisted for later blind human annotation.
"""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

from data_ai.evaluation.gemini_claim_atomizer_v0_4 import (
    GeminiClaimAtomizerV04,
)


BASE_DIR = Path(
    "data/evaluation/atomization_v1/final_eval_v1"
)

INPUT_FILE = (
    BASE_DIR
    / "atomization_final_eval_dataset_v1.csv"
)

RESULTS_DIR = (
    BASE_DIR
    / "results"
)

OUTPUT_FILE = (
    RESULTS_DIR
    / "atomization_final_eval_predictions_v0_4.csv"
)


FIELDNAMES = [
    "final_eval_id",
    "calibration_id",
    "source_claim_id",
    "format",
    "source_claim_text",
    "predicted_review_status",
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

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


def main() -> None:
    api_key = os.getenv(
        "DATA_IA_GEMINI_API_KEY",
        "",
    ).strip()

    model = os.getenv(
        "DATA_IA_GEMINI_MODEL",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "DATA_IA_GEMINI_API_KEY is not configured."
        )

    if not model:
        raise RuntimeError(
            "DATA_IA_GEMINI_MODEL is not configured."
        )

    provider = GeminiClaimAtomizerV04(
        api_key=api_key,
        model=model,
    )

    source_rows = load_csv(
        INPUT_FILE
    )

    if len(source_rows) != 23:
        raise RuntimeError(
            "Expected 23 final-eval items, "
            f"found {len(source_rows)}."
        )

    output_rows: list[
        dict[str, str | int]
    ] = []

    print("=" * 84)
    print(
        "CLAIM ATOMIZATION FINAL EVAL V1 "
        "— v0.4 FROZEN CANDIDATE"
    )
    print("=" * 84)

    print(
        "Source items:",
        len(source_rows),
    )

    print(
        "Model:",
        model,
    )

    print(
        "Prompt version:",
        provider.prompt_version,
    )

    print()
    print(
        "Claim texts and atom contents are hidden "
        "from console output."
    )

    for index, row in enumerate(
        source_rows,
        start=1,
    ):
        print()
        print("-" * 84)

        print(
            f"[{index}/{len(source_rows)}] "
            f"{row['final_eval_id']}"
        )

        started_at = (
            time.perf_counter()
        )

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
                "STATUS: success"
            )

            print(
                "REVIEW STATUS:",
                result.review_status,
            )

            print(
                "CLASS:",
                result.atomization_class,
            )

            print(
                "ATOM COUNT:",
                len(result.atoms),
            )

            if not result.atoms:
                output_rows.append(
                    {
                        "final_eval_id": (
                            row[
                                "final_eval_id"
                            ]
                        ),
                        "calibration_id": (
                            row[
                                "calibration_id"
                            ]
                        ),
                        "source_claim_id": (
                            row[
                                "source_claim_id"
                            ]
                        ),
                        "format": (
                            row["format"]
                        ),
                        "source_claim_text": (
                            row[
                                "source_claim_text"
                            ]
                        ),
                        "predicted_review_status": (
                            result.review_status
                        ),
                        "predicted_class": (
                            result.atomization_class
                            or ""
                        ),
                        "predicted_atom_count": 0,
                        "predicted_atom_order": 0,
                        "predicted_atom_text": "",
                        "predicted_atom_type": "",
                        "model": (
                            result.model
                        ),
                        "prompt_version": (
                            result.prompt_version
                        ),
                        "latency_ms": (
                            latency_ms
                        ),
                        "status": "success",
                        "error_message": "",
                    }
                )

            else:
                for (
                    atom_order,
                    atom,
                ) in enumerate(
                    result.atoms,
                    start=1,
                ):
                    output_rows.append(
                        {
                            "final_eval_id": (
                                row[
                                    "final_eval_id"
                                ]
                            ),
                            "calibration_id": (
                                row[
                                    "calibration_id"
                                ]
                            ),
                            "source_claim_id": (
                                row[
                                    "source_claim_id"
                                ]
                            ),
                            "format": (
                                row["format"]
                            ),
                            "source_claim_text": (
                                row[
                                    "source_claim_text"
                                ]
                            ),
                            "predicted_review_status": (
                                result.review_status
                            ),
                            "predicted_class": (
                                result.atomization_class
                                or ""
                            ),
                            "predicted_atom_count": (
                                len(
                                    result.atoms
                                )
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
                            "model": (
                                result.model
                            ),
                            "prompt_version": (
                                result.prompt_version
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
                "STATUS: failed"
            )

            print(
                "ERROR:",
                str(exc),
            )

            output_rows.append(
                {
                    "final_eval_id": (
                        row[
                            "final_eval_id"
                        ]
                    ),
                    "calibration_id": (
                        row[
                            "calibration_id"
                        ]
                    ),
                    "source_claim_id": (
                        row[
                            "source_claim_id"
                        ]
                    ),
                    "format": (
                        row["format"]
                    ),
                    "source_claim_text": (
                        row[
                            "source_claim_text"
                        ]
                    ),
                    "predicted_review_status": "",
                    "predicted_class": "",
                    "predicted_atom_count": 0,
                    "predicted_atom_order": 0,
                    "predicted_atom_text": "",
                    "predicted_atom_type": "",
                    "model": (
                        provider.model
                    ),
                    "prompt_version": (
                        provider.prompt_version
                    ),
                    "latency_ms": (
                        latency_ms
                    ),
                    "status": "failed",
                    "error_message": (
                        str(exc)
                    ),
                }
            )

        write_rows(
            output_rows
        )

        if index < len(
            source_rows
        ):
            time.sleep(1)

    successful_ids = {
        row["final_eval_id"]
        for row in output_rows
        if row["status"]
        == "success"
    }

    failed_ids = {
        row["final_eval_id"]
        for row in output_rows
        if row["status"]
        == "failed"
    }

    print()
    print("=" * 84)
    print("SUMMARY")
    print("=" * 84)

    print(
        "Successful final-eval items:",
        len(successful_ids),
    )

    print(
        "Failed final-eval items:",
        len(failed_ids),
    )

    if failed_ids:
        print(
            "Failed IDs:",
            ", ".join(
                sorted(
                    failed_ids
                )
            ),
        )

    print()

    print(
        "Output:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()