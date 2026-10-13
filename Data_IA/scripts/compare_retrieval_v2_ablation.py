from pathlib import Path
import json
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

GT_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "ground_truth_v2.csv"
)

BASELINE_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "results"
    / "retrieval_metrics_gt_v2.csv"
)

FILTERED_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "input"
    / "retrieval_results_agentes_v2.json"
)

UNFILTERED_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "input"
    / "retrieval_results_agentes_v2_unfiltered.json"
)


def parse_relevant_ids(value):
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    ]


def recall_at_k(relevant, retrieved, k):
    relevant = set(relevant)

    if not relevant:
        return 0.0

    return len(
        relevant.intersection(retrieved[:k])
    ) / len(relevant)


def precision_at_k(relevant, retrieved, k):
    return len(
        set(relevant).intersection(retrieved[:k])
    ) / k


def evaluate_batch(path, gt_by_case):
    with path.open("r", encoding="utf-8") as f:
        batch = json.load(f)

    assert len(batch) == 50

    rows = []

    for case in batch:
        case_id = case["case_id"]
        gt = gt_by_case[case_id]

        relevant = parse_relevant_ids(
            gt["relevant_chunk_ids"]
        )

        retrieved = [
            result["chunk_id"]
            for result in case.get("results", [])
        ]

        rows.append(
            {
                "case_id": case_id,
                "categoria": gt["categoria"],
                "recall_at_3": recall_at_k(
                    relevant, retrieved, 3
                ),
                "recall_at_5": recall_at_k(
                    relevant, retrieved, 5
                ),
                "precision_at_3": precision_at_k(
                    relevant, retrieved, 3
                ),
                "precision_at_5": precision_at_k(
                    relevant, retrieved, 5
                ),
            }
        )

    return pd.DataFrame(rows)


def summarize(df):
    return {
        "Recall@3": df["recall_at_3"].mean(),
        "Recall@5": df["recall_at_5"].mean(),
        "Precision@3": df["precision_at_3"].mean(),
        "Precision@5": df["precision_at_5"].mean(),
    }


def main():
    gt = pd.read_csv(
        GT_PATH,
        encoding="utf-8-sig",
    )

    gt_by_case = gt.set_index(
        "case_id"
    ).to_dict("index")

    filtered = evaluate_batch(
        FILTERED_PATH,
        gt_by_case,
    )

    unfiltered = evaluate_batch(
        UNFILTERED_PATH,
        gt_by_case,
    )

    baseline_df = pd.read_csv(
        BASELINE_PATH,
        encoding="utf-8-sig",
    )

    baseline_lookup = (
        baseline_df
        .set_index("metric")["mean"]
        .to_dict()
    )

    baseline = {
        "Recall@3": float(
            baseline_lookup["recall_at_3"]
        ),
        "Recall@5": float(
            baseline_lookup["recall_at_5"]
        ),
        "Precision@3": float(
            baseline_lookup["precision_at_3"]
        ),
        "Precision@5": float(
            baseline_lookup["precision_at_5"]
        ),
    }

    unfiltered_summary = summarize(
        unfiltered
    )

    filtered_summary = summarize(
        filtered
    )

    comparison = pd.DataFrame(
        {
            "V1 baseline": baseline,
            "V2 unfiltered": unfiltered_summary,
            "V2 filtered": filtered_summary,
        }
    )

    comparison[
        "delta_unfiltered_vs_v1"
    ] = (
        comparison["V2 unfiltered"]
        - comparison["V1 baseline"]
    )

    comparison[
        "delta_filter"
    ] = (
        comparison["V2 filtered"]
        - comparison["V2 unfiltered"]
    )

    print()
    print("=== ABLATION RETRIEVAL V2 ===")
    print()

    print(
        comparison.round(6).to_string()
    )

    print()
    print(
        "=== CASOS CON RECALL@5 = 0 ==="
    )

    print(
        "V2 unfiltered:",
        int(
            (
                unfiltered["recall_at_5"]
                == 0
            ).sum()
        ),
    )

    print(
        "V2 filtered:",
        int(
            (
                filtered["recall_at_5"]
                == 0
            ).sum()
        ),
    )

    print()
    print("=== POR CATEGORÍA ===")

    category = (
        unfiltered
        .groupby("categoria")[
            [
                "recall_at_3",
                "recall_at_5",
                "precision_at_3",
                "precision_at_5",
            ]
        ]
        .mean()
        .round(6)
    )

    print(category.to_string())


if __name__ == "__main__":
    main()