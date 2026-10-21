"""Build untouched Claim Atomization final evaluation set v1.

The final evaluation set contains every original claim that was
not used in:

- atomization development v1
- validation / holdout v1

Important:
- no Gemini outputs are consulted;
- no routing results are consulted;
- no semantic-review results are consulted;
- all remaining source claims are included;
- selection is deterministic because there is no sampling.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


EVALUATION_DIR = Path(
    "data/evaluation"
)

SOURCE_GT = (
    EVALUATION_DIR
    / "calibration_v1"
    / "results"
    / "content_support_claim_ground_truth_v1.csv"
)

DEV_DATASET = (
    EVALUATION_DIR
    / "atomization_v1"
    / "atomization_dataset_v1.csv"
)

VALIDATION_DATASET = (
    EVALUATION_DIR
    / "atomization_v1"
    / "holdout_v1"
    / "atomization_holdout_dataset_v1.csv"
)

FINAL_DIR = (
    EVALUATION_DIR
    / "atomization_v1"
    / "final_eval_v1"
)

OUTPUT_DATASET = (
    FINAL_DIR
    / "atomization_final_eval_dataset_v1.csv"
)

OUTPUT_MANIFEST = (
    FINAL_DIR
    / "atomization_final_eval_manifest_v1.json"
)


EXPECTED_SOURCE_COUNT = 59
EXPECTED_DEV_COUNT = 16
EXPECTED_VALIDATION_COUNT = 20
EXPECTED_FINAL_COUNT = 23


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


def source_key(
    calibration_id: str,
    claim_id: str,
) -> str:
    return (
        f"{calibration_id}|{claim_id}"
    )


def main() -> None:
    source_rows = load_csv(
        SOURCE_GT
    )

    dev_rows = load_csv(
        DEV_DATASET
    )

    validation_rows = load_csv(
        VALIDATION_DATASET
    )

    if (
        len(source_rows)
        != EXPECTED_SOURCE_COUNT
    ):
        raise RuntimeError(
            "Unexpected source claim count: "
            f"{len(source_rows)}"
        )

    if (
        len(dev_rows)
        != EXPECTED_DEV_COUNT
    ):
        raise RuntimeError(
            "Unexpected development count: "
            f"{len(dev_rows)}"
        )

    if (
        len(validation_rows)
        != EXPECTED_VALIDATION_COUNT
    ):
        raise RuntimeError(
            "Unexpected validation count: "
            f"{len(validation_rows)}"
        )

    source_keys = {
        source_key(
            row["calibration_id"],
            row["claim_id"],
        )
        for row in source_rows
    }

    dev_keys = {
        source_key(
            row["calibration_id"],
            row["source_claim_id"],
        )
        for row in dev_rows
    }

    validation_keys = {
        source_key(
            row["calibration_id"],
            row["source_claim_id"],
        )
        for row in validation_rows
    }

    dev_validation_overlap = (
        dev_keys
        & validation_keys
    )

    if dev_validation_overlap:
        raise RuntimeError(
            "Development/validation overlap detected: "
            f"{sorted(dev_validation_overlap)}"
        )

    used_keys = (
        dev_keys
        | validation_keys
    )

    unknown_used_keys = (
        used_keys
        - source_keys
    )

    if unknown_used_keys:
        raise RuntimeError(
            "Development or validation contains "
            "claims not present in source GT: "
            f"{sorted(unknown_used_keys)}"
        )

    remaining_rows = [
        row
        for row in source_rows
        if source_key(
            row["calibration_id"],
            row["claim_id"],
        )
        not in used_keys
    ]

    if (
        len(remaining_rows)
        != EXPECTED_FINAL_COUNT
    ):
        raise RuntimeError(
            "Expected "
            f"{EXPECTED_FINAL_COUNT} "
            "untouched claims, found "
            f"{len(remaining_rows)}."
        )

    remaining_rows.sort(
        key=lambda row: (
            row["calibration_id"],
            row["claim_id"],
        )
    )

    final_keys = {
        source_key(
            row["calibration_id"],
            row["claim_id"],
        )
        for row in remaining_rows
    }

    if (
        final_keys
        & dev_keys
    ):
        raise RuntimeError(
            "Final evaluation overlaps development."
        )

    if (
        final_keys
        & validation_keys
    ):
        raise RuntimeError(
            "Final evaluation overlaps validation."
        )

    all_partitioned_keys = (
        dev_keys
        | validation_keys
        | final_keys
    )

    if (
        all_partitioned_keys
        != source_keys
    ):
        missing = sorted(
            source_keys
            - all_partitioned_keys
        )

        extra = sorted(
            all_partitioned_keys
            - source_keys
        )

        raise RuntimeError(
            "Partition integrity failure. "
            f"Missing={missing}; "
            f"Extra={extra}"
        )

    FINAL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_rows = []

    for index, row in enumerate(
        remaining_rows,
        start=1,
    ):
        output_rows.append(
            {
                "final_eval_id": (
                    f"FINAL-V1-{index:03d}"
                ),
                "calibration_id": (
                    row["calibration_id"]
                ),
                "source_claim_id": (
                    row["claim_id"]
                ),
                "format": (
                    row["format"]
                ),
                "source_claim_text": (
                    row["claim_text"]
                ),
                "human_support_label": (
                    row[
                        "human_support_label"
                    ]
                ),
                "annotation_priority": (
                    row.get(
                        "annotation_priority",
                        "",
                    )
                ),
                "selection_reason": (
                    "all_remaining_untouched_claims"
                ),
            }
        )

    fieldnames = [
        "final_eval_id",
        "calibration_id",
        "source_claim_id",
        "format",
        "source_claim_text",
        "human_support_label",
        "annotation_priority",
        "selection_reason",
    ]

    with OUTPUT_DATASET.open(
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
            output_rows
        )

    format_counts = Counter(
        row["format"]
        for row in output_rows
    )

    support_counts = Counter(
        row[
            "human_support_label"
        ]
        for row in output_rows
    )

    priority_counts = Counter(
        row[
            "annotation_priority"
        ]
        for row in output_rows
    )

    manifest = {
        "version": (
            "atomization-final-eval-v1"
        ),
        "source_ground_truth": (
            str(SOURCE_GT)
        ),
        "development_dataset": (
            str(DEV_DATASET)
        ),
        "validation_dataset": (
            str(VALIDATION_DATASET)
        ),
        "source_claim_count": (
            len(source_rows)
        ),
        "development_claim_count": (
            len(dev_rows)
        ),
        "validation_claim_count": (
            len(validation_rows)
        ),
        "final_eval_claim_count": (
            len(output_rows)
        ),
        "development_validation_overlap": (
            len(
                dev_keys
                & validation_keys
            )
        ),
        "development_final_overlap": (
            len(
                dev_keys
                & final_keys
            )
        ),
        "validation_final_overlap": (
            len(
                validation_keys
                & final_keys
            )
        ),
        "complete_partition_verified": (
            all_partitioned_keys
            == source_keys
        ),
        "selection_policy": (
            "all source claims remaining after "
            "development and validation exclusion"
        ),
        "sampling_used": False,
        "gemini_used_for_selection": False,
        "model_results_used_for_selection": False,
        "format_distribution": (
            dict(
                format_counts
            )
        ),
        "human_support_distribution": (
            dict(
                support_counts
            )
        ),
        "annotation_priority_distribution": (
            dict(
                priority_counts
            )
        ),
    }

    OUTPUT_MANIFEST.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 84)
    print(
        "CLAIM ATOMIZATION FINAL EVAL V1"
    )
    print("=" * 84)

    print(
        "Original source claims:",
        len(source_rows),
    )

    print(
        "Development claims:",
        len(dev_rows),
    )

    print(
        "Validation claims:",
        len(validation_rows),
    )

    print(
        "Final untouched claims:",
        len(output_rows),
    )

    print()

    print(
        "Development/validation overlap:",
        len(
            dev_keys
            & validation_keys
        ),
    )

    print(
        "Development/final overlap:",
        len(
            dev_keys
            & final_keys
        ),
    )

    print(
        "Validation/final overlap:",
        len(
            validation_keys
            & final_keys
        ),
    )

    print(
        "Complete partition verified:",
        (
            all_partitioned_keys
            == source_keys
        ),
    )

    print()

    print(
        "Format distribution:"
    )

    for name in sorted(
        format_counts
    ):
        print(
            f"  {name}: "
            f"{format_counts[name]}"
        )

    print()

    print(
        "Human support distribution:"
    )

    for name in [
        "supported",
        "unsupported",
        "uncertain",
    ]:
        print(
            f"  {name}: "
            f"{support_counts[name]}"
        )

    print()

    print(
        "Annotation priority distribution:"
    )

    for name in sorted(
        priority_counts
    ):
        print(
            f"  {name}: "
            f"{priority_counts[name]}"
        )

    print()

    print(
        "Dataset:",
        OUTPUT_DATASET,
    )

    print(
        "Manifest:",
        OUTPUT_MANIFEST,
    )


if __name__ == "__main__":
    main()