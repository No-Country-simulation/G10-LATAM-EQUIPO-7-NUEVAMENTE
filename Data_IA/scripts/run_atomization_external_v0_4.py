"""Run frozen Claim Atomizer v0.4 on external validation v1.

Methodological rules:
- claim-atomizer-v0.4 is already frozen in Git.
- external validation dataset is already frozen in Git.
- human Ground Truth is already frozen in Git before this run.
- this script DOES NOT read Ground Truth.
- this script DOES NOT modify the frozen dataset.
- the dataset's inherited `format` column is intentionally ignored
  because it is not a valid content-format signal.
- all cases use the neutral metadata value `external_documentation`.
- claim texts and atom contents are not printed to console.
- attempt 1 is preserved separately for provider reliability analysis.
"""

from __future__ import annotations

import csv
import os
import shutil
import time
from pathlib import Path

from data_ai.evaluation.gemini_claim_atomizer_v0_4 import (
    GeminiClaimAtomizerV04,
)


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

INPUT_FILE = (
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

ATTEMPT1_FILE = (
    RESULTS_DIR
    / "atomization_external_predictions_attempt1_v0_4.csv"
)


EXPECTED_ITEMS = 80

CONTENT_FORMAT_USED = (
    "external_documentation"
)


FIELDNAMES = [
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


def write_rows(
    path: Path,
    rows: list[dict[str, str | int]],
) -> None:
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
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


def validate_source_rows(
    rows: list[dict[str, str]],
) -> None:
    if len(rows) != EXPECTED_ITEMS:
        raise RuntimeError(
            f"Expected {EXPECTED_ITEMS} external items, "
            f"found {len(rows)}."
        )

    required_columns = {
        "external_case_id",
        "source_claim_id",
        "claim_text_final",
        "source_domain",
        "source_reference",
    }

    if not rows:
        raise RuntimeError(
            "External dataset is empty."
        )

    missing_columns = (
        required_columns
        - set(rows[0].keys())
    )

    if missing_columns:
        raise RuntimeError(
            "External dataset missing columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    external_ids = [
        row["external_case_id"].strip()
        for row in rows
    ]

    if any(
        not value
        for value in external_ids
    ):
        raise RuntimeError(
            "Empty external_case_id found."
        )

    if len(set(external_ids)) != EXPECTED_ITEMS:
        raise RuntimeError(
            "external_case_id values are not unique."
        )

    source_ids = [
        row["source_claim_id"].strip()
        for row in rows
    ]

    if any(
        not value
        for value in source_ids
    ):
        raise RuntimeError(
            "Empty source_claim_id found."
        )

    if len(set(source_ids)) != EXPECTED_ITEMS:
        raise RuntimeError(
            "source_claim_id values are not unique."
        )

    empty_claims = [
        row["external_case_id"]
        for row in rows
        if not row[
            "claim_text_final"
        ].strip()
    ]

    if empty_claims:
        raise RuntimeError(
            "Empty claim_text_final values: "
            + ", ".join(
                empty_claims
            )
        )


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

    if PREDICTIONS_FILE.exists():
        raise RuntimeError(
            "Predictions file already exists. "
            "Refusing to overwrite an existing external run: "
            f"{PREDICTIONS_FILE}"
        )

    if ATTEMPT1_FILE.exists():
        raise RuntimeError(
            "Attempt-1 file already exists. "
            "Refusing to overwrite it: "
            f"{ATTEMPT1_FILE}"
        )

    provider = GeminiClaimAtomizerV04(
        api_key=api_key,
        model=model,
    )

    source_rows = load_csv(
        INPUT_FILE
    )

    validate_source_rows(
        source_rows
    )

    output_rows: list[
        dict[str, str | int]
    ] = []

    print("=" * 84)
    print(
        "CLAIM ATOMIZATION EXTERNAL "
        "VALIDATION V1 - v0.4 FROZEN"
    )
    print("=" * 84)

    print()
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

    print(
        "Content format metadata:",
        CONTENT_FORMAT_USED,
    )

    print()
    print(
        "Ground Truth is NOT loaded "
        "by this runner."
    )

    print(
        "Claim texts and atom contents "
        "are hidden from console output."
    )

    print()

    for index, row in enumerate(
        source_rows,
        start=1,
    ):
        case_id = (
            row["external_case_id"]
        )

        print("-" * 84)

        print(
            f"[{index}/{len(source_rows)}] "
            f"{case_id}"
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

            base = result_base(
                row
            )

            if not result.atoms:
                output_rows.append(
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
                    output_rows.append(
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

            base = result_base(
                row
            )

            output_rows.append(
                {
                    **base,
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

        # Persist after every case so a provider or shell failure
        # does not destroy completed work.
        write_rows(
            PREDICTIONS_FILE,
            output_rows,
        )

        print()

        if index < len(
            source_rows
        ):
            time.sleep(1)

    # Preserve the untouched first-attempt output.
    shutil.copyfile(
        PREDICTIONS_FILE,
        ATTEMPT1_FILE,
    )

    successful_ids = {
        row["external_case_id"]
        for row in output_rows
        if row["status"]
        == "success"
    }

    failed_ids = {
        row["external_case_id"]
        for row in output_rows
        if row["status"]
        == "failed"
    }

    all_ids = (
        successful_ids
        | failed_ids
    )

    if len(all_ids) != EXPECTED_ITEMS:
        raise RuntimeError(
            "Attempt 1 did not produce a status "
            f"for all {EXPECTED_ITEMS} cases. "
            f"Found {len(all_ids)} unique IDs."
        )

    print()
    print("=" * 84)
    print("ATTEMPT 1 SUMMARY")
    print("=" * 84)

    print(
        "Successful external items:",
        len(successful_ids),
    )

    print(
        "Failed external items:",
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
        "Predictions:",
        PREDICTIONS_FILE,
    )

    print(
        "Attempt-1 snapshot:",
        ATTEMPT1_FILE,
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Do not evaluate against Ground Truth yet."
    )

    print(
        "If provider failures exist, retry only "
        "those failed IDs next."
    )


if __name__ == "__main__":
    main()