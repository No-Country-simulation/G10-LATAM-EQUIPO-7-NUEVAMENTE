from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "review_batches/external_structural_review_batch_03_v1.csv"
)


DECISIONS = {
    "EXT-POOL-V1-041": (
        "relational",
        "temporal_relation",
        "The claim explicitly states that rigorous testing "
        "occurred before any implementation.",
    ),
    "EXT-POOL-V1-042": (
        "non_propositional",
        "",
        "Context-dependent statement because 'esto' refers "
        "to omitted preceding content.",
    ),
    "EXT-POOL-V1-043": (
        "relational",
        "conditional_relation",
        "Using the Pydantic PyCharm Plugin is explicitly "
        "conditioned on using PyCharm.",
    ),
    "EXT-POOL-V1-044": (
        "non_propositional",
        "",
        "Incomplete introduction to a following list.",
    ),
    "EXT-POOL-V1-045": (
        "non_propositional",
        "",
        "Label or fragment rather than a complete proposition.",
    ),
    "EXT-POOL-V1-046": (
        "atomic",
        "",
        "Single proposition about declaring path parameters "
        "and request body parameters at the same time.",
    ),
    "EXT-POOL-V1-047": (
        "compound",
        "",
        "Two independently meaningful propositions: FastAPI "
        "recognizes each parameter and obtains its data from "
        "the correct location.",
    ),
    "EXT-POOL-V1-048": (
        "relational",
        "conditional_relation",
        "Interpretation as a query parameter depends on the "
        "parameter being a singular type.",
    ),
    "EXT-POOL-V1-049": (
        "atomic",
        "",
        "Single proposition about what the concepts section "
        "helps the reader understand.",
    ),
    "EXT-POOL-V1-050": (
        "non_propositional",
        "",
        "Context-dependent statement with an omitted subject "
        "from the preceding sentence.",
    ),
    "EXT-POOL-V1-051": (
        "atomic",
        "",
        "Single proposition describing the composition of "
        "the Kubernetes Control Plane.",
    ),
    "EXT-POOL-V1-052": (
        "atomic",
        "",
        "Single proposition about Kubernetes abstractions "
        "being represented by API objects.",
    ),
    "EXT-POOL-V1-053": (
        "non_propositional",
        "",
        "Navigation or read-more instruction.",
    ),
    "EXT-POOL-V1-054": (
        "non_propositional",
        "",
        "Introduction to a following list.",
    ),
    "EXT-POOL-V1-055": (
        "compound",
        "",
        "Two independently meaningful propositions: "
        "controllers are based on basic objects and provide "
        "additional functionality.",
    ),
    "EXT-POOL-V1-056": (
        "atomic",
        "",
        "Single proposition about how Control Plane "
        "components govern cluster communication.",
    ),
    "EXT-POOL-V1-057": (
        "atomic",
        "",
        "Single proposition describing a Kubernetes "
        "Deployment object.",
    ),
    "EXT-POOL-V1-058": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-059": (
        "relational",
        "conditional_relation",
        "Providing the object spec and basic information is "
        "required when creating a Kubernetes object.",
    ),
    "EXT-POOL-V1-060": (
        "relational",
        "conditional_relation",
        "Including the information as JSON is required when "
        "using the Kubernetes API to create the object.",
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
            "Some Batch 03 rows remain unreviewed."
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

    print("Structural Review Batch 03 v1")
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