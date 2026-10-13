from pathlib import Path
import sys
import json
import re
import hashlib

import pandas as pd
from rank_bm25 import BM25Okapi


# ============================================================
# ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.vector_store import VectorStore
from agentes.rag.pipeline import ingest_ground_truth_v1


# ============================================================
# PATHS
# ============================================================

GROUND_TRUTH_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "ground_truth_v2.csv"
)

CHUNKS_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "chunks_v1.csv"
)

OUTPUT_DIR = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "results"
    / "retrieval_v2_ablation"
    / "weighted_rrf_ablation"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# OUTPUT FILES
# ============================================================

GLOBAL_METRICS_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_global_metrics.csv"
)

CASE_COMPARISON_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_case_comparison.csv"
)

CATEGORY_METRICS_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_category_metrics.csv"
)

CHANGED_CASES_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_changed_cases.csv"
)

MANIFEST_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_manifest.json"
)


# ============================================================
# CHROMA
# ============================================================

CHROMA_PATH = (
    ROOT
    / ".benchmark_chroma_v2_weighted_rrf_ablation"
)

COLLECTION_NAME = (
    "benchmark_retrieval_v2_weighted_rrf_ablation"
)


# ============================================================
# CONFIG
# ============================================================

TOP_K = 5
CANDIDATE_K = TOP_K * 3
RRF_K = 60


WEIGHT_CONFIGS = {
    "RRF 50/50": {
        "vector_weight": 0.50,
        "bm25_weight": 0.50,
    },
    "RRF 60/40": {
        "vector_weight": 0.60,
        "bm25_weight": 0.40,
    },
    "RRF 70/30": {
        "vector_weight": 0.70,
        "bm25_weight": 0.30,
    },
    "RRF 80/20": {
        "vector_weight": 0.80,
        "bm25_weight": 0.20,
    },
}


# ============================================================
# HELPERS
# ============================================================

def parse_relevant_ids(value):
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    ]


def tokenize(text):
    return re.findall(
        r"\w+",
        str(text).lower(),
    )


def recall_at_k(
    relevant,
    retrieved,
    k,
):
    relevant_set = set(relevant)

    if not relevant_set:
        return 0.0

    return (
        len(
            relevant_set.intersection(
                retrieved[:k]
            )
        )
        / len(relevant_set)
    )


def precision_at_k(
    relevant,
    retrieved,
    k,
):
    if k <= 0:
        return 0.0

    return (
        len(
            set(relevant).intersection(
                retrieved[:k]
            )
        )
        / k
    )


def sha256_file(path):
    hasher = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(65536),
            b"",
        ):
            hasher.update(block)

    return hasher.hexdigest()


# ============================================================
# GENERAR RANKINGS BASE
# ============================================================

def build_base_rankings(
    vector_store,
    query,
    document_id,
):
    """
    Genera los rankings vectorial y BM25
    usados luego por Weighted RRF.
    """

    where_clause = {
        "document_id": document_id
    }

    # ========================================================
    # 1. VECTOR SEARCH
    # ========================================================

    query_embedding = (
        vector_store
        .embedding_service
        .embed_query(query)
    )

    vector_data = (
        vector_store
        .collection
        .query(
            query_embeddings=[
                query_embedding
            ],
            n_results=CANDIDATE_K,
            where=where_clause,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )
    )

    vector_results = []

    if (
        vector_data
        and vector_data["ids"]
        and vector_data["ids"][0]
    ):
        for rank, chunk_id in enumerate(
            vector_data["ids"][0],
            start=1,
        ):
            metadata = (
                vector_data[
                    "metadatas"
                ][0][rank - 1]
                or {}
            )

            vector_results.append(
                {
                    "rank": rank,
                    "chunk_id": chunk_id,
                    "document_id": (
                        metadata.get(
                            "document_id"
                        )
                    ),
                    "text": (
                        vector_data[
                            "documents"
                        ][0][rank - 1]
                    ),
                    "metadata": metadata,
                    "distance": float(
                        vector_data[
                            "distances"
                        ][0][rank - 1]
                    ),
                }
            )

    # ========================================================
    # 2. BM25
    # ========================================================

    all_filtered_data = (
        vector_store
        .collection
        .get(
            where=where_clause,
            include=[
                "documents",
                "metadatas",
            ],
        )
    )

    bm25_results = []

    if (
        all_filtered_data
        and all_filtered_data["documents"]
    ):
        documents = (
            all_filtered_data[
                "documents"
            ]
        )

        tokenized_corpus = [
            tokenize(doc)
            for doc in documents
        ]

        bm25 = BM25Okapi(
            tokenized_corpus
        )

        query_tokens = tokenize(
            query
        )

        scores = bm25.get_scores(
            query_tokens
        )

        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:CANDIDATE_K]

        bm25_rank = 0

        for i in top_indices:
            if scores[i] <= 0:
                continue

            bm25_rank += 1

            metadata = (
                all_filtered_data[
                    "metadatas"
                ][i]
                or {}
            )

            bm25_results.append(
                {
                    "rank": bm25_rank,
                    "chunk_id": (
                        all_filtered_data[
                            "ids"
                        ][i]
                    ),
                    "document_id": (
                        metadata.get(
                            "document_id"
                        )
                    ),
                    "text": documents[i],
                    "metadata": metadata,
                    "bm25_score": float(
                        scores[i]
                    ),
                }
            )

    return (
        vector_results,
        bm25_results,
    )


