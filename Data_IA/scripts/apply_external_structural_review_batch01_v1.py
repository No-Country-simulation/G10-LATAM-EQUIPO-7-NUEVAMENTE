from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "review_batches/external_structural_review_batch_01_v1.csv"
)


DECISIONS = {
    "EXT-POOL-V1-001": (
        "compound",
        "",
        "Two independently meaningful propositions: "
        "what the example demonstrates and what that implies "
        "about external tool use.",
    ),
    "EXT-POOL-V1-002": (
        "non_propositional",
        "",
        "Procedural step heading.",
    ),
    "EXT-POOL-V1-003": (
        "non_propositional",
        "",
        "Section heading.",
    ),
    "EXT-POOL-V1-004": (
        "atomic",
        "",
        'Single proposition: type must be "function".',
    ),
    "EXT-POOL-V1-005": (
        "non_propositional",
        "",
        "Field label followed by a nominal description.",
    ),
    "EXT-POOL-V1-006": (
        "non_propositional",
        "",
        "Field label followed by a nominal description.",
    ),
    "EXT-POOL-V1-007": (
        "relational",
        "conditional_relation",
        "The instruction explicitly depends on the condition "
        "that the functions are independent.",
    ),
    "EXT-POOL-V1-008": (
        "non_propositional",
        "",
        "Instruction-like fragment associated with a heading.",
    ),
    "EXT-POOL-V1-009": (
        "atomic",
        "",
        "Single independently checkable proposition.",
    ),
    "EXT-POOL-V1-010": (
        "non_propositional",
        "",
        "Procedural instruction.",
    ),
    "EXT-POOL-V1-011": (
        "non_propositional",
        "",
        "Procedural instruction.",
    ),
    "EXT-POOL-V1-012": (
        "non_propositional",
        "",
        "Infinitive capability/list fragment.",
    ),
    "EXT-POOL-V1-013": (
        "non_propositional",
        "",
        "Infinitive capability/list fragment.",
    ),
    "EXT-POOL-V1-014": (
        "atomic",
        "",
        "Single proposition about Pydantic and Zod support.",
    ),
    "EXT-POOL-V1-015": (
        "non_propositional",
        "",
        "Navigation/read-more instruction.",
    ),
    "EXT-POOL-V1-016": (
        "non_propositional",
        "",
        "Label followed by a nominal description.",
    ),
    "EXT-POOL-V1-017": (
        "atomic",
        "",
        "Single proposition about configuring Gemini "
        "to follow a provided JSON schema.",
    ),
    "EXT-POOL-V1-018": (
        "non_propositional",
        "",
        "Incomplete introduction to a following list.",
    ),
    "EXT-POOL-V1-019": (
        "non_propositional",
        "",
        "Procedural recipe instruction.",
    ),
    "EXT-POOL-V1-020": (
        "relational",
        "causal_relation",
        "The claim states that using anyOf and enum enables "
        "the output structure to vary according to content.",
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
            "Some Batch 01 rows remain unreviewed."
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

    print("Structural Review Batch 01 v1")
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