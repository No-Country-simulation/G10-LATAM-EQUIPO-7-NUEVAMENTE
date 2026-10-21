from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "review_batches/external_structural_review_batch_02_v1.csv"
)


DECISIONS = {
    "EXT-POOL-V1-021": (
        "relational",
        "causal_relation",
        "Streaming structured outputs enables processing "
        "the response while it is still being generated.",
    ),
    "EXT-POOL-V1-022": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-023": (
        "non_propositional",
        "",
        "Imperative instruction associated with a label.",
    ),
    "EXT-POOL-V1-024": (
        "relational",
        "conditional_relation",
        "Possible schema rejection depends on schema size "
        "or nesting depth.",
    ),
    "EXT-POOL-V1-025": (
        "non_propositional",
        "",
        "Procedural instruction.",
    ),
    "EXT-POOL-V1-026": (
        "atomic",
        "",
        "Single proposition about configuring the app "
        "location in pyproject.toml.",
    ),
    "EXT-POOL-V1-027": (
        "relational",
        "conditional_relation",
        "Opening the browser is explicitly conditioned on "
        "the user not already being signed in.",
    ),
    "EXT-POOL-V1-028": (
        "non_propositional",
        "",
        "Procedural step.",
    ),
    "EXT-POOL-V1-029": (
        "atomic",
        "",
        "Single proposition describing what the decorator "
        "tells FastAPI about the function.",
    ),
    "EXT-POOL-V1-030": (
        "non_propositional",
        "",
        "Context-dependent statement with an omitted referent.",
    ),
    "EXT-POOL-V1-031": (
        "atomic",
        "",
        "Single proposition about supported return value types.",
    ),
    "EXT-POOL-V1-032": (
        "atomic",
        "",
        "Single proposition about automatic JSON conversion.",
    ),
    "EXT-POOL-V1-033": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-034": (
        "atomic",
        "",
        "Single proposition about FastAPI providing data "
        "validation from the Python type declaration.",
    ),
    "EXT-POOL-V1-035": (
        "non_propositional",
        "",
        "Context-dependent illustrative instruction.",
    ),
    "EXT-POOL-V1-036": (
        "relational",
        "negation_or_absence",
        "The inability to redefine a path operation is "
        "essentially expressed through negation.",
    ),
    "EXT-POOL-V1-037": (
        "relational",
        "conditional_relation",
        "Using a Python Enum is explicitly conditioned on "
        "wanting predefined valid path parameter values.",
    ),
    "EXT-POOL-V1-038": (
        "atomic",
        "",
        "Single proposition about returning enum members "
        "from a path operation.",
    ),
    "EXT-POOL-V1-039": (
        "non_propositional",
        "",
        "Introduction to a following JSON response example.",
    ),
    "EXT-POOL-V1-040": (
        "non_propositional",
        "",
        "Context-dependent statement because 'hacerlo' "
        "refers to omitted preceding content.",
    ),
}


def main() -> None:
    df = pd.read_csv(
        PATH,
        keep_default_na=False,
    )

    expected_ids = set(DECISIONS)
    actual_ids = set(df["external_review_id"])

    if actual_ids != expected_ids:
        missing = expected_ids - actual_ids
        unexpected = actual_ids - expected_ids

        raise ValueError(
            "Batch IDs do not match decisions. "
            f"Missing={sorted(missing)}, "
            f"Unexpected={sorted(unexpected)}"
        )

    for review_id, (
        bucket,
        subtype,
        notes,
    ) in DECISIONS.items():
        mask = df["external_review_id"] == review_id

        df.loc[mask, "target_bucket"] = bucket
        df.loc[mask, "relation_subtype"] = subtype
        df.loc[mask, "review_status"] = "reviewed"
        df.loc[mask, "review_notes"] = notes

    if (df["review_status"] != "reviewed").any():
        raise ValueError(
            "Some Batch 02 rows remain unreviewed."
        )

    if (
        (df["target_bucket"] == "relational")
        & (df["relation_subtype"] == "")
    ).any():
        raise ValueError(
            "Relational claims must have a relation subtype."
        )

    if (
        (df["target_bucket"] != "relational")
        & (df["relation_subtype"] != "")
    ).any():
        raise ValueError(
            "Only relational claims may have relation_subtype."
        )

    df.to_csv(
        PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("Structural Review Batch 02 v1")
    print("=============================")

    print()
    print("Target buckets:")
    print(
        df["target_bucket"]
        .value_counts()
        .to_string()
    )

    print()
    print("Relation subtypes:")

    relational = df[
        df["target_bucket"] == "relational"
    ]

    if relational.empty:
        print("None")
    else:
        print(
            relational["relation_subtype"]
            .value_counts()
            .to_string()
        )

    print()
    print(
        "Reviewed:",
        int((df["review_status"] == "reviewed").sum()),
    )

    print(f"Updated: {PATH}")


if __name__ == "__main__":
    main()