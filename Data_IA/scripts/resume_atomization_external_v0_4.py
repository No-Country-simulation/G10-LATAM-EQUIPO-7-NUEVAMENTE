"""Retry failed external-validation items for frozen Claim Atomizer v0.4.

Rules:
- preserves all successful attempt-1 predictions;
- retries ONLY items whose current prediction status is failed;
- does not modify claim-atomizer-v0.4;
- does not modify the frozen external dataset;
- does not read Ground Truth;
- keeps retry diagnostics in a separate log;
- claim texts and atom contents are hidden from console output.
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
    "data/evaluation/atomization_external_v1"
)

DATASET_FILE = (
    BASE_DIR
    / "dataset"
    / "external_claim_balanced_dataset_v1.csv"
)

RESULTS_DIR = (
    BASE_DIR
    / "results"
)

PREDICTIONS_FILE = (
    RESULTS_DIR
    / "atomization_external_predictions_v0_4.csv"
)

RETRY_LOG_FILE = (
    RESULTS_DIR
    / "atomization_external_retry_log_v0_4.csv"
)


EXPECTED_ITEMS = 80

CONTENT_FORMAT_USED = (
    "external_documentation"
)


FIELDS = [
    "external_case_id",
    "source_claim_id",
    "source_domain",
    "source_reference",
    "content_format_used",
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
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def sort_key(
    row: dict[str, str | int],
):
    case_id = str(
        row["external_case_id"]
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
        case_id,
        atom_order,
    )


def write_predictions(
    rows: list[dict[str, str | int]],
) -> None:
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


def next_attempt_number(
    external_case_id: str,
) -> int:
    if not RETRY_LOG_FILE.exists():
        return 2

    rows = load_csv(
        RETRY_LOG_FILE
    )

    previous_attempts = []

    for row in rows:
        if (
            row["external_case_id"]
            != external_case_id
        ):
            continue

        try:
            previous_attempts.append(
                int(
                    row["attempt"]
                )
            )
        except ValueError:
            continue

    if not previous_attempts:
        return 2

    return (
        max(previous_attempts)
        + 1
    )


def append_retry_log(
    *,
    external_case_id: str,
    attempt: int,
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
        "external_case_id",
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
                "external_case_id": (
                    external_case_id
                ),
                "attempt": attempt,
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


def result_base(
    row: dict[str, str],
) -> dict[str, str]:
    return {
        "external_case_id": (
            row["external_case_id"]
        ),
        "source_claim_id": (
            row["source_claim_id"]
        ),
        "source_domain": (
            row["source_domain"]
        ),
        "source_reference": (
            row["source_reference"]
        ),
        "content_format_used": (
            CONTENT_FORMAT_USED
        ),
    }


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

    if not DATASET_FILE.exists():
        raise RuntimeError(
            f"Dataset not found: "
            f"{DATASET_FILE}"
        )

    if not PREDICTIONS_FILE.exists():
        raise RuntimeError(
            "Predictions file does not exist. "
            "Run attempt 1 first."
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

    if len(dataset_rows) != EXPECTED_ITEMS:
        raise RuntimeError(
            f"Expected {EXPECTED_ITEMS} dataset rows; "
            f"found {len(dataset_rows)}."
        )

    predictions = load_csv(
        PREDICTIONS_FILE
    )

    failed_ids = sorted(
        {
            row["external_case_id"]
            for row in predictions
            if row["status"]
            == "failed"
        }
    )

    if not failed_ids:
        print(
            "No failed external items remain."
        )
        return

    source_by_id = {
        row["external_case_id"]: row
        for row in dataset_rows
    }

    missing_ids = (
        set(failed_ids)
        - set(source_by_id)
    )

    if missing_ids:
        raise RuntimeError(
            "Failed IDs missing from dataset: "
            + ", ".join(
                sorted(missing_ids)
            )
        )

    print("=" * 84)
    print(
        "RESUME CLAIM ATOMIZATION "
        "EXTERNAL VALIDATION V1 - v0.4"
    )
    print("=" * 84)

    print()
    print(
        "Failed items to retry:",
        len(failed_ids),
    )

    print(
        "Model:",
        model,
    )

    print(
        "Prompt version:",
        provider.prompt_version,
    )

    print(
        "Content format metadata:",
        CONTENT_FORMAT_USED,
    )

    print()
    print(
        "Ground Truth is NOT loaded."
    )

    print(
        "Successful predictions are preserved."
    )

    for index, external_case_id in enumerate(
        failed_ids,
        start=1,
    ):
        row = source_by_id[
            external_case_id
        ]

        attempt = next_attempt_number(
            external_case_id
        )

        print()
        print("-" * 84)

        print(
            f"[{index}/{len(failed_ids)}] "
            f"{external_case_id}"
        )

        print(
            "ATTEMPT:",
            attempt,
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
                        "claim_text_final"
                    ]
                ),
                format=(
                    CONTENT_FORMAT_USED
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
                (
                    result.atomization_class
                    or ""
                ),
            )

            print(
                "ATOM COUNT:",
                len(result.atoms),
            )

            # Remove the failed placeholder for this case.
            predictions = [
                existing
                for existing in predictions
                if existing[
                    "external_case_id"
                ]
                != external_case_id
            ]

            base = result_base(
                row
            )

            if not result.atoms:
                predictions.append(
                    {
                        **base,
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
                            **base,
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
                external_case_id=(
                    external_case_id
                ),
                attempt=attempt,
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
                external_case_id=(
                    external_case_id
                ),
                attempt=attempt,
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

        # More conservative than attempt 1.
        if index < len(
            failed_ids
        ):
            time.sleep(5)

    remaining_failed = {
        row["external_case_id"]
        for row in predictions
        if row["status"]
        == "failed"
    }

    successful_ids = {
        row["external_case_id"]
        for row in predictions
        if row["status"]
        == "success"
    }

    print()
    print("=" * 84)
    print("RESUME SUMMARY")
    print("=" * 84)

    print(
        "Successful external items:",
        len(successful_ids),
    )

    print(
        "Remaining failed items:",
        len(remaining_failed),
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

    print()
    print("IMPORTANT:")

    if remaining_failed:
        print(
            "Do not evaluate yet. "
            "Provider failures still remain."
        )
    else:
        print(
            "All 80 cases now have completed predictions."
        )

        print(
            "Predictions can be frozen before "
            "Ground Truth comparison."
        )


if __name__ == "__main__":
    main()