from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "review_batches/external_structural_review_batch_05_v1.csv"
)


DECISIONS = {
    "EXT-POOL-V1-081": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-082": (
        "relational",
        "conditional_relation",
        "Raising a ValueError is explicitly conditioned on "
        "the string matching both a column name and an "
        "index level name.",
    ),
    "EXT-POOL-V1-083": (
        "relational",
        "temporal_relation",
        "The change to the columns Index name field is "
        "explicitly situated after the groupby operation.",
    ),
    "EXT-POOL-V1-084": (
        "atomic",
        "",
        "Single proposition about the result of an "
        "aggregation being treated as a scalar value.",
    ),
    "EXT-POOL-V1-085": (
        "non_propositional",
        "",
        "Imperative instruction fragment.",
    ),
    "EXT-POOL-V1-086": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-087": (
        "atomic",
        "",
        "Single proposition about pandas allowing multiple "
        "lambda functions.",
    ),
    "EXT-POOL-V1-088": (
        "compound",
        "",
        "Two independently meaningful propositions: "
        "group_keys can control inclusion of grouped columns "
        "in the indices, and group_keys defaults to True.",
    ),
    "EXT-POOL-V1-089": (
        "atomic",
        "",
        "Single proposition describing scikit-learn and the "
        "learning paradigms it supports.",
    ),
    "EXT-POOL-V1-090": (
        "compound",
        "",
        "Two independently checkable facts: transformer "
        "objects lack predict and instead provide transform, "
        "which outputs a transformed sample matrix.",
    ),
    "EXT-POOL-V1-091": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-092": (
        "relational",
        "causal_relation",
        "Using a pipeline is stated to prevent data leakage.",
    ),
    "EXT-POOL-V1-093": (
        "compound",
        "",
        "Two independently meaningful propositions: "
        "train_test_split divides data into train and test "
        "sets, and scikit-learn provides additional model "
        "evaluation tools.",
    ),
    "EXT-POOL-V1-094": (
        "atomic",
        "",
        "Single proposition about automatically finding "
        "parameter combinations through cross-validation.",
    ),
    "EXT-POOL-V1-095": (
        "non_propositional",
        "",
        "Navigation or read-more instruction.",
    ),
    "EXT-POOL-V1-096": (
        "relational",
        "conditional_relation",
        "Breaking the independence assumption is explicitly "
        "conditioned on preprocessing the whole dataset "
        "without a pipeline before cross-validation.",
    ),
    "EXT-POOL-V1-097": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-098": (
        "atomic",
        "",
        "Single proposition about associating an event "
        "listener in order to react to an event.",
    ),
    "EXT-POOL-V1-099": (
        "non_propositional",
        "",
        "Normative recommendation rather than an "
        "independently checkable factual proposition.",
    ),
    "EXT-POOL-V1-100": (
        "relational",
        "conditional_relation",
        "The described developer behavior is conditioned on "
        "the user having submitted the data incorrectly.",
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
            "Some Batch 05 rows remain unreviewed."
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

    print("Structural Review Batch 05 v1")
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