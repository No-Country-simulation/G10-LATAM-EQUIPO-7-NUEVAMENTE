from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "review_batches/external_structural_review_batch_04_v1.csv"
)


DECISIONS = {
    "EXT-POOL-V1-061": (
        "non_propositional",
        "",
        "Field label followed by a nominal description.",
    ),
    "EXT-POOL-V1-062": (
        "non_propositional",
        "",
        "Field label followed by a descriptive fragment.",
    ),
    "EXT-POOL-V1-063": (
        "atomic",
        "",
        "Single proposition about what the StatefulSet "
        "template describes.",
    ),
    "EXT-POOL-V1-064": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-065": (
        "non_propositional",
        "",
        "Context-dependent statement with an omitted referent.",
    ),
    "EXT-POOL-V1-066": (
        "compound",
        "",
        "Two independently meaningful effects are stated: "
        "facilitating workflows and making administrative "
        "inspection of state easier.",
    ),
    "EXT-POOL-V1-067": (
        "atomic",
        "",
        "Single proposition about the Kubernetes Control "
        "Plane using the same APIs as developers and users.",
    ),
    "EXT-POOL-V1-068": (
        "relational",
        "negation_or_absence",
        "The claim's essential meaning is expressed through "
        "the negation that Kubernetes is not merely an "
        "orchestration system.",
    ),
    "EXT-POOL-V1-069": (
        "compound",
        "",
        "Two independently meaningful propositions: "
        "containers are easier to build than virtual "
        "machines, and their decoupling enables portability "
        "across clouds and operating system distributions.",
    ),
    "EXT-POOL-V1-070": (
        "relational",
        "causal_relation",
        "The claim explicitly explains why immutable images "
        "can be created at build time using 'ya que'.",
    ),
    "EXT-POOL-V1-071": (
        "relational",
        "causal_relation",
        "Generating a container image at build time is stated "
        "to enable a consistent environment from development "
        "through production.",
    ),
    "EXT-POOL-V1-072": (
        "atomic",
        "",
        "Single proposition about portability across multiple "
        "cloud, operating system, and infrastructure "
        "environments.",
    ),
    "EXT-POOL-V1-073": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-074": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-075": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-076": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-077": (
        "atomic",
        "",
        "Single proposition about operations generally "
        "excluding missing data.",
    ),
    "EXT-POOL-V1-078": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-079": (
        "non_propositional",
        "",
        "Navigation or read-more instruction.",
    ),
    "EXT-POOL-V1-080": (
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
            "Some Batch 04 rows remain unreviewed."
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

    print("Structural Review Batch 04 v1")
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