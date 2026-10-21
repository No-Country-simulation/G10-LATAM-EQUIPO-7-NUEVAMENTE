from __future__ import annotations

from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_compound_expansion_pool_v2.csv"
)


DECISIONS = {
    "EXT-COMP2-V1-001": (
        "atomic",
        "",
        "Single proposition stating that the process can be repeated several times.",
    ),
    "EXT-COMP2-V1-002": (
        "compound",
        "",
        "Two independently checkable properties are stated: "
        "the output block contains a valid JSON string and "
        "that JSON conforms exactly to the requested schema.",
    ),
    "EXT-COMP2-V1-003": (
        "non_propositional",
        "",
        "Incomplete introduction to a following list.",
    ),
    "EXT-COMP2-V1-004": (
        "non_propositional",
        "",
        "Context-dependent statement because 'verlo' refers "
        "to omitted preceding content.",
    ),
    "EXT-COMP2-V1-005": (
        "non_propositional",
        "",
        "Context-dependent statement because 'Este' refers "
        "to an omitted preceding entity.",
    ),
    "EXT-COMP2-V1-006": (
        "atomic",
        "",
        "Single complete definition of a response body.",
    ),
    "EXT-COMP2-V1-007": (
        "atomic",
        "",
        "Single proposition about Kubernetes providing a "
        "container-centered management environment.",
    ),
    "EXT-COMP2-V1-008": (
        "non_propositional",
        "",
        "Question used as a section heading.",
    ),
    "EXT-COMP2-V1-009": (
        "non_propositional",
        "",
        "Context-dependent fragment with an omitted referent.",
    ),
    "EXT-COMP2-V1-013": (
        "non_propositional",
        "",
        "Infinitive section heading.",
    ),
    "EXT-COMP2-V1-014": (
        "non_propositional",
        "",
        "Context-dependent statement because 'Esto' refers "
        "to omitted preceding content.",
    ),
    "EXT-COMP2-V1-015": (
        "atomic",
        "",
        "One independently checkable proposition states that "
        "the complete example can be viewed live; the appended "
        "imperative does not constitute a second factual proposition.",
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

        df.loc[mask, "target_bucket"] = bucket
        df.loc[mask, "relation_subtype"] = subtype
        df.loc[mask, "review_status"] = "reviewed"
        df.loc[mask, "review_notes"] = notes

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
            "Some hygiene-valid v2 candidates remain unreviewed."
        )

    relational = (
        reviewed["target_bucket"]
        == "relational"
    )

    if (
        relational
        & (reviewed["relation_subtype"] == "")
    ).any():
        raise ValueError(
            "Relational claims must have a subtype."
        )

    if (
        (~relational)
        & (reviewed["relation_subtype"] != "")
    ).any():
        raise ValueError(
            "Non-relational claims must not have a subtype."
        )

    df.to_csv(
        PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("Compound Expansion Structural Review v2")
    print("=======================================")

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

    print()
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