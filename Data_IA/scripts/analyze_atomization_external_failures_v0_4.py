"""Analyze failure patterns from external atomization validation v0.4.

This script is offline-only:
- no Gemini calls;
- no model changes;
- no Ground Truth changes;
- no prediction changes.

It analyzes:
- propositional detection failures;
- structural failures;
- over/under-atomization;
- confusion by human bucket;
- confusion by predicted class;
- relation-subtype patterns;
- source-domain patterns;
- atom-type sequence mismatches.

Outputs:
- atomization_external_detection_failures_v0_4.csv
- atomization_external_structural_failures_v0_4.csv
- atomization_external_failure_summary_v0_4.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation/atomization_external_v1"
)

RESULTS_DIR = (
    BASE_DIR
    / "results"
)

CASES_FILE = (
    RESULTS_DIR
    / "atomization_external_evaluation_cases_v0_4.csv"
)

DETECTION_FAILURES_FILE = (
    RESULTS_DIR
    / "atomization_external_detection_failures_v0_4.csv"
)

STRUCTURAL_FAILURES_FILE = (
    RESULTS_DIR
    / "atomization_external_structural_failures_v0_4.csv"
)

SUMMARY_FILE = (
    RESULTS_DIR
    / "atomization_external_failure_summary_v0_4.json"
)


EXPECTED_ITEMS = 80


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


def parse_int(
    value: str,
) -> int | None:
    value = str(
        value
    ).strip()

    if not value:
        return None

    try:
        return int(
            value
        )
    except ValueError:
        return None


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


def main() -> None:
    rows = load_csv(
        CASES_FILE
    )

    if len(rows) != EXPECTED_ITEMS:
        raise RuntimeError(
            f"Expected {EXPECTED_ITEMS} evaluation cases, "
            f"found {len(rows)}."
        )

    # ==========================================================
    # Detection failures
    # ==========================================================

    detection_failures = [
        row
        for row in rows
        if row["detection_result"]
        in {
            "FP",
            "FN",
            "provider_failed",
        }
    ]

    detection_failure_rows = []

    for row in detection_failures:
        detection_failure_rows.append(
            {
                "external_case_id": (
                    row["external_case_id"]
                ),
                "source_domain": (
                    row["source_domain"]
                ),
                "target_bucket": (
                    row["target_bucket"]
                ),
                "relation_subtype": (
                    row["relation_subtype"]
                ),
                "gt_review_status": (
                    row["gt_review_status"]
                ),
                "predicted_review_status": (
                    row["predicted_review_status"]
                ),
                "detection_result": (
                    row["detection_result"]
                ),
                "gt_class": (
                    row["gt_class"]
                ),
                "predicted_class": (
                    row["predicted_class"]
                ),
                "expected_atom_count": (
                    row["expected_atom_count"]
                ),
                "predicted_atom_count": (
                    row["predicted_atom_count"]
                ),
            }
        )

    detection_fieldnames = [
        "external_case_id",
        "source_domain",
        "target_bucket",
        "relation_subtype",
        "gt_review_status",
        "predicted_review_status",
        "detection_result",
        "gt_class",
        "predicted_class",
        "expected_atom_count",
        "predicted_atom_count",
    ]

    write_csv(
        DETECTION_FAILURES_FILE,
        detection_fieldnames,
        detection_failure_rows,
    )

    # ==========================================================
    # Structural failures
    # ==========================================================

    structural_failures = []

    for row in rows:
        if (
            row["gt_review_status"]
            != "valid_claim"
        ):
            continue

        if (
            row["exact_structure_match"]
            == "1"
        ):
            continue

        expected_count = parse_int(
            row["expected_atom_count"]
        )

        predicted_count = parse_int(
            row["predicted_atom_count"]
        )

        delta = parse_int(
            row["atom_delta"]
        )

        if delta is None:
            atomization_direction = (
                "not_evaluable"
            )
        elif delta > 0:
            atomization_direction = (
                "over_atomized"
            )
        elif delta < 0:
            atomization_direction = (
                "under_atomized"
            )
        else:
            atomization_direction = (
                "count_equal_structure_wrong"
            )

        structural_failures.append(
            {
                "external_case_id": (
                    row["external_case_id"]
                ),
                "source_domain": (
                    row["source_domain"]
                ),
                "target_bucket": (
                    row["target_bucket"]
                ),
                "relation_subtype": (
                    row["relation_subtype"]
                ),
                "gt_class": (
                    row["gt_class"]
                ),
                "predicted_class": (
                    row["predicted_class"]
                ),
                "expected_atom_count": (
                    expected_count
                    if expected_count is not None
                    else ""
                ),
                "predicted_atom_count": (
                    predicted_count
                    if predicted_count is not None
                    else ""
                ),
                "atom_delta": (
                    delta
                    if delta is not None
                    else ""
                ),
                "atomization_direction": (
                    atomization_direction
                ),
                "gt_type_sequence": (
                    row["gt_type_sequence"]
                ),
                "predicted_type_sequence": (
                    row[
                        "predicted_type_sequence"
                    ]
                ),
                "class_match": (
                    row["class_match"]
                ),
                "count_match": (
                    row["count_match"]
                ),
                "type_sequence_match": (
                    row[
                        "type_sequence_match"
                    ]
                ),
            }
        )

    structural_fieldnames = [
        "external_case_id",
        "source_domain",
        "target_bucket",
        "relation_subtype",
        "gt_class",
        "predicted_class",
        "expected_atom_count",
        "predicted_atom_count",
        "atom_delta",
        "atomization_direction",
        "gt_type_sequence",
        "predicted_type_sequence",
        "class_match",
        "count_match",
        "type_sequence_match",
    ]

    write_csv(
        STRUCTURAL_FAILURES_FILE,
        structural_fieldnames,
        structural_failures,
    )

    # ==========================================================
    # Aggregations
    # ==========================================================

    detection_counts = Counter(
        row["detection_result"]
        for row in rows
    )

    structural_direction_counts = Counter(
        row["atomization_direction"]
        for row in structural_failures
    )

    failures_by_bucket = Counter(
        row["target_bucket"]
        for row in structural_failures
    )

    failures_by_domain = Counter(
        row["source_domain"]
        for row in structural_failures
    )

    relation_failures = [
        row
        for row in structural_failures
        if row["target_bucket"]
        == "relational"
    ]

    relation_failures_by_subtype = Counter(
        (
            row["relation_subtype"]
            or "unspecified"
        )
        for row in relation_failures
    )

    class_confusion = Counter(
        (
            row["gt_class"],
            row["predicted_class"]
            or "non_propositional",
        )
        for row in structural_failures
    )

    type_sequence_confusion = Counter(
        (
            row["gt_type_sequence"],
            row["predicted_type_sequence"]
            or "none",
        )
        for row in structural_failures
        if (
            row["gt_type_sequence"]
            != row[
                "predicted_type_sequence"
            ]
        )
    )

    exact_by_bucket = defaultdict(
        lambda: {
            "total": 0,
            "exact": 0,
        }
    )

    for row in rows:
        if (
            row["gt_review_status"]
            != "valid_claim"
        ):
            continue

        bucket = (
            row["target_bucket"]
        )

        exact_by_bucket[
            bucket
        ]["total"] += 1

        if (
            row["exact_structure_match"]
            == "1"
        ):
            exact_by_bucket[
                bucket
            ]["exact"] += 1

    exact_bucket_summary = {}

    for bucket, stats in (
        exact_by_bucket.items()
    ):
        total = stats["total"]
        exact = stats["exact"]

        exact_bucket_summary[
            bucket
        ] = {
            "total": total,
            "exact": exact,
            "failed": (
                total
                - exact
            ),
            "exact_accuracy": round(
                (
                    exact
                    / total
                    if total
                    else 0.0
                ),
                4,
            ),
        }

    # ==========================================================
    # Dominant patterns
    # ==========================================================

    over_relational = sum(
        1
        for row in relation_failures
        if row["atomization_direction"]
        == "over_atomized"
    )

    under_compound = sum(
        1
        for row in structural_failures
        if (
            row["target_bucket"]
            == "compound"
            and row[
                "atomization_direction"
            ]
            == "under_atomized"
        )
    )

    over_atomic = sum(
        1
        for row in structural_failures
        if (
            row["target_bucket"]
            == "atomic"
            and row[
                "atomization_direction"
            ]
            == "over_atomized"
        )
    )

    dominant_patterns = {
        "relational_over_atomization": {
            "count": (
                over_relational
            ),
            "total_relational_cases": 20,
            "rate": round(
                over_relational / 20,
                4,
            ),
        },
        "compound_under_atomization": {
            "count": (
                under_compound
            ),
            "total_compound_cases": 20,
            "rate": round(
                under_compound / 20,
                4,
            ),
        },
        "atomic_over_atomization": {
            "count": (
                over_atomic
            ),
            "total_atomic_cases": 20,
            "rate": round(
                over_atomic / 20,
                4,
            ),
        },
    }

    # ==========================================================
    # JSON-friendly transformations
    # ==========================================================

    class_confusion_json = [
        {
            "gt_class": gt_class,
            "predicted_class": (
                predicted_class
            ),
            "count": count,
        }
        for (
            gt_class,
            predicted_class,
        ), count in (
            class_confusion.most_common()
        )
    ]

    type_confusion_json = [
        {
            "gt_type_sequence": (
                gt_sequence
            ),
            "predicted_type_sequence": (
                pred_sequence
            ),
            "count": count,
        }
        for (
            gt_sequence,
            pred_sequence,
        ), count in (
            type_sequence_confusion
            .most_common()
        )
    ]

    # ==========================================================
    # Summary
    # ==========================================================

    summary = {
        "candidate": (
            "claim-atomizer-v0.4"
        ),
        "evaluation_set": (
            "atomization-external-validation-v1"
        ),
        "analysis_type": (
            "offline_failure_analysis"
        ),
        "gemini_calls": False,
        "model_modified": False,
        "ground_truth_modified": False,
        "predictions_modified": False,
        "counts": {
            "total_cases": (
                len(rows)
            ),
            "detection_failures": (
                len(
                    detection_failures
                )
            ),
            "structural_failures": (
                len(
                    structural_failures
                )
            ),
        },
        "detection": {
            "confusion_counts": dict(
                sorted(
                    detection_counts.items()
                )
            ),
            "failure_counts": {
                key: value
                for key, value
                in detection_counts.items()
                if key
                in {
                    "FP",
                    "FN",
                    "provider_failed",
                }
            },
        },
        "structure": {
            "failure_direction_counts": dict(
                sorted(
                    structural_direction_counts.items()
                )
            ),
            "failures_by_bucket": dict(
                sorted(
                    failures_by_bucket.items()
                )
            ),
            "failures_by_domain": dict(
                sorted(
                    failures_by_domain.items()
                )
            ),
            "exact_by_bucket": (
                exact_bucket_summary
            ),
        },
        "relational": {
            "failure_count": (
                len(
                    relation_failures
                )
            ),
            "failures_by_subtype": dict(
                sorted(
                    relation_failures_by_subtype.items()
                )
            ),
        },
        "class_confusion": (
            class_confusion_json
        ),
        "type_sequence_confusion": (
            type_confusion_json
        ),
        "dominant_patterns": (
            dominant_patterns
        ),
        "interpretation_guardrails": [
            (
                "This analysis identifies observed "
                "failure patterns only."
            ),
            (
                "It does not redesign or tune "
                "claim-atomizer-v0.4."
            ),
            (
                "No conclusion about production "
                "integration should be made from a "
                "single failure category alone."
            ),
            (
                "The benchmark is deliberately "
                "balanced and does not represent "
                "natural production prevalence."
            ),
        ],
    }

    SUMMARY_FILE.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # ==========================================================
    # Console summary
    # ==========================================================

    print("=" * 88)
    print(
        "ATOMIZATION EXTERNAL FAILURE "
        "ANALYSIS - v0.4"
    )
    print("=" * 88)

    print()
    print(
        "DETECTION FAILURES"
    )
    print("-" * 44)

    print(
        "Total:",
        len(
            detection_failures
        ),
    )

    print(
        "FP:",
        detection_counts.get(
            "FP",
            0,
        ),
    )

    print(
        "FN:",
        detection_counts.get(
            "FN",
            0,
        ),
    )

    print(
        "Provider failed:",
        detection_counts.get(
            "provider_failed",
            0,
        ),
    )

    print()
    print(
        "STRUCTURAL FAILURES"
    )
    print("-" * 44)

    print(
        "Total:",
        len(
            structural_failures
        ),
    )

    for key, value in sorted(
        structural_direction_counts.items()
    ):
        print(
            f"{key}: {value}"
        )

    print()
    print(
        "FAILURES BY HUMAN BUCKET"
    )
    print("-" * 44)

    for bucket in [
        "atomic",
        "compound",
        "relational",
    ]:
        print(
            f"{bucket}: "
            f"{failures_by_bucket.get(bucket, 0)}"
        )

    print()
    print(
        "RELATIONAL FAILURES BY SUBTYPE"
    )
    print("-" * 44)

    for subtype, count in sorted(
        relation_failures_by_subtype.items()
    ):
        print(
            f"{subtype}: {count}"
        )

    print()
    print(
        "DOMINANT PATTERNS"
    )
    print("-" * 44)

    print(
        "Relational over-atomization:",
        f"{over_relational}/20",
    )

    print(
        "Compound under-atomization:",
        f"{under_compound}/20",
    )

    print(
        "Atomic over-atomization:",
        f"{over_atomic}/20",
    )

    print()
    print(
        "TOP CLASS CONFUSIONS"
    )
    print("-" * 44)

    for (
        gt_class,
        predicted_class,
    ), count in (
        class_confusion.most_common(
            10
        )
    ):
        print(
            f"{gt_class} -> "
            f"{predicted_class}: "
            f"{count}"
        )

    print()
    print(
        "FAILURES BY DOMAIN"
    )
    print("-" * 44)

    for domain, count in sorted(
        failures_by_domain.items()
    ):
        print(
            f"{domain}: {count}"
        )

    print()
    print(
        "OUTPUTS"
    )
    print("-" * 44)

    print(
        "Detection failures:",
        DETECTION_FAILURES_FILE,
    )

    print(
        "Structural failures:",
        STRUCTURAL_FAILURES_FILE,
    )

    print(
        "Summary:",
        SUMMARY_FILE,
    )


if __name__ == "__main__":
    main()