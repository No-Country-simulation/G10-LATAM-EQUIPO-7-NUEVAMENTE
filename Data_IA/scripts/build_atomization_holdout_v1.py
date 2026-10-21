"""Build Claim Atomization holdout v1.

Creates a fresh holdout set from the manually annotated
content-support claim ground truth.

Important:
- excludes every source claim used in atomization development v1;
- does not use Gemini outputs;
- does not use semantic-review results;
- does not use router decisions;
- selection is deterministic;
- this holdout is intended for atomization evaluation, not
  support-label balance.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(
    "data/evaluation"
)

SOURCE_GT = (
    BASE_DIR
    / "calibration_v1"
    / "results"
    / "content_support_claim_ground_truth_v1.csv"
)

DEV_DATASET = (
    BASE_DIR
    / "atomization_v1"
    / "atomization_dataset_v1.csv"
)

HOLDOUT_DIR = (
    BASE_DIR
    / "atomization_v1"
    / "holdout_v1"
)

OUTPUT_DATASET = (
    HOLDOUT_DIR
    / "atomization_holdout_dataset_v1.csv"
)

OUTPUT_MANIFEST = (
    HOLDOUT_DIR
    / "atomization_holdout_manifest_v1.json"
)


HOLDOUT_SIZE = 20

SELECTION_SEED = (
    "claim-atomization-holdout-v1"
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


def source_key(
    calibration_id: str,
    claim_id: str,
) -> str:
    return (
        f"{calibration_id}|{claim_id}"
    )


def deterministic_rank(
    row: dict[str, str],
) -> str:
    raw = (
        f"{SELECTION_SEED}|"
        f"{row['calibration_id']}|"
        f"{row['claim_id']}|"
        f"{row['claim_text']}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def select_round_robin_by_format(
    rows: list[dict[str, str]],
    target: int,
) -> list[dict[str, str]]:
    by_format: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in rows:
        by_format[
            row["format"]
        ].append(row)

    for format_rows in (
        by_format.values()
    ):
        format_rows.sort(
            key=deterministic_rank
        )

    formats = sorted(
        by_format
    )

    selected: list[
        dict[str, str]
    ] = []

    indexes = {
        format_name: 0
        for format_name in formats
    }

    while (
        len(selected) < target
    ):
        added_this_round = False

        for format_name in formats:
            if (
                len(selected)
                >= target
            ):
                break

            index = indexes[
                format_name
            ]

            candidates = by_format[
                format_name
            ]

            if index >= len(
                candidates
            ):
                continue

            selected.append(
                candidates[index]
            )

            indexes[
                format_name
            ] += 1

            added_this_round = True

        if not added_this_round:
            break

    return selected


def main() -> None:
    source_rows = load_csv(
        SOURCE_GT
    )

    dev_rows = load_csv(
        DEV_DATASET
    )

    if len(source_rows) != 59:
        raise RuntimeError(
            "Expected 59 source claims, "
            f"found {len(source_rows)}."
        )

    dev_keys = {
        source_key(
            row[
                "calibration_id"
            ],
            row[
                "source_claim_id"
            ],
        )
        for row in dev_rows
    }

    source_keys = {
        source_key(
            row[
                "calibration_id"
            ],
            row[
                "claim_id"
            ],
        )
        for row in source_rows
    }

    overlap = (
        source_keys
        & dev_keys
    )

    if len(overlap) != len(
        dev_rows
    ):
        raise RuntimeError(
            "Development overlap mismatch: "
            f"expected {len(dev_rows)}, "
            f"found {len(overlap)}."
        )

    candidates = [
        row
        for row in source_rows
        if source_key(
            row[
                "calibration_id"
            ],
            row[
                "claim_id"
            ],
        )
        not in dev_keys
    ]

    expected_candidates = (
        len(source_rows)
        - len(dev_rows)
    )

    if (
        len(candidates)
        != expected_candidates
    ):
        raise RuntimeError(
            "Candidate count mismatch: "
            f"expected "
            f"{expected_candidates}, "
            f"found {len(candidates)}."
        )

    # ----------------------------------------------------------
    # Selection policy
    #
    # Include uncertain examples first because there are only a
    # few and they represent useful ambiguity.
    #
    # The remaining slots are selected deterministically across
    # formats.
    #
    # Unsupported examples are included automatically if any
    # remain after excluding development.
    # ----------------------------------------------------------

    uncertain = [
        row
        for row in candidates
        if row[
            "human_support_label"
        ]
        == "uncertain"
    ]

    unsupported = [
        row
        for row in candidates
        if row[
            "human_support_label"
        ]
        == "unsupported"
    ]

    supported = [
        row
        for row in candidates
        if row[
            "human_support_label"
        ]
        == "supported"
    ]

    uncertain.sort(
        key=deterministic_rank
    )

    unsupported.sort(
        key=deterministic_rank
    )

    selected: list[
        dict[str, str]
    ] = []

    # Keep all remaining uncertain claims.
    selected.extend(
        uncertain
    )

    # Keep all remaining unsupported claims if any exist.
    for row in unsupported:
        if (
            len(selected)
            >= HOLDOUT_SIZE
        ):
            break

        selected.append(
            row
        )

    remaining_slots = (
        HOLDOUT_SIZE
        - len(selected)
    )

    if remaining_slots > 0:
        selected.extend(
            select_round_robin_by_format(
                supported,
                remaining_slots,
            )
        )

    if (
        len(selected)
        != HOLDOUT_SIZE
    ):
        raise RuntimeError(
            "Could not construct "
            f"{HOLDOUT_SIZE}-claim "
            "holdout."
        )

    selected_keys = {
        source_key(
            row[
                "calibration_id"
            ],
            row[
                "claim_id"
            ],
        )
        for row in selected
    }

    accidental_overlap = (
        selected_keys
        & dev_keys
    )

    if accidental_overlap:
        raise RuntimeError(
            "Development leakage detected."
        )

    HOLDOUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_rows = []

    for index, row in enumerate(
        selected,
        start=1,
    ):
        output_rows.append(
            {
                "holdout_id": (
                    f"HOLDOUT-V1-"
                    f"{index:03d}"
                ),
                "calibration_id": (
                    row[
                        "calibration_id"
                    ]
                ),
                "source_claim_id": (
                    row[
                        "claim_id"
                    ]
                ),
                "format": (
                    row["format"]
                ),
                "source_claim_text": (
                    row[
                        "claim_text"
                    ]
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
                    "fresh_holdout_v1"
                ),
            }
        )

    fieldnames = [
        "holdout_id",
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

    support_counts = Counter(
        row[
            "human_support_label"
        ]
        for row in output_rows
    )

    format_counts = Counter(
        row["format"]
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
            "atomization-holdout-v1"
        ),
        "selection_seed": (
            SELECTION_SEED
        ),
        "source_ground_truth": (
            str(SOURCE_GT)
        ),
        "development_dataset": (
            str(DEV_DATASET)
        ),
        "source_claim_count": (
            len(source_rows)
        ),
        "development_claim_count": (
            len(dev_rows)
        ),
        "development_overlap_verified": (
            len(overlap)
        ),
        "fresh_candidate_count": (
            len(candidates)
        ),
        "holdout_claim_count": (
            len(output_rows)
        ),
        "development_holdout_overlap": (
            len(
                selected_keys
                & dev_keys
            )
        ),
        "human_support_distribution": (
            dict(
                support_counts
            )
        ),
        "format_distribution": (
            dict(
                format_counts
            )
        ),
        "annotation_priority_distribution": (
            dict(
                priority_counts
            )
        ),
        "selection_policy": (
            "all remaining uncertain, "
            "all remaining unsupported "
            "if available, then "
            "deterministic round-robin "
            "supported sampling by format"
        ),
        "gemini_used_for_selection": (
            False
        ),
        "model_results_used_for_selection": (
            False
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

    print("=" * 80)
    print(
        "CLAIM ATOMIZATION HOLDOUT V1"
    )
    print("=" * 80)

    print(
        "Source claims:",
        len(source_rows),
    )

    print(
        "Development claims:",
        len(dev_rows),
    )

    print(
        "Verified development overlap:",
        len(overlap),
    )

    print(
        "Fresh candidates:",
        len(candidates),
    )

    print(
        "Selected holdout:",
        len(output_rows),
    )

    print(
        "Development/holdout overlap:",
        len(
            selected_keys
            & dev_keys
        ),
    )

    print()

    print(
        "Human support distribution:"
    )

    for label in [
        "supported",
        "unsupported",
        "uncertain",
    ]:
        print(
            f"  {label}: "
            f"{support_counts[label]}"
        )

    print()

    print(
        "Format distribution:"
    )

    for format_name in sorted(
        format_counts
    ):
        print(
            f"  {format_name}: "
            f"{format_counts[format_name]}"
        )

    print()

    print(
        "Annotation priority distribution:"
    )

    for priority in sorted(
        priority_counts
    ):
        print(
            f"  {priority}: "
            f"{priority_counts[priority]}"
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