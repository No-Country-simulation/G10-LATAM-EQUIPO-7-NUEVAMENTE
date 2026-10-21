"""Run Test B: stability and provider reliability for Claim Atomizer v0.4.

Purpose
-------
This script performs a small deterministic stability test after Test A.

Methodological constraints
--------------------------
- claim-atomizer-v0.4 remains frozen;
- no prompt changes;
- no production integration;
- no Ground Truth modification;
- no prediction modification from Test A;
- no retries are performed during Test B because provider failures
  are themselves part of the reliability measurement;
- the sample is selected deterministically from the frozen external
  benchmark;
- literal atom text is NOT used for stability comparison.

Sample
------
- 16 frozen external cases;
- 4 per human bucket:
    atomic
    compound
    relational
    non_propositional
- 3 independent repetitions per case;
- 48 total provider calls.

Stability signature
-------------------
A successful output is considered structurally equivalent when these
fields are identical:

- review_status
- atomization_class
- atom_count
- atom_type sequence

The final experiment conclusion also reads the already-frozen Test A
summary. Test C is marked SKIPPED when Test A structural quality is
insufficient.

This script does not redefine Test A thresholds and does not invent a
new production-readiness threshold for Test B.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
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

TEST_A_SUMMARY_FILE = (
    RESULTS_DIR
    / "atomization_external_evaluation_summary_v0_4.json"
)

SAMPLE_FILE = (
    RESULTS_DIR
    / "atomization_external_stability_sample_v0_4.csv"
)

RUNS_FILE = (
    RESULTS_DIR
    / "atomization_external_stability_runs_v0_4.csv"
)

CASE_SUMMARY_FILE = (
    RESULTS_DIR
    / "atomization_external_stability_cases_v0_4.csv"
)

STABILITY_SUMMARY_FILE = (
    RESULTS_DIR
    / "atomization_external_stability_summary_v0_4.json"
)

FINAL_CONCLUSION_FILE = (
    RESULTS_DIR
    / "atomization_external_experiment_conclusion_v0_4.json"
)


EXPECTED_DATASET_ITEMS = 80

BUCKETS = [
    "atomic",
    "compound",
    "relational",
    "non_propositional",
]

CASES_PER_BUCKET = 4

REPETITIONS = 3

EXPECTED_SAMPLE_SIZE = (
    len(BUCKETS)
    * CASES_PER_BUCKET
)

EXPECTED_CALLS = (
    EXPECTED_SAMPLE_SIZE
    * REPETITIONS
)

SEED = "claim-atomizer-v0.4-test-b-20261021"

CONTENT_FORMAT_USED = (
    "external_documentation"
)


SAMPLE_FIELDS = [
    "stability_case_order",
    "external_case_id",
    "source_claim_id",
    "source_domain",
    "source_reference",
    "target_bucket",
    "relation_subtype",
    "claim_text_final",
]


RUN_FIELDS = [
    "timestamp_utc",
    "stability_case_order",
    "external_case_id",
    "source_claim_id",
    "source_domain",
    "target_bucket",
    "relation_subtype",
    "repetition",
    "content_format_used",
    "status",
    "predicted_review_status",
    "predicted_class",
    "predicted_atom_count",
    "predicted_type_sequence",
    "structural_signature",
    "model",
    "prompt_version",
    "latency_ms",
    "error_message",
    "root_cause",
]


CASE_SUMMARY_FIELDS = [
    "stability_case_order",
    "external_case_id",
    "source_domain",
    "target_bucket",
    "relation_subtype",
    "attempts",
    "successes",
    "failures",
    "provider_success_rate",
    "unique_success_signatures",
    "all_three_successful",
    "stable_among_successes",
    "fully_stable",
    "mean_latency_ms_success",
    "min_latency_ms_success",
    "max_latency_ms_success",
]


def load_csv(
    path: Path,
) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def load_json(
    path: Path,
) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Required JSON file not found: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(
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
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


def stable_rank(
    bucket: str,
    external_case_id: str,
) -> str:
    raw = (
        f"{SEED}:{bucket}:{external_case_id}"
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        raw
    ).hexdigest()


def get_root_cause(
    exc: Exception,
) -> str:
    cause = exc.__cause__

    if cause is None:
        return repr(
            exc
        )

    return repr(
        cause
    )


def structural_signature(
    *,
    review_status: str,
    predicted_class: str,
    atom_count: int,
    atom_types: list[str],
) -> str:
    payload = {
        "review_status": (
            review_status
        ),
        "predicted_class": (
            predicted_class
        ),
        "atom_count": (
            atom_count
        ),
        "atom_types": (
            atom_types
        ),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


def validate_dataset(
    rows: list[dict[str, str]],
) -> None:
    if len(rows) != EXPECTED_DATASET_ITEMS:
        raise RuntimeError(
            f"Expected {EXPECTED_DATASET_ITEMS} "
            f"dataset rows, found {len(rows)}."
        )

    required_columns = {
        "external_case_id",
        "source_claim_id",
        "claim_text_final",
        "source_domain",
        "source_reference",
        "target_bucket",
        "relation_subtype",
    }

    if not rows:
        raise RuntimeError(
            "Dataset is empty."
        )

    missing_columns = (
        required_columns
        - set(
            rows[0].keys()
        )
    )

    if missing_columns:
        raise RuntimeError(
            "Dataset missing columns: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    ids = [
        row[
            "external_case_id"
        ].strip()
        for row in rows
    ]

    if len(
        set(ids)
    ) != EXPECTED_DATASET_ITEMS:
        raise RuntimeError(
            "external_case_id values are not unique."
        )

    bucket_counts = Counter(
        row[
            "target_bucket"
        ]
        for row in rows
    )

    for bucket in BUCKETS:
        if (
            bucket_counts.get(
                bucket,
                0,
            )
            < CASES_PER_BUCKET
        ):
            raise RuntimeError(
                f"Not enough cases for bucket {bucket}."
            )


def build_sample(
    rows: list[dict[str, str]],
) -> list[dict[str, str | int]]:
    selected: list[
        dict[str, str | int]
    ] = []

    for bucket in BUCKETS:
        bucket_rows = [
            row
            for row in rows
            if row[
                "target_bucket"
            ]
            == bucket
        ]

        ranked = sorted(
            bucket_rows,
            key=lambda row: (
                stable_rank(
                    bucket,
                    row[
                        "external_case_id"
                    ],
                ),
                row[
                    "external_case_id"
                ],
            ),
        )

        chosen = ranked[
            :CASES_PER_BUCKET
        ]

        for row in chosen:
            selected.append(
                {
                    "stability_case_order": 0,
                    "external_case_id": (
                        row[
                            "external_case_id"
                        ]
                    ),
                    "source_claim_id": (
                        row[
                            "source_claim_id"
                        ]
                    ),
                    "source_domain": (
                        row[
                            "source_domain"
                        ]
                    ),
                    "source_reference": (
                        row[
                            "source_reference"
                        ]
                    ),
                    "target_bucket": (
                        row[
                            "target_bucket"
                        ]
                    ),
                    "relation_subtype": (
                        row.get(
                            "relation_subtype",
                            "",
                        )
                    ),
                    "claim_text_final": (
                        row[
                            "claim_text_final"
                        ]
                    ),
                }
            )

    selected = sorted(
        selected,
        key=lambda row: (
            BUCKETS.index(
                str(
                    row[
                        "target_bucket"
                    ]
                )
            ),
            str(
                row[
                    "external_case_id"
                ]
            ),
        ),
    )

    for index, row in enumerate(
        selected,
        start=1,
    ):
        row[
            "stability_case_order"
        ] = index

    if len(
        selected
    ) != EXPECTED_SAMPLE_SIZE:
        raise RuntimeError(
            f"Expected {EXPECTED_SAMPLE_SIZE} "
            f"sample cases, found {len(selected)}."
        )

    if len(
        {
            str(
                row[
                    "external_case_id"
                ]
            )
            for row in selected
        }
    ) != EXPECTED_SAMPLE_SIZE:
        raise RuntimeError(
            "Duplicate stability sample IDs."
        )

    return selected


def summarize_cases(
    run_rows: list[
        dict[str, object]
    ],
) -> list[
    dict[str, object]
]:
    by_case: dict[
        str,
        list[dict[str, object]]
    ] = defaultdict(
        list
    )

    for row in run_rows:
        by_case[
            str(
                row[
                    "external_case_id"
                ]
            )
        ].append(
            row
        )

    summaries = []

    for external_case_id, rows in sorted(
        by_case.items(),
        key=lambda item: int(
            item[1][0][
                "stability_case_order"
            ]
        ),
    ):
        successes = [
            row
            for row in rows
            if row[
                "status"
            ]
            == "success"
        ]

        failures = [
            row
            for row in rows
            if row[
                "status"
            ]
            == "failed"
        ]

        signatures = {
            str(
                row[
                    "structural_signature"
                ]
            )
            for row in successes
        }

        successful_latencies = [
            int(
                row[
                    "latency_ms"
                ]
            )
            for row in successes
        ]

        all_three_successful = (
            len(
                successes
            )
            == REPETITIONS
        )

        stable_among_successes = (
            len(
                signatures
            )
            <= 1
            and len(
                successes
            )
            >= 2
        )

        fully_stable = (
            all_three_successful
            and len(
                signatures
            )
            == 1
        )

        first = rows[0]

        if successful_latencies:
            mean_latency = round(
                sum(
                    successful_latencies
                )
                / len(
                    successful_latencies
                ),
                2,
            )

            min_latency = min(
                successful_latencies
            )

            max_latency = max(
                successful_latencies
            )

        else:
            mean_latency = ""
            min_latency = ""
            max_latency = ""

        summaries.append(
            {
                "stability_case_order": (
                    first[
                        "stability_case_order"
                    ]
                ),
                "external_case_id": (
                    external_case_id
                ),
                "source_domain": (
                    first[
                        "source_domain"
                    ]
                ),
                "target_bucket": (
                    first[
                        "target_bucket"
                    ]
                ),
                "relation_subtype": (
                    first[
                        "relation_subtype"
                    ]
                ),
                "attempts": (
                    len(
                        rows
                    )
                ),
                "successes": (
                    len(
                        successes
                    )
                ),
                "failures": (
                    len(
                        failures
                    )
                ),
                "provider_success_rate": round(
                    len(
                        successes
                    )
                    / len(
                        rows
                    ),
                    4,
                ),
                "unique_success_signatures": (
                    len(
                        signatures
                    )
                ),
                "all_three_successful": int(
                    all_three_successful
                ),
                "stable_among_successes": int(
                    stable_among_successes
                ),
                "fully_stable": int(
                    fully_stable
                ),
                "mean_latency_ms_success": (
                    mean_latency
                ),
                "min_latency_ms_success": (
                    min_latency
                ),
                "max_latency_ms_success": (
                    max_latency
                ),
            }
        )

    return summaries


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

    # Prevent accidental overwriting of Test B evidence.
    existing_outputs = [
        SAMPLE_FILE,
        RUNS_FILE,
        CASE_SUMMARY_FILE,
        STABILITY_SUMMARY_FILE,
        FINAL_CONCLUSION_FILE,
    ]

    existing = [
        path
        for path
        in existing_outputs
        if path.exists()
    ]

    if existing:
        raise RuntimeError(
            "Test B output already exists. "
            "Refusing to overwrite frozen evidence:\n"
            + "\n".join(
                str(
                    path
                )
                for path
                in existing
            )
        )

    dataset_rows = load_csv(
        DATASET_FILE
    )

    validate_dataset(
        dataset_rows
    )

    test_a_summary = load_json(
        TEST_A_SUMMARY_FILE
    )

    provider = GeminiClaimAtomizerV04(
        api_key=api_key,
        model=model,
    )

    sample = build_sample(
        dataset_rows
    )

    write_csv(
        SAMPLE_FILE,
        SAMPLE_FIELDS,
        sample,
    )

    run_rows: list[
        dict[str, object]
    ] = []

    print("=" * 88)
    print(
        "CLAIM ATOMIZATION TEST B - "
        "STABILITY AND PROVIDER RELIABILITY"
    )
    print("=" * 88)

    print()
    print(
        "Candidate:",
        provider.prompt_version,
    )

    print(
        "Model:",
        model,
    )

    print(
        "Sample cases:",
        EXPECTED_SAMPLE_SIZE,
    )

    print(
        "Repetitions per case:",
        REPETITIONS,
    )

    print(
        "Planned calls:",
        EXPECTED_CALLS,
    )

    print()
    print(
        "No retries will be performed."
    )

    print(
        "Literal atom text is not used "
        "for stability comparison."
    )

    call_number = 0

    for sample_row in sample:
        external_case_id = str(
            sample_row[
                "external_case_id"
            ]
        )

        for repetition in range(
            1,
            REPETITIONS + 1,
        ):
            call_number += 1

            print()
            print("-" * 88)

            print(
                f"[{call_number}/{EXPECTED_CALLS}] "
                f"{external_case_id} "
                f"repetition={repetition}"
            )

            started_at = (
                time.perf_counter()
            )

            try:
                result = (
                    provider.atomize(
                        source_claim_id=str(
                            sample_row[
                                "source_claim_id"
                            ]
                        ),
                        claim_text=str(
                            sample_row[
                                "claim_text_final"
                            ]
                        ),
                        format=(
                            CONTENT_FORMAT_USED
                        ),
                    )
                )

                latency_ms = int(
                    (
                        time.perf_counter()
                        - started_at
                    )
                    * 1000
                )

                atom_types = [
                    atom.atom_type
                    for atom
                    in result.atoms
                ]

                signature = (
                    structural_signature(
                        review_status=(
                            result.review_status
                        ),
                        predicted_class=(
                            result.atomization_class
                            or ""
                        ),
                        atom_count=len(
                            result.atoms
                        ),
                        atom_types=(
                            atom_types
                        ),
                    )
                )

                run_row = {
                    "timestamp_utc": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "stability_case_order": (
                        sample_row[
                            "stability_case_order"
                        ]
                    ),
                    "external_case_id": (
                        external_case_id
                    ),
                    "source_claim_id": (
                        sample_row[
                            "source_claim_id"
                        ]
                    ),
                    "source_domain": (
                        sample_row[
                            "source_domain"
                        ]
                    ),
                    "target_bucket": (
                        sample_row[
                            "target_bucket"
                        ]
                    ),
                    "relation_subtype": (
                        sample_row[
                            "relation_subtype"
                        ]
                    ),
                    "repetition": (
                        repetition
                    ),
                    "content_format_used": (
                        CONTENT_FORMAT_USED
                    ),
                    "status": "success",
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
                    "predicted_type_sequence": (
                        " > ".join(
                            atom_types
                        )
                    ),
                    "structural_signature": (
                        signature
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
                    "error_message": "",
                    "root_cause": "",
                }

                print(
                    "STATUS: success"
                )

                print(
                    "REVIEW STATUS:",
                    result.review_status,
                )

                print(
                    "CLASS:",
                    result.atomization_class
                    or "",
                )

                print(
                    "ATOM COUNT:",
                    len(
                        result.atoms
                    ),
                )

                print(
                    "TYPE SEQUENCE:",
                    (
                        " > ".join(
                            atom_types
                        )
                        or "(none)"
                    ),
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

                run_row = {
                    "timestamp_utc": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "stability_case_order": (
                        sample_row[
                            "stability_case_order"
                        ]
                    ),
                    "external_case_id": (
                        external_case_id
                    ),
                    "source_claim_id": (
                        sample_row[
                            "source_claim_id"
                        ]
                    ),
                    "source_domain": (
                        sample_row[
                            "source_domain"
                        ]
                    ),
                    "target_bucket": (
                        sample_row[
                            "target_bucket"
                        ]
                    ),
                    "relation_subtype": (
                        sample_row[
                            "relation_subtype"
                        ]
                    ),
                    "repetition": (
                        repetition
                    ),
                    "content_format_used": (
                        CONTENT_FORMAT_USED
                    ),
                    "status": "failed",
                    "predicted_review_status": "",
                    "predicted_class": "",
                    "predicted_atom_count": 0,
                    "predicted_type_sequence": "",
                    "structural_signature": "",
                    "model": (
                        provider.model
                    ),
                    "prompt_version": (
                        provider.prompt_version
                    ),
                    "latency_ms": (
                        latency_ms
                    ),
                    "error_message": (
                        str(
                            exc
                        )
                    ),
                    "root_cause": (
                        root_cause
                    ),
                }

                print(
                    "STATUS: failed"
                )

                print(
                    "ERROR:",
                    str(
                        exc
                    ),
                )

                print(
                    "ROOT CAUSE:",
                    root_cause,
                )

            run_rows.append(
                run_row
            )

            # Persist after every call.
            write_csv(
                RUNS_FILE,
                RUN_FIELDS,
                run_rows,
            )

            if (
                call_number
                < EXPECTED_CALLS
            ):
                time.sleep(
                    3
                )

    if len(
        run_rows
    ) != EXPECTED_CALLS:
        raise RuntimeError(
            f"Expected {EXPECTED_CALLS} run rows, "
            f"found {len(run_rows)}."
        )

    case_summaries = summarize_cases(
        run_rows
    )

    write_csv(
        CASE_SUMMARY_FILE,
        CASE_SUMMARY_FIELDS,
        case_summaries,
    )

    # ==========================================================
    # Overall provider metrics
    # ==========================================================

    success_rows = [
        row
        for row
        in run_rows
        if row[
            "status"
        ]
        == "success"
    ]

    failed_rows = [
        row
        for row
        in run_rows
        if row[
            "status"
        ]
        == "failed"
    ]

    provider_success_rate = (
        len(
            success_rows
        )
        / EXPECTED_CALLS
    )

    # ==========================================================
    # Stability metrics
    # ==========================================================

    all_three_successful_cases = sum(
        int(
            row[
                "all_three_successful"
            ]
        )
        for row
        in case_summaries
    )

    fully_stable_cases = sum(
        int(
            row[
                "fully_stable"
            ]
        )
        for row
        in case_summaries
    )

    cases_with_two_or_more_successes = sum(
        1
        for row
        in case_summaries
        if int(
            row[
                "successes"
            ]
        )
        >= 2
    )

    stable_among_successes_cases = sum(
        int(
            row[
                "stable_among_successes"
            ]
        )
        for row
        in case_summaries
    )

    fully_stable_rate = (
        fully_stable_cases
        / EXPECTED_SAMPLE_SIZE
    )

    if cases_with_two_or_more_successes:
        stability_among_successes_rate = (
            stable_among_successes_cases
            / cases_with_two_or_more_successes
        )
    else:
        stability_among_successes_rate = 0.0

    # ==========================================================
    # Bucket stability
    # ==========================================================

    bucket_summary = {}

    for bucket in BUCKETS:
        bucket_cases = [
            row
            for row
            in case_summaries
            if row[
                "target_bucket"
            ]
            == bucket
        ]

        bucket_fully_stable = sum(
            int(
                row[
                    "fully_stable"
                ]
            )
            for row
            in bucket_cases
        )

        bucket_all_success = sum(
            int(
                row[
                    "all_three_successful"
                ]
            )
            for row
            in bucket_cases
        )

        bucket_summary[
            bucket
        ] = {
            "cases": len(
                bucket_cases
            ),
            "all_three_successful": (
                bucket_all_success
            ),
            "fully_stable": (
                bucket_fully_stable
            ),
            "fully_stable_rate": round(
                (
                    bucket_fully_stable
                    / len(
                        bucket_cases
                    )
                    if bucket_cases
                    else 0.0
                ),
                4,
            ),
        }

    # ==========================================================
    # Latency
    # ==========================================================

    success_latencies = [
        int(
            row[
                "latency_ms"
            ]
        )
        for row
        in success_rows
    ]

    if success_latencies:
        mean_latency_ms = round(
            sum(
                success_latencies
            )
            / len(
                success_latencies
            ),
            2,
        )

        min_latency_ms = min(
            success_latencies
        )

        max_latency_ms = max(
            success_latencies
        )

    else:
        mean_latency_ms = None
        min_latency_ms = None
        max_latency_ms = None

    # ==========================================================
    # Test A frozen result
    # ==========================================================

    test_a = (
        test_a_summary.get(
            "test_a",
            {},
        )
    )

    test_a_decision = (
        test_a.get(
            "decision",
            "UNKNOWN",
        )
    )

    test_a_results = (
        test_a.get(
            "results",
            {},
        )
    )

    # ==========================================================
    # Test B summary
    # ==========================================================

    stability_summary = {
        "candidate": (
            "claim-atomizer-v0.4"
        ),
        "test": (
            "Test B - stability and provider reliability"
        ),
        "methodology": {
            "sample_selection": (
                "deterministic stable-hash selection"
            ),
            "sample_size": (
                EXPECTED_SAMPLE_SIZE
            ),
            "cases_per_bucket": (
                CASES_PER_BUCKET
            ),
            "repetitions_per_case": (
                REPETITIONS
            ),
            "planned_calls": (
                EXPECTED_CALLS
            ),
            "retries_performed": False,
            "literal_atom_text_used_for_stability": False,
            "stability_signature": [
                "review_status",
                "atomization_class",
                "atom_count",
                "atom_type_sequence",
            ],
            "candidate_modified": False,
            "prompt_modified": False,
            "ground_truth_modified": False,
            "production_impact": False,
        },
        "provider": {
            "successful_calls": (
                len(
                    success_rows
                )
            ),
            "failed_calls": (
                len(
                    failed_rows
                )
            ),
            "total_calls": (
                EXPECTED_CALLS
            ),
            "success_rate": round(
                provider_success_rate,
                4,
            ),
        },
        "stability": {
            "sample_cases": (
                EXPECTED_SAMPLE_SIZE
            ),
            "all_three_successful_cases": (
                all_three_successful_cases
            ),
            "fully_stable_cases": (
                fully_stable_cases
            ),
            "fully_stable_rate": round(
                fully_stable_rate,
                4,
            ),
            "cases_with_two_or_more_successes": (
                cases_with_two_or_more_successes
            ),
            "stable_among_successes_cases": (
                stable_among_successes_cases
            ),
            "stability_among_successes_rate": round(
                stability_among_successes_rate,
                4,
            ),
        },
        "bucket_stability": (
            bucket_summary
        ),
        "latency_success_only": {
            "mean_ms": (
                mean_latency_ms
            ),
            "min_ms": (
                min_latency_ms
            ),
            "max_ms": (
                max_latency_ms
            ),
        },
        "interpretation": (
            "Test B characterizes repeatability and provider "
            "reliability only. No new arbitrary pass/fail "
            "threshold is introduced after observing results."
        ),
    }

    STABILITY_SUMMARY_FILE.write_text(
        json.dumps(
            stability_summary,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # ==========================================================
    # Final experiment conclusion
    # ==========================================================

    test_a_failed_structural_quality = (
        test_a_decision
        == "INVESTIGATE"
        or any(
            not bool(
                result.get(
                    "passed",
                    False,
                )
            )
            for key, result
            in test_a_results.items()
            if key
            in {
                "exact_structure_accuracy",
                "count_accuracy",
            }
        )
    )

    if test_a_failed_structural_quality:
        test_c_status = (
            "SKIPPED"
        )

        test_c_reason = (
            "External structural validation did not meet "
            "the frozen minimum quality criteria. Running "
            "content-support A/B would confound downstream "
            "effects with known atomization errors."
        )

        final_decision = (
            "STOP_V0_4_FOR_PRODUCTION_INTEGRATION"
        )

    else:
        test_c_status = (
            "NOT_RUN"
        )

        test_c_reason = (
            "Test A did not trigger the structural-quality "
            "stop condition."
        )

        final_decision = (
            "REVIEW_BEFORE_TEST_C"
        )

    conclusion = {
        "candidate": (
            "claim-atomizer-v0.4"
        ),
        "experiment": (
            "Claim Atomization v1"
        ),
        "test_a": {
            "status": (
                test_a_decision
            ),
            "source": str(
                TEST_A_SUMMARY_FILE
            ),
            "key_results": (
                test_a_results
            ),
        },
        "test_b": {
            "status": (
                "COMPLETED"
            ),
            "provider_success_rate": round(
                provider_success_rate,
                4,
            ),
            "fully_stable_rate": round(
                fully_stable_rate,
                4,
            ),
            "stability_among_successes_rate": round(
                stability_among_successes_rate,
                4,
            ),
            "source": str(
                STABILITY_SUMMARY_FILE
            ),
        },
        "test_c": {
            "status": (
                test_c_status
            ),
            "reason": (
                test_c_reason
            ),
        },
        "final_decision": (
            final_decision
        ),
        "production_integration": False,
        "prompt_tuning_performed_during_external_validation": False,
        "future_work": {
            "v0_4_should_be_modified": False,
            "possible_future_candidate": (
                "A future v0.5 may be designed as a new "
                "experiment using the frozen external failure "
                "analysis as hypothesis-generation evidence."
            ),
            "important": (
                "Any future candidate should be evaluated "
                "on a newly protected benchmark rather than "
                "tuned directly against this external set."
            ),
        },
        "final_interpretation": (
            "claim-atomizer-v0.4 remains a useful experimental "
            "artifact but did not demonstrate sufficient "
            "external structural generalization for production "
            "integration."
        ),
    }

    FINAL_CONCLUSION_FILE.write_text(
        json.dumps(
            conclusion,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # ==========================================================
    # Console summary
    # ==========================================================

    print()
    print("=" * 88)
    print(
        "TEST B SUMMARY"
    )
    print("=" * 88)

    print()
    print(
        "PROVIDER"
    )
    print("-" * 44)

    print(
        "Successful calls:",
        f"{len(success_rows)}/{EXPECTED_CALLS}",
    )

    print(
        "Failed calls:",
        len(
            failed_rows
        ),
    )

    print(
        "Provider success rate:",
        f"{provider_success_rate:.4f}",
    )

    print()
    print(
        "STABILITY"
    )
    print("-" * 44)

    print(
        "Cases:",
        EXPECTED_SAMPLE_SIZE,
    )

    print(
        "All 3 repetitions successful:",
        f"{all_three_successful_cases}/"
        f"{EXPECTED_SAMPLE_SIZE}",
    )

    print(
        "Fully stable cases:",
        f"{fully_stable_cases}/"
        f"{EXPECTED_SAMPLE_SIZE}",
    )

    print(
        "Fully stable rate:",
        f"{fully_stable_rate:.4f}",
    )

    print(
        "Stable among cases with >=2 successes:",
        f"{stable_among_successes_cases}/"
        f"{cases_with_two_or_more_successes}",
    )

    print(
        "Stability among successes:",
        f"{stability_among_successes_rate:.4f}",
    )

    print()
    print(
        "BY BUCKET"
    )
    print("-" * 44)

    for bucket in BUCKETS:
        stats = (
            bucket_summary[
                bucket
            ]
        )

        print(
            f"{bucket}: "
            f"{stats['fully_stable']}/"
            f"{stats['cases']} fully stable"
        )

    print()
    print(
        "LATENCY - SUCCESSFUL CALLS"
    )
    print("-" * 44)

    print(
        "Mean ms:",
        mean_latency_ms,
    )

    print(
        "Min ms:",
        min_latency_ms,
    )

    print(
        "Max ms:",
        max_latency_ms,
    )

    print()
    print(
        "FINAL EXPERIMENT DECISION"
    )
    print("-" * 44)

    print(
        "Test A:",
        test_a_decision,
    )

    print(
        "Test B:",
        "COMPLETED",
    )

    print(
        "Test C:",
        test_c_status,
    )

    print(
        "Final decision:",
        final_decision,
    )

    print(
        "Production integration:",
        "NO",
    )

    print()
    print(
        "OUTPUTS"
    )
    print("-" * 44)

    print(
        "Sample:",
        SAMPLE_FILE,
    )

    print(
        "Runs:",
        RUNS_FILE,
    )

    print(
        "Case summary:",
        CASE_SUMMARY_FILE,
    )

    print(
        "Stability summary:",
        STABILITY_SUMMARY_FILE,
    )

    print(
        "Final conclusion:",
        FINAL_CONCLUSION_FILE,
    )


if __name__ == "__main__":
    main()