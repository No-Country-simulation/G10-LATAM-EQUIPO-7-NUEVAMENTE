from __future__ import annotations

from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_compound_expansion_pool_v1.csv"
)


DECISIONS = {
    "EXT-COMP-V1-015": (
        "relational",
        "temporal_relation",
        "The availability of server-side field validation "
        "is explicitly situated starting with Kubernetes v1.25.",
    ),
    "EXT-COMP-V1-016": (
        "non_propositional",
        "",
        "Question used as a section heading.",
    ),
    "EXT-COMP-V1-017": (
        "relational",
        "causal_relation",
        "Kubernetes orchestration is presented as enabling "
        "user workloads not to manage compute, networking, "
        "and storage themselves.",
    ),
    "EXT-COMP-V1-018": (
        "relational",
        "negation_or_absence",
        "The essential meaning is expressed through the "
        "negation that Kubernetes does not limit the types "
        "of applications it supports.",
    ),
    "EXT-COMP-V1-019": (
        "compound",
        "",
        "Two independently meaningful propositions: passing "
        "a list of column labels selects multiple columns, "
        "and this can be useful for obtaining or rearranging "
        "a subset.",
    ),
    "EXT-COMP-V1-023": (
        "atomic",
        "",
        "Single proposition about the following GroupBy "
        "methods acting as filtrations.",
    ),
    "EXT-COMP-V1-025": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-COMP-V1-026": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-COMP-V1-027": (
        "atomic",
        "",
        "Single proposition describing the purpose of the "
        "id attribute.",
    ),
    "EXT-COMP-V1-028": (
        "non_propositional",
        "",
        "Context-dependent statement because the referent "
        "of 'Es una característica' is omitted.",
    ),
    "EXT-COMP-V1-029": (
        "compound",
        "",
        "Two independently checkable propositions: "
        "interpreted code executes from top to bottom, and "
        "the execution result is returned immediately.",
    ),
    "EXT-COMP-V1-030": (
        "non_propositional",
        "",
        "Context-dependent statement because 'Ambos tipos' "
        "refers to omitted preceding content and includes "
        "an editorial remark.",
    ),
}


def main() -> None:
    df = pd.read_csv(
        PATH,
        keep_default_na=False,
    )

    for expansion_id, (
        bucket,
        subtype,
        notes,
    ) in DECISIONS.items():
        mask = (
            df["expansion_id"] == expansion_id
        )

        if int(mask.sum()) != 1:
            raise ValueError(
                f"Expected exactly one row for "
                f"{expansion_id}; found {int(mask.sum())}."
            )

        if (
            df.loc[mask, "hygiene_status"]
            .iloc[0]
            not in {"keep", "keep_cleaned"}
        ):
            raise ValueError(
                f"{expansion_id} is not hygiene-valid."
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
        df["expansion_id"].isin(
            DECISIONS
        )
    ].copy()

    if (
        reviewed["review_status"]
        != "reviewed"
    ).any():
        raise ValueError(
            "Some Part 2 cases remain unreviewed."
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
        "Compound Expansion Structural Review "
        "Part 2 v1"
    )
    print(
        "====================================="
    )

    print()
    print("Buckets:")
    print(
        reviewed["target_bucket"]
        .value_counts()
        .to_string()
    )

    print()
    print("Relation subtypes:")

    rel = reviewed[
        reviewed["target_bucket"]
        == "relational"
    ]

    if rel.empty:
        print("None")
    else:
        print(
            rel["relation_subtype"]
            .value_counts()
            .to_string()
        )

    print()
    print(
        "Reviewed:",
        len(reviewed),
    )

    print(f"Updated: {PATH}")

    print()
    print("IMPORTANT:")
    print(
        "All hygiene-valid expansion cases are now "
        "structurally adjudicated."
    )
    print(
        "No Claim Atomizer predictions were used."
    )


if __name__ == "__main__":
    main()