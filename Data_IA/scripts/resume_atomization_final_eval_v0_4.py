"""Resume failed items from frozen v0.4 final evaluation.

This script:
- preserves successful predictions from attempt 1;
- retries ONLY failed final-eval items;
- does not modify v0.4;
- does not modify final_eval_v1;
- logs retry diagnostics separately.
"""

from __future__ import annotations

import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from data_ai.evaluation.gemini_claim_atomizer_v0_4 import (
    GeminiClaimAtomizerV04,
)


BASE_DIR = Path(
    "data/evaluation/atomization_v1/final_eval_v1"
)

DATASET_FILE = (
    BASE_DIR
    / "atomization_final_eval_dataset_v1.csv"
)

RESULTS_DIR = (
    BASE_DIR
    / "results"
)

PREDICTIONS_FILE = (
    RESULTS_DIR
    / "atomization_final_eval_predictions_v0_4.csv"
)

RETRY_LOG_FILE = (
    RESULTS_DIR
    / "atomization_final_eval_retry_log_v0_4.csv"
)


FIELDS = [
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


def write_predictions(
    rows: list[dict[str, str | int]],
) -> None:
    def sort_key(
        row: dict[str, str | int],
    ):
        final_eval_id = str(
            row["final_eval_id"]
        )

        try:
            atom_order = int(
                str(
                    row[
                        "predicted_atom_order"
                    ]
                )
            )
        except ValueError:
            atom_order = 0

        return (
            final_eval_id,
            atom_order,
        )

    rows = sorted(
        rows,
        key=sort_key,
    )

    with PREDICTIONS_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


def append_retry_log(
    *,
    final_eval_id: str,
    status: str,
    latency_ms: int,
    error_message: str,
    root_cause: str,
) -> None:
    exists = (
        RETRY_LOG_FILE.exists()
    )

    fieldnames = [
        "timestamp_utc",
        "final_eval_id",
        "attempt",
        "status",
        "latency_ms",
        "error_message",
        "root_cause",
    ]

    with RETRY_LOG_FILE.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        if not exists:
            writer.writeheader()

        writer.writerow(
            {
                "timestamp_utc": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "final_eval_id": (
                    final_eval_id
                ),
                "attempt": 2,
                "status": status,
                "latency_ms": (
                    latency_ms
                ),
                "error_message": (
                    error_message
                ),
                "root_cause": (
                    root_cause
                ),
            }
        )


def get_root_cause(
    exc: Exception,
) -> str:
    cause = exc.__cause__

    if cause is None:
        return repr(exc)

    return repr(cause)


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
            "DATA_IA_GEMINI_API_KEY "
            "is not configured."
        )

    if not model:
        raise RuntimeError(
            "DATA_IA_GEMINI_MODEL "
            "is not configured."
        )

    provider = (
        GeminiClaimAtomizerV04(
            api_key=api_key,
            model=model,
        )
    )

    dataset_rows = load_csv(
        DATASET_FILE
    )

    predictions = load_csv(
        PREDICTIONS_FILE
    )

    failed_ids = sorted(
        {
            row["final_eval_id"]
            for row in predictions
            if row["status"]
            == "failed"
        }
    )

    if not failed_ids:
        print(
            "No failed final-eval "
            "items remain."
        )
        return

    source_by_id = {
        row["final_eval_id"]: row
        for row in dataset_rows
    }

    print("=" * 84)
    print(
        "RESUME CLAIM ATOMIZATION "
        "FINAL EVAL V1 — v0.4"
    )
    print("=" * 84)

    print(
        "Failed items to retry:",
        len(failed_ids),
    )

    print(
        "IDs:",
        ", ".join(
            failed_ids
        ),
    )

    for index, final_eval_id in enumerate(
        failed_ids,
        start=1,
    ):
        row = source_by_id[
            final_eval_id
        ]

        print()
        print("-" * 84)

        print(
            f"[{index}/{len(failed_ids)}] "
            f"{final_eval_id}"
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
                format=(
                    row["format"]
                ),
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
                len(
                    result.atoms
                ),
            )

            predictions = [
                existing
                for existing in predictions
                if existing[
                    "final_eval_id"
                ]
                != final_eval_id
            ]

            if not result.atoms:
                predictions.append(
                    {
                        "final_eval_id": (
                            final_eval_id
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
                    predictions.append(
                        {
                            "final_eval_id": (
                                final_eval_id
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

            append_retry_log(
                final_eval_id=(
                    final_eval_id
                ),
                status="success",
                latency_ms=(
                    latency_ms
                ),
                error_message="",
                root_cause="",
            )

            write_predictions(
                predictions
            )

        except Exception as exc:
            latency_ms = int(
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            root_cause = (
                get_root_cause(
                    exc
                )
            )

            print(
                "STATUS: failed"
            )

            print(
                "ERROR:",
                str(exc),
            )

            print(
                "ROOT CAUSE:",
                root_cause,
            )

            append_retry_log(
                final_eval_id=(
                    final_eval_id
                ),
                status="failed",
                latency_ms=(
                    latency_ms
                ),
                error_message=(
                    str(exc)
                ),
                root_cause=(
                    root_cause
                ),
            )

        if index < len(
            failed_ids
        ):
            time.sleep(5)

    remaining_failed = {
        row["final_eval_id"]
        for row in predictions
        if row["status"]
        == "failed"
    }

    successful_ids = {
        row["final_eval_id"]
        for row in predictions
        if row["status"]
        == "success"
    }

    print()
    print("=" * 84)
    print("RESUME SUMMARY")
    print("=" * 84)

    print(
        "Successful final-eval items:",
        len(
            successful_ids
        ),
    )

    print(
        "Remaining failed items:",
        len(
            remaining_failed
        ),
    )

    if remaining_failed:
        print(
            "Remaining IDs:",
            ", ".join(
                sorted(
                    remaining_failed
                )
            ),
        )

    print()

    print(
        "Predictions:",
        PREDICTIONS_FILE,
    )

    print(
        "Retry log:",
        RETRY_LOG_FILE,
    )


if __name__ == "__main__":
    main()