# ============================================================
# WEIGHTED RRF
# ============================================================

def weighted_rrf(
    vector_results,
    bm25_results,
    vector_weight,
    bm25_weight,
):
    """
    Weighted Reciprocal Rank Fusion:

    score =
        vector_weight / (RRF_K + vector_rank)
        +
        bm25_weight / (RRF_K + bm25_rank)

    Si un chunk solo aparece en una señal,
    únicamente recibe la contribución de esa señal.
    """

    fused = {}

    # --------------------------------------------------------
    # Vector contribution
    # --------------------------------------------------------

    for row in vector_results:
        chunk_id = row[
            "chunk_id"
        ]

        rank = row[
            "rank"
        ]

        if chunk_id not in fused:
            fused[
                chunk_id
            ] = {
                "chunk_id": chunk_id,
                "document_id": (
                    row[
                        "document_id"
                    ]
                ),
                "text": row[
                    "text"
                ],
                "metadata": (
                    row[
                        "metadata"
                    ]
                ),
                "vector_rank": None,
                "bm25_rank": None,
                "vector_contribution": 0.0,
                "bm25_contribution": 0.0,
                "weighted_rrf_score": 0.0,
            }

        contribution = (
            vector_weight
            / (
                RRF_K
                + rank
            )
        )

        fused[
            chunk_id
        ][
            "vector_rank"
        ] = rank

        fused[
            chunk_id
        ][
            "vector_contribution"
        ] = contribution

        fused[
            chunk_id
        ][
            "weighted_rrf_score"
        ] += contribution

    # --------------------------------------------------------
    # BM25 contribution
    # --------------------------------------------------------

    for row in bm25_results:
        chunk_id = row[
            "chunk_id"
        ]

        rank = row[
            "rank"
        ]

        if chunk_id not in fused:
            fused[
                chunk_id
            ] = {
                "chunk_id": chunk_id,
                "document_id": (
                    row[
                        "document_id"
                    ]
                ),
                "text": row[
                    "text"
                ],
                "metadata": (
                    row[
                        "metadata"
                    ]
                ),
                "vector_rank": None,
                "bm25_rank": None,
                "vector_contribution": 0.0,
                "bm25_contribution": 0.0,
                "weighted_rrf_score": 0.0,
            }

        contribution = (
            bm25_weight
            / (
                RRF_K
                + rank
            )
        )

        fused[
            chunk_id
        ][
            "bm25_rank"
        ] = rank

        fused[
            chunk_id
        ][
            "bm25_contribution"
        ] = contribution

        fused[
            chunk_id
        ][
            "weighted_rrf_score"
        ] += contribution

    ranked = sorted(
        fused.values(),
        key=lambda x: x[
            "weighted_rrf_score"
        ],
        reverse=True,
    )

    for rank, row in enumerate(
        ranked,
        start=1,
    ):
        row["rank"] = rank

    return ranked


# ============================================================
# TOP-K FORMAT
# ============================================================

