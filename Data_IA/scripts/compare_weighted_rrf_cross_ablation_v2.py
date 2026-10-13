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
    / "weighted_rrf_cross_ablation"
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
    / "weighted_rrf_cross_global_metrics.csv"
)

CASE_COMPARISON_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_cross_case_comparison.csv"
)

CATEGORY_METRICS_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_cross_category_metrics.csv"
)

CHANGED_CASES_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_cross_changed_cases.csv"
)

MANIFEST_PATH = (
    OUTPUT_DIR
    / "weighted_rrf_cross_manifest.json"
)


# ============================================================
# CHROMA
# ============================================================

CHROMA_PATH = (
    ROOT
    / ".benchmark_chroma_v2_weighted_rrf_cross"
)

COLLECTION_NAME = (
    "benchmark_retrieval_v2_weighted_rrf_cross"
)


# ============================================================
# CONFIG
# ============================================================

TOP_K = 5
CANDIDATE_K = TOP_K * 3
RRF_K = 60

WEIGHT_CONFIGS = {
    "RRF 50/50 + Cross": {
        "vector_weight": 0.50,
        "bm25_weight": 0.50,
    },
    "RRF 60/40 + Cross": {
        "vector_weight": 0.60,
        "bm25_weight": 0.40,
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
# BASE RANKINGS
# ============================================================

def build_base_rankings(
    vector_store,
    query,
    document_id,
):
    where_clause = {
        "document_id": document_id
    }

    # --------------------------------------------------------
    # Vector
    # --------------------------------------------------------

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
                }
            )

    # --------------------------------------------------------
    # BM25
    # --------------------------------------------------------

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
                "weighted_rrf_score": 0.0,
            }

        fused[
            chunk_id
        ][
            "vector_rank"
        ] = rank

        fused[
            chunk_id
        ][
            "weighted_rrf_score"
        ] += (
            vector_weight
            / (
                RRF_K
                + rank
            )
        )

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
                "weighted_rrf_score": 0.0,
            }

        fused[
            chunk_id
        ][
            "bm25_rank"
        ] = rank

        fused[
            chunk_id
        ][
            "weighted_rrf_score"
        ] += (
            bm25_weight
            / (
                RRF_K
                + rank
            )
        )

    ranked = sorted(
        fused.values(),
        key=lambda x: x[
            "weighted_rrf_score"
        ],
        reverse=True,
    )[:CANDIDATE_K]

    return ranked


# ============================================================
# CROSS-ENCODER
# ============================================================

def apply_cross_encoder(
    vector_store,
    query,
    candidates,
):
    if not candidates:
        return []

    cross_input = [
        [
            query,
            row["text"],
        ]
        for row in candidates
    ]

    cross_scores = (
        vector_store
        .reranker
        .predict(
            cross_input
        )
    )

    reranked = []

    for index, row in enumerate(
        candidates
    ):
        item = dict(row)

        item[
            "cross_score"
        ] = float(
            cross_scores[index]
        )

        reranked.append(
            item
        )

    reranked = sorted(
        reranked,
        key=lambda x: x[
            "cross_score"
        ],
        reverse=True,
    )

    for rank, row in enumerate(
        reranked,
        start=1,
    ):
        row["rank"] = rank

    return reranked


# ============================================================
# FORMAT TOP K
# ============================================================

def format_top_k(
    reranked,
):
    output = []

    for rank, row in enumerate(
        reranked[:TOP_K],
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
                        "cross_score"
                    ]
                ),
                "cross_score": float(
                    row[
                        "cross_score"
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

        gt = gt_by_case[
            case_id
        ]

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

            candidates = weighted_rrf(
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

            reranked = (
                apply_cross_encoder(
                    vector_store,
                    query,
                    candidates,
                )
            )

            results = (
                format_top_k(
                    reranked
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
                        "cross_encoder"
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
    # EXPORT RAW
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
            .replace(
                "+",
                "plus",
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

    global_df = pd.DataFrame(
        summaries
    )

    print()
    print(
        "=== WEIGHTED RRF + CROSS ABLATION ==="
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
        short = (
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
            .replace(
                "+",
                "plus",
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
                    f"{col}_{short}"
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
    # CHANGED CASES
    # ========================================================

    baseline_df = (
        evaluation_frames[
            "RRF 50/50 + Cross"
        ]
        .set_index(
            "case_id"
        )
    )

    candidate_df = (
        evaluation_frames[
            "RRF 60/40 + Cross"
        ]
        .set_index(
            "case_id"
        )
    )

    changed_rows = []

    for case_id in (
        baseline_df.index
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

        cand_r3 = (
            candidate_df.loc[
                case_id,
                "recall_at_3",
            ]
        )

        cand_r5 = (
            candidate_df.loc[
                case_id,
                "recall_at_5",
            ]
        )

        if (
            base_r3 != cand_r3
            or base_r5 != cand_r5
        ):
            changed_rows.append(
                {
                    "case_id": (
                        case_id
                    ),
                    "categoria": (
                        candidate_df.loc[
                            case_id,
                            "categoria",
                        ]
                    ),
                    "recall_at_3_50_50_cross": (
                        base_r3
                    ),
                    "recall_at_3_60_40_cross": (
                        cand_r3
                    ),
                    "delta_recall_at_3": (
                        cand_r3
                        - base_r3
                    ),
                    "recall_at_5_50_50_cross": (
                        base_r5
                    ),
                    "recall_at_5_60_40_cross": (
                        cand_r5
                    ),
                    "delta_recall_at_5": (
                        cand_r5
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
    # KEY CASES
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
    # BEST CONFIG
    # ========================================================

    print()
    print(
        "=== MEJOR CONFIGURACIÓN ==="
    )

    ranking_df = (
        global_df
        .T
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

    print()
    print(
        "Mejor configuración:",
        ranking_df.index[0],
    )

    # ========================================================
    # MANIFEST
    # ========================================================

    manifest = {
        "experiment": (
            "retrieval_v2_weighted_rrf_cross_ablation"
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
        "conditions": (
            WEIGHT_CONFIGS
        ),
        "cross_encoder": {
            "enabled": True,
            "model": (
                "cross-encoder/"
                "ms-marco-MiniLM-L-6-v2"
            ),
        },
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