from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "review_batches/external_structural_review_batch_06_v1.csv"
)


DECISIONS = {
    "EXT-POOL-V1-101": (
        "compound",
        "",
        "The claim describes the implemented submit-handler "
        "check and separately explains when the submit event fires.",
    ),
    "EXT-POOL-V1-102": (
        "compound",
        "",
        "Multiple independently meaningful propositions are "
        "expressed about listeners, emitters, on(), and once().",
    ),
    "EXT-POOL-V1-103": (
        "atomic",
        "",
        "Single proposition about the Node.js HTTP connect "
        "event documentation providing an example.",
    ),
    "EXT-POOL-V1-104": (
        "atomic",
        "",
        "Single proposition about using JavaScript and "
        "WebExtensions to create cross-browser extensions.",
    ),
    "EXT-POOL-V1-105": (
        "non_propositional",
        "",
        "Introductory fragment to a following list.",
    ),
    "EXT-POOL-V1-106": (
        "non_propositional",
        "",
        "Introduction to a following list of form attributes.",
    ),
    "EXT-POOL-V1-107": (
        "compound",
        "",
        "Two independently meaningful practices are stated: "
        "some people use p elements while others use different "
        "HTML elements.",
    ),
    "EXT-POOL-V1-108": (
        "atomic",
        "",
        "Single proposition about the text input type.",
    ),
    "EXT-POOL-V1-109": (
        "relational",
        "temporal_relation",
        "The screen reader reading the associated label is "
        "explicitly situated when the user reaches each control.",
    ),
    "EXT-POOL-V1-110": (
        "compound",
        "",
        "Two independently meaningful propositions: radio "
        "buttons and checkboxes are implemented similarly, and "
        "they support checked for preselection.",
    ),
    "EXT-POOL-V1-111": (
        "atomic",
        "",
        "Single proposition about grouping select options "
        "with optgroup.",
    ),
    "EXT-POOL-V1-112": (
        "compound",
        "",
        "Two independent propositions: rows specifies text-area "
        "height and cols specifies width.",
    ),
    "EXT-POOL-V1-113": (
        "atomic",
        "",
        "Single proposition defining APIs as reusable code "
        "blocks that enable difficult functionality.",
    ),
    "EXT-POOL-V1-114": (
        "non_propositional",
        "",
        "Conversational remark rather than an independently "
        "checkable factual proposition.",
    ),
    "EXT-POOL-V1-115": (
        "compound",
        "",
        "Multiple propositions describe separate execution "
        "environments, independent execution, and isolation "
        "between browser tabs.",
    ),
    "EXT-POOL-V1-116": (
        "relational",
        "comparative_relation",
        "The essential meaning contrasts server-side dynamic "
        "content generation with client-side JavaScript.",
    ),
    "EXT-POOL-V1-117": (
        "atomic",
        "",
        "Single proposition comparing JavaScript application "
        "to HTML with the general manner used by CSS.",
    ),
    "EXT-POOL-V1-118": (
        "relational",
        "comparative_relation",
        "The claim explicitly contrasts the HTML integration "
        "mechanisms used by CSS and JavaScript.",
    ),
    "EXT-POOL-V1-119": (
        "non_propositional",
        "",
        "Procedural instruction.",
    ),
    "EXT-POOL-V1-120": (
        "non_propositional",
        "",
        "Introduction to a following example.",
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
            "Some Batch 06 rows remain unreviewed."
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

    print("Structural Review Batch 06 v1")
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