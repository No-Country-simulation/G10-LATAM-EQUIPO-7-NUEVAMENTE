from __future__ import annotations

from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_compound_expansion_pool_v1.csv"
)


DECISIONS = {
    "EXT-COMP-V1-001": (
        "atomic",
        "",
        "Single proposition about the server type supported "
        "by remote MCP.",
    ),
    "EXT-COMP-V1-002": (
        "relational",
        "negation_or_absence",
        "The essential meaning is expressed through the "
        "negation that text generation before tool calls "
        "is not required.",
    ),
    "EXT-COMP-V1-003": (
        "non_propositional",
        "",
        "Procedural instruction.",
    ),
    "EXT-COMP-V1-004": (
        "non_propositional",
        "",
        "Imperative instruction fragment.",
    ),
    "EXT-COMP-V1-005": (
        "non_propositional",
        "",
        "Nominal list of features rather than a complete "
        "independently checkable proposition.",
    ),
    "EXT-COMP-V1-007": (
        "non_propositional",
        "",
        "Procedural instruction.",
    ),
    "EXT-COMP-V1-008": (
        "atomic",
        "",
        "Despite the discourse marker 'Nota que', the claim "
        "contains one complete factual proposition about the "
        "path parameter being declared as an integer.",
    ),
    "EXT-COMP-V1-009": (
        "relational",
        "causal_relation",
        "The claim links validation being performed with "
        "Pydantic to obtaining Pydantic's benefits using "
        "'así que'.",
    ),
    "EXT-COMP-V1-010": (
        "non_propositional",
        "",
        "Context-dependent statement because 'compararlo' "
        "refers to omitted preceding content.",
    ),
    "EXT-COMP-V1-011": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-COMP-V1-012": (
        "compound",
        "",
        "Two independently checkable propositions: a GET "
        "request body has undefined behavior in the "
        "specifications, and FastAPI nevertheless supports it.",
    ),
    "EXT-COMP-V1-013": (
        "compound",
        "",
        "Multiple independently meaningful facts describe "
        "the Kubernetes Master: its daemon composition, "
        "execution on one cluster node, and the name of "
        "that node.",
    ),
    "EXT-COMP-V1-014": (
        "non_propositional",
        "",
        "Section heading.",
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
            "Some Part 1 cases remain unreviewed."
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
        "Part 1 v1"
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
        "Only the first 13 hygiene-valid expansion "
        "cases were structurally adjudicated."
    )
    print(
        "No Claim Atomizer predictions were used."
    )


if __name__ == "__main__":
    main()