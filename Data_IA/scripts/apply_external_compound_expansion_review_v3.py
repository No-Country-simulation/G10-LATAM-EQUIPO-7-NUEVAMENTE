from __future__ import annotations

from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_compound_expansion_pool_v3.csv"
)


DECISIONS = {
    "EXT-COMP3-V1-001": (
        "non_propositional",
        "",
        "Imperative instruction rather than an independently "
        "checkable proposition.",
    ),
    "EXT-COMP3-V1-002": (
        "compound",
        "",
        "Two independently checkable propositions are stated: "
        "minLength and maxLength are not applied during "
        "constrained decoding, and the server ignores them.",
    ),
    "EXT-COMP3-V1-003": (
        "non_propositional",
        "",
        "Incomplete documentation fragment.",
    ),
    "EXT-COMP3-V1-004": (
        "atomic",
        "",
        "Single proposition about declaring the type of a "
        "path parameter using standard Python type annotations.",
    ),
    "EXT-COMP3-V1-005": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-COMP3-V1-006": (
        "atomic",
        "",
        "Single proposition about Kubernetes Labels allowing "
        "users to organize resources.",
    ),
    "EXT-COMP3-V1-007": (
        "non_propositional",
        "",
        "Incomplete introduction to a following matplotlib "
        "API example.",
    ),
    "EXT-COMP3-V1-009": (
        "non_propositional",
        "",
        "Context-dependent statement because 'al hacerlo' "
        "refers to omitted preceding content.",
    ),
    "EXT-COMP3-V1-010": (
        "compound",
        "",
        "Multiple independently meaningful DOM API capabilities "
        "are stated: creating, deleting, and changing HTML, "
        "and dynamically applying styles.",
    ),
}


def main() -> None:
    df = pd.read_csv(
        PATH,
        keep_default_na=False,
    )

    valid = df[
        df["hygiene_status"].isin(
            {"keep", "keep_cleaned"}
        )
    ].copy()

    expected_ids = set(DECISIONS)
    actual_ids = set(valid["expansion_id"])

    if actual_ids != expected_ids:
        raise ValueError(
            "Valid candidate IDs do not match decisions. "
            f"Missing={sorted(expected_ids - actual_ids)}, "
            f"Unexpected={sorted(actual_ids - expected_ids)}"
        )

    for expansion_id, (
        bucket,
        subtype,
        notes,
    ) in DECISIONS.items():
        mask = (
            df["expansion_id"] == expansion_id
        )

        df.loc[
            mask,
            "target_bucket",
        ] = bucket

        df.loc[
            mask,
            "relation_subtype",
        ] = subtype

        df.loc[
            mask,
            "review_status",
        ] = "reviewed"

        df.loc[
            mask,
            "review_notes",
        ] = notes

    reviewed = df[
        df["hygiene_status"].isin(
            {"keep", "keep_cleaned"}
        )
    ].copy()

    if (
        reviewed["review_status"]
        != "reviewed"
    ).any():
        raise ValueError(
            "Some hygiene-valid v3 candidates remain unreviewed."
        )

    relational = (
        reviewed["target_bucket"]
        == "relational"
    )

    if (
        relational
        & (
            reviewed["relation_subtype"]
            == ""
        )
    ).any():
        raise ValueError(
            "Relational claims must have a subtype."
        )

    if (
        (~relational)
        & (
            reviewed["relation_subtype"]
            != ""
        )
    ).any():
        raise ValueError(
            "Non-relational claims must not have a subtype."
        )

    df.to_csv(
        PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "Compound Expansion Structural Review v3"
    )
    print(
        "======================================="
    )

    print()
    print("Buckets:")
    print(
        reviewed["target_bucket"]
        .value_counts()
        .to_string()
    )

    print()
    print(
        "Reviewed:",
        len(reviewed),
    )

    print(
        "Compound claims:",
        int(
            (
                reviewed["target_bucket"]
                == "compound"
            ).sum()
        ),
    )

    print()
    print(f"Updated: {PATH}")

    print()
    print("IMPORTANT:")
    print(
        "No Claim Atomizer predictions were used."
    )


if __name__ == "__main__":
    main()