def format_top_k(
    ranked_results,
):
    output = []

    for rank, row in enumerate(
        ranked_results[:TOP_K],
        start=1,
    ):
        output.append(
            {
                "rank": rank,
                "chunk_id": (
                    row[
                        "chunk_id"
                    ]
                ),
                "document_id": (
                    row[
                        "document_id"
                    ]
                ),
                "score": float(
                    row[
                        "weighted_rrf_score"
                    ]
                ),
                "weighted_rrf_score": float(
                    row[
                        "weighted_rrf_score"
                    ]
                ),
                "vector_rank": (
                    row[
                        "vector_rank"
                    ]
                ),
                "bm25_rank": (
                    row[
                        "bm25_rank"
                    ]
                ),
                "vector_contribution": float(
                    row[
                        "vector_contribution"
                    ]
                ),
                "bm25_contribution": float(
                    row[
                        "bm25_contribution"
                    ]
                ),
                "text": (
                    row[
                        "text"
                    ]
                ),
                "metadata": (
                    row[
                        "metadata"
                    ]
                ),
            }
        )

    return output


# ============================================================
# EVALUATION
# ============================================================

def evaluate_condition(
    batch,
    ground_truth_df,
    condition,
):
    gt_by_case = (
        ground_truth_df
        .set_index("case_id")
        .to_dict("index")
    )

    rows = []

    for case in batch:
        case_id = (
            case[
                "case_id"
            ]
        )

        gt = (
            gt_by_case[
                case_id
            ]
        )

        relevant = (
            parse_relevant_ids(
                gt[
                    "relevant_chunk_ids"
                ]
            )
        )

        retrieved = [
            result[
                "chunk_id"
            ]
            for result
            in case[
                "results"
            ]
        ]

        rows.append(
            {
                "condition": (
                    condition
                ),
                "case_id": (
                    case_id
                ),
                "document_id": (
                    gt[
                        "document_id"
                    ]
                ),
                "categoria": (
                    gt[
                        "categoria"
                    ]
                ),
                "pregunta": (
                    gt[
                        "pregunta"
                    ]
                ),
                "relevant_chunk_ids": (
                    ";".join(
                        relevant
                    )
                ),
                "retrieved_chunk_ids": (
                    ";".join(
                        retrieved
                    )
                ),
                "recall_at_3": (
                    recall_at_k(
                        relevant,
                        retrieved,
                        3,
                    )
                ),
                "recall_at_5": (
                    recall_at_k(
                        relevant,
                        retrieved,
                        5,
                    )
                ),
                "precision_at_3": (
                    precision_at_k(
                        relevant,
                        retrieved,
                        3,
                    )
                ),
                "precision_at_5": (
                    precision_at_k(
                        relevant,
                        retrieved,
                        5,
                    )
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def summarize(df):
    return {
        "Recall@3": (
            df[
                "recall_at_3"
            ].mean()
        ),
        "Recall@5": (
            df[
                "recall_at_5"
            ].mean()
        ),
        "Precision@3": (
            df[
                "precision_at_3"
            ].mean()
        ),
        "Precision@5": (
            df[
                "precision_at_5"
            ].mean()
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        "Cargando Ground Truth..."
    )

    gt = pd.read_csv(
        GROUND_TRUTH_PATH,
        encoding="utf-8-sig",
    )

    assert len(gt) == 50

    assert (
        gt[
            "case_id"
        ].nunique()
        == 50
    )

    print(
        "Inicializando embeddings..."
    )

    embedding_service = (
        MultilingualEmbedding()
    )

    print(
        "Inicializando Vector Store..."
    )

    vector_store = VectorStore(
        path=str(
            CHROMA_PATH
        ),
        collection_name=(
            COLLECTION_NAME
        ),
        embedding_service=(
            embedding_service
        ),
    )

    print(
        "Cargando corpus congelado..."
    )

    ingestion = (
        ingest_ground_truth_v1(
            str(
                CHUNKS_PATH
            ),
            vector_store,
        )
    )

    print(
        "Chunks:",
        ingestion,
    )

    # ========================================================
    # BATCHES
    # ========================================================

    batches = {
        name: []
        for name
        in WEIGHT_CONFIGS
    }

    total = len(gt)

    # ========================================================
    # RUN
    # ========================================================

    for i, row in gt.iterrows():
        case_id = str(
            row[
                "case_id"
            ]
        ).strip()

        query = str(
            row[
                "pregunta"
            ]
        ).strip()

        document_id = str(
            row[
                "document_id"
            ]
        ).strip()

        print(
            f"[{i + 1:02d}/{total}] "
            f"{case_id}"
        )

        (
            vector_results,
            bm25_results,
        ) = build_base_rankings(
            vector_store,
            query,
            document_id,
        )

        for (
            condition,
            config,
        ) in WEIGHT_CONFIGS.items():

            ranked = weighted_rrf(
                vector_results=(
                    vector_results
                ),
                bm25_results=(
                    bm25_results
                ),
                vector_weight=(
                    config[
                        "vector_weight"
                    ]
                ),
                bm25_weight=(
                    config[
                        "bm25_weight"
                    ]
                ),
            )

            results = (
                format_top_k(
                    ranked
                )
            )

            batches[
                condition
            ].append(
                {
                    "contract_version": (
                        "2.0"
                    ),
                    "case_id": (
                        case_id
                    ),
                    "query": (
                        query
                    ),
                    "top_k": (
                        TOP_K
                    ),
                    "score_type": (
                        "weighted_rrf"
                    ),
                    "status": (
                        "success"
                    ),
                    "filter_mode": (
                        "document_id"
                    ),
                    "filter_trace": {
                        "document_id": (
                            document_id
                        )
                    },
                    "weights": {
                        "vector": (
                            config[
                                "vector_weight"
                            ]
                        ),
                        "bm25": (
                            config[
                                "bm25_weight"
                            ]
                        ),
                    },
                    "results": (
                        results
                    ),
                    "error": None,
                }
            )

    # ========================================================
    # EXPORT RAW BATCHES
    # ========================================================

    for condition, batch in (
        batches.items()
    ):
        safe_name = (
            condition
            .lower()
            .replace(
                " ",
                "_",
            )
            .replace(
                "/",
                "_",
            )
        )

        output_path = (
            OUTPUT_DIR
            / (
                f"retrieval_"
                f"{safe_name}.json"
            )
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                batch,
                f,
                ensure_ascii=False,
                indent=2,
            )

    # ========================================================
    # EVALUATE
    # ========================================================

    evaluation_frames = {}
    summaries = {}

    for condition, batch in (
        batches.items()
    ):
        df = evaluate_condition(
            batch,
            gt,
            condition,
        )

        evaluation_frames[
            condition
        ] = df

        summaries[
            condition
        ] = summarize(
            df
        )

    # ========================================================
    # GLOBAL METRICS
    # ========================================================

    global_df = pd.DataFrame(
        summaries
    )

    print()
    print(
        "=== WEIGHTED RRF ABLATION ==="
    )
    print()

    print(
        global_df
        .round(6)
        .to_string()
    )

    global_df.to_csv(
        GLOBAL_METRICS_PATH,
        encoding="utf-8-sig",
    )

    # ========================================================
    # FAIL COUNT
    # ========================================================

    print()
    print(
        "=== CASOS Recall@5 = 0 ==="
    )

    for condition, df in (
        evaluation_frames.items()
    ):
        failures = int(
            (
                df[
                    "recall_at_5"
                ]
                == 0
            ).sum()
        )

        print(
            f"{condition}: "
            f"{failures}"
        )

    # ========================================================
    # CASE COMPARISON
    # ========================================================

    base = gt[
        [
            "case_id",
            "document_id",
            "categoria",
            "pregunta",
            "relevant_chunk_ids",
        ]
    ].copy()

    for condition, df in (
        evaluation_frames.items()
    ):
        short_name = (
            condition
            .lower()
            .replace(
                " ",
                "_",
            )
            .replace(
                "/",
                "_",
            )
        )

        part = df[
            [
                "case_id",
                "retrieved_chunk_ids",
                "recall_at_3",
                "recall_at_5",
                "precision_at_3",
                "precision_at_5",
            ]
        ].copy()

        part = part.rename(
            columns={
                col: (
                    f"{col}_"
                    f"{short_name}"
                )
                for col
                in part.columns
                if col != "case_id"
            }
        )

        base = base.merge(
            part,
            on="case_id",
        )

    base.to_csv(
        CASE_COMPARISON_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # CATEGORY METRICS
    # ========================================================

    category_frames = []

    for condition, df in (
        evaluation_frames.items()
    ):
        category_df = (
            df
            .groupby(
                "categoria"
            )[
                [
                    "recall_at_3",
                    "recall_at_5",
                    "precision_at_3",
                    "precision_at_5",
                ]
            ]
            .mean()
            .reset_index()
        )

        category_df[
            "condition"
        ] = condition

        category_frames.append(
            category_df
        )

    category_df = pd.concat(
        category_frames,
        ignore_index=True,
    )

    category_df.to_csv(
        CATEGORY_METRICS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # CHANGES VS 50/50
    # ========================================================

    baseline_df = (
        evaluation_frames[
            "RRF 50/50"
        ]
        .set_index(
            "case_id"
        )
    )

    changed_rows = []

    for condition, df in (
        evaluation_frames.items()
    ):
        if (
            condition
            == "RRF 50/50"
        ):
            continue

        current_df = (
            df
            .set_index(
                "case_id"
            )
        )

        for case_id in (
            current_df.index
        ):
            base_r3 = (
                baseline_df.loc[
                    case_id,
                    "recall_at_3",
                ]
            )

            base_r5 = (
                baseline_df.loc[
                    case_id,
                    "recall_at_5",
                ]
            )

            current_r3 = (
                current_df.loc[
                    case_id,
                    "recall_at_3",
                ]
            )

            current_r5 = (
                current_df.loc[
                    case_id,
                    "recall_at_5",
                ]
            )

            if (
                current_r3 != base_r3
                or current_r5 != base_r5
            ):
                changed_rows.append(
                    {
                        "condition": (
                            condition
                        ),
                        "case_id": (
                            case_id
                        ),
                        "categoria": (
                            current_df.loc[
                                case_id,
                                "categoria",
                            ]
                        ),
                        "recall_at_3_50_50": (
                            base_r3
                        ),
                        "recall_at_3_condition": (
                            current_r3
                        ),
                        "delta_recall_at_3": (
                            current_r3
                            - base_r3
                        ),
                        "recall_at_5_50_50": (
                            base_r5
                        ),
                        "recall_at_5_condition": (
                            current_r5
                        ),
                        "delta_recall_at_5": (
                            current_r5
                            - base_r5
                        ),
                    }
                )

    changed_df = pd.DataFrame(
        changed_rows
    )

    changed_df.to_csv(
        CHANGED_CASES_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # FOCUS CASES
    # ========================================================

    focus_cases = [
        "BE-ES-001-Q02",
        "BE-ES-002-Q03",
        "CLD-ES-001-Q05",
    ]

    print()
    print(
        "=== CASOS CLAVE ==="
    )

    for case_id in focus_cases:
        print()
        print(
            case_id
        )

        for condition, df in (
            evaluation_frames.items()
        ):
            row = df[
                df[
                    "case_id"
                ]
                == case_id
            ]

            if row.empty:
                continue

            print(
                f"  {condition}: "
                f"R@3="
                f"{row.iloc[0]['recall_at_3']:.3f} "
                f"R@5="
                f"{row.iloc[0]['recall_at_5']:.3f}"
            )

    # ========================================================
    # BEST GLOBAL CONFIG
    # ========================================================

    print()
    print(
        "=== MEJOR CONFIGURACIÓN ==="
    )

    ranking_df = (
        global_df
        .T
        .copy()
    )

    ranking_df = (
        ranking_df
        .sort_values(
            by=[
                "Recall@5",
                "Recall@3",
                "Precision@5",
                "Precision@3",
            ],
            ascending=False,
        )
    )

    print(
        ranking_df
        .round(6)
        .to_string()
    )

    best_condition = (
        ranking_df.index[0]
    )

    print()
    print(
        "Mejor configuración:",
        best_condition,
    )

    # ========================================================
    # MANIFEST
    # ========================================================

    manifest = {
        "experiment": (
            "retrieval_v2_weighted_rrf_ablation"
        ),
        "total_cases": 50,
        "top_k": TOP_K,
        "candidate_k": (
            CANDIDATE_K
        ),
        "rrf_k": (
            RRF_K
        ),
        "metadata_filter": (
            "document_id"
        ),
        "ground_truth": (
            "ground_truth_v2.csv"
        ),
        "corpus": (
            "chunks_v1.csv"
        ),
        "formula": (
            "vector_weight / "
            "(rrf_k + vector_rank) "
            "+ bm25_weight / "
            "(rrf_k + bm25_rank)"
        ),
        "weight_configs": (
            WEIGHT_CONFIGS
        ),
        "cross_encoder": False,
        "hashes": {
            "ground_truth_v2.csv": (
                sha256_file(
                    GROUND_TRUTH_PATH
                )
            ),
            "chunks_v1.csv": (
                sha256_file(
                    CHUNKS_PATH
                )
            ),
        },
    }

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            manifest,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "Artefactos:"
    )

    print(
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()