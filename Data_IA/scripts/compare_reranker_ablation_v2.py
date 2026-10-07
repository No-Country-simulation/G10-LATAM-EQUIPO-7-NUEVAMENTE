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

CROSS_ENCODER_RESULTS_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "input"
    / "retrieval_results_agentes_v2.json"
)

OUTPUT_DIR = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "results"
    / "retrieval_v2_ablation"
    / "reranker_ablation"
)

RRF_RESULTS_PATH = (
    OUTPUT_DIR
    / "retrieval_results_v2_rrf_only.json"
)

CASE_COMPARISON_PATH = (
    OUTPUT_DIR
    / "reranker_ablation_case_comparison.csv"
)

GLOBAL_METRICS_PATH = (
    OUTPUT_DIR
    / "reranker_ablation_global_metrics.csv"
)

CATEGORY_METRICS_PATH = (
    OUTPUT_DIR
    / "reranker_ablation_category_metrics.csv"
)

FAILURE_ANALYSIS_PATH = (
    OUTPUT_DIR
    / "reranker_ablation_failures.csv"
)

MANIFEST_PATH = (
    OUTPUT_DIR
    / "reranker_ablation_manifest.json"
)


# ============================================================
# CHROMA
# ============================================================

CHROMA_PATH = ROOT / ".benchmark_chroma_v2_reranker_ablation"

COLLECTION_NAME = "benchmark_retrieval_v2_reranker_ablation"


# ============================================================
# CONFIG
# ============================================================

TOP_K = 5
CANDIDATE_K = TOP_K * 3
RRF_K = 60


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
    relevant = set(relevant)

    if not relevant:
        return 0.0

    return (
        len(
            relevant.intersection(
                retrieved[:k]
            )
        )
        / len(relevant)
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
# RRF-ONLY SEARCH
# ============================================================

def search_rrf_only(
    vector_store,
    query,
    document_id,
    top_k=TOP_K,
):
    """
    Replica el pipeline actual hasta RRF,
    pero NO aplica Cross-Encoder.
    """

    embedding = (
        vector_store
        .embedding_service
        .embed_query(query)
    )

    candidate_k = top_k * 3

    where_clause = {
        "document_id": document_id
    }

    # ========================================================
    # 1. VECTOR SEARCH
    # ========================================================

    vector_data = (
        vector_store
        .collection
        .query(
            query_embeddings=[
                embedding
            ],
            n_results=candidate_k,
            where=where_clause,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )
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
        tokenized_corpus = [
            tokenize(doc)
            for doc
            in all_filtered_data[
                "documents"
            ]
        ]

        bm25 = BM25Okapi(
            tokenized_corpus
        )

        tokenized_query = tokenize(
            query
        )

        doc_scores = bm25.get_scores(
            tokenized_query
        )

        top_indices = sorted(
            range(len(doc_scores)),
            key=lambda i: doc_scores[i],
            reverse=True,
        )[:candidate_k]

        for i in top_indices:
            if doc_scores[i] > 0:
                bm25_results.append(
                    {
                        "chunk_id": (
                            all_filtered_data[
                                "ids"
                            ][i]
                        ),
                        "text": (
                            all_filtered_data[
                                "documents"
                            ][i]
                        ),
                        "metadata": (
                            all_filtered_data[
                                "metadatas"
                            ][i]
                        ),
                        "bm25_score": float(
                            doc_scores[i]
                        ),
                    }
                )

    # ========================================================
    # 3. RRF
    # ========================================================

    rrf_scores = {}

    if (
        vector_data
        and vector_data["ids"]
        and vector_data["ids"][0]
    ):
        for rank, chunk_id in enumerate(
            vector_data["ids"][0]
        ):
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {
                    "rrf_score": 0.0,
                    "text": (
                        vector_data[
                            "documents"
                        ][0][rank]
                    ),
                    "metadata": (
                        vector_data[
                            "metadatas"
                        ][0][rank]
                    ),
                    "vector_rank": None,
                    "bm25_rank": None,
                }

            rrf_scores[chunk_id][
                "vector_rank"
            ] = rank + 1

            rrf_scores[chunk_id][
                "rrf_score"
            ] += (
                1.0
                / (
                    RRF_K
                    + rank
                    + 1
                )
            )

    for rank, res in enumerate(
        bm25_results
    ):
        chunk_id = res["chunk_id"]

        if chunk_id not in rrf_scores:
            rrf_scores[chunk_id] = {
                "rrf_score": 0.0,
                "text": res["text"],
                "metadata": res[
                    "metadata"
                ],
                "vector_rank": None,
                "bm25_rank": None,
            }

        rrf_scores[chunk_id][
            "bm25_rank"
        ] = rank + 1

        rrf_scores[chunk_id][
            "rrf_score"
        ] += (
            1.0
            / (
                RRF_K
                + rank
                + 1
            )
        )

    hybrid_candidates = sorted(
        rrf_scores.items(),
        key=lambda x: x[1][
            "rrf_score"
        ],
        reverse=True,
    )[:candidate_k]

    # ========================================================
    # 4. TOP-K DIRECTAMENTE DESDE RRF
    # ========================================================

    final_rrf = hybrid_candidates[
        :top_k
    ]

    results = []

    for rank, (
        chunk_id,
        data,
    ) in enumerate(
        final_rrf,
        start=1,
    ):
        results.append(
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "document_id": (
                    data[
                        "metadata"
                    ].get(
                        "document_id"
                    )
                ),
                "score": float(
                    data[
                        "rrf_score"
                    ]
                ),
                "rrf_score": float(
                    data[
                        "rrf_score"
                    ]
                ),
                "vector_rank": data[
                    "vector_rank"
                ],
                "bm25_rank": data[
                    "bm25_rank"
                ],
                "text": data["text"],
                "metadata": data[
                    "metadata"
                ],
            }
        )

    return results


# ============================================================
# GENERAR BATCH RRF-ONLY
# ============================================================

def generate_rrf_batch(
    vector_store,
    ground_truth_df,
):
    batch = []

    total = len(
        ground_truth_df
    )

    for index, row in (
        ground_truth_df.iterrows()
    ):
        case_id = str(
            row["case_id"]
        ).strip()

        query = str(
            row["pregunta"]
        ).strip()

        document_id = str(
            row["document_id"]
        ).strip()

        print(
            f"[{index + 1:02d}/{total}] "
            f"{case_id}"
        )

        results = search_rrf_only(
            vector_store=vector_store,
            query=query,
            document_id=document_id,
            top_k=TOP_K,
        )

        batch.append(
            {
                "contract_version": "2.0",
                "case_id": case_id,
                "query": query,
                "top_k": TOP_K,
                "score_type": "rrf",
                "status": "success",
                "results": results,
                "error": None,
                "filter_mode": (
                    "document_id"
                ),
                "filter_trace": {
                    "document_id": (
                        document_id
                    )
                },
            }
        )

    return batch


# ============================================================
# EVALUACIÓN
# ============================================================

def evaluate_batch(
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
        case_id = case["case_id"]

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
            result["chunk_id"]
            for result
            in case["results"]
        ]

        rows.append(
            {
                "condition": condition,
                "case_id": case_id,
                "document_id": (
                    gt["document_id"]
                ),
                "categoria": (
                    gt["categoria"]
                ),
                "pregunta": (
                    gt["pregunta"]
                ),
                "relevant_chunk_ids": (
                    ";".join(relevant)
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


# ============================================================
# SUMMARY
# ============================================================

def summarize(
    df,
):
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
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Cargando Ground Truth..."
    )

    ground_truth_df = (
        pd.read_csv(
            GROUND_TRUTH_PATH,
            encoding="utf-8-sig",
        )
    )

    assert len(
        ground_truth_df
    ) == 50

    assert (
        ground_truth_df[
            "case_id"
        ].nunique()
        == 50
    )

    print(
        "Cargando resultados "
        "Cross-Encoder actuales..."
    )

    with (
        CROSS_ENCODER_RESULTS_PATH
        .open(
            "r",
            encoding="utf-8",
        )
    ) as f:
        cross_batch = json.load(f)

    assert len(
        cross_batch
    ) == 50

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
            str(CHUNKS_PATH),
            vector_store,
        )
    )

    print(
        "Chunks:",
        ingestion,
    )

    print()
    print(
        "Generando RRF-only..."
    )

    rrf_batch = (
        generate_rrf_batch(
            vector_store,
            ground_truth_df,
        )
    )

    with RRF_RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            rrf_batch,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "Evaluando RRF-only..."
    )

    rrf_df = evaluate_batch(
        rrf_batch,
        ground_truth_df,
        "V2 filtered RRF-only",
    )

    print(
        "Evaluando Cross-Encoder..."
    )

    cross_df = evaluate_batch(
        cross_batch,
        ground_truth_df,
        "V2 filtered Cross-Encoder",
    )

    # ========================================================
    # GLOBAL
    # ========================================================

    rrf_summary = summarize(
        rrf_df
    )

    cross_summary = summarize(
        cross_df
    )

    global_df = pd.DataFrame(
        {
            "RRF-only": (
                rrf_summary
            ),
            "Cross-Encoder": (
                cross_summary
            ),
        }
    )

    global_df[
        "delta_cross_vs_rrf"
    ] = (
        global_df[
            "Cross-Encoder"
        ]
        - global_df[
            "RRF-only"
        ]
    )

    print()
    print(
        "=== RERANKER ABLATION ==="
    )
    print()

    print(
        global_df
        .round(6)
        .to_string()
    )

    # ========================================================
    # CASE COMPARISON
    # ========================================================

    case_df = (
        rrf_df[
            [
                "case_id",
                "document_id",
                "categoria",
                "pregunta",
                "relevant_chunk_ids",
                "retrieved_chunk_ids",
                "recall_at_3",
                "recall_at_5",
                "precision_at_3",
                "precision_at_5",
            ]
        ]
        .merge(
            cross_df[
                [
                    "case_id",
                    "retrieved_chunk_ids",
                    "recall_at_3",
                    "recall_at_5",
                    "precision_at_3",
                    "precision_at_5",
                ]
            ],
            on="case_id",
            suffixes=(
                "_rrf",
                "_cross",
            ),
        )
    )

    for metric in [
        "recall_at_3",
        "recall_at_5",
        "precision_at_3",
        "precision_at_5",
    ]:
        case_df[
            f"delta_{metric}_cross_vs_rrf"
        ] = (
            case_df[
                f"{metric}_cross"
            ]
            - case_df[
                f"{metric}_rrf"
            ]
        )

    # ========================================================
    # FAILURES / WINS
    # ========================================================

    failure_df = (
        case_df[
            (
                case_df[
                    "recall_at_5_rrf"
                ]
                !=
                case_df[
                    "recall_at_5_cross"
                ]
            )
        ]
        .copy()
    )

    print()
    print(
        "=== CASOS DONDE CAMBIA RECALL@5 ==="
    )

    if failure_df.empty:
        print(
            "Sin diferencias."
        )
    else:
        print(
            failure_df[
                [
                    "case_id",
                    "categoria",
                    "recall_at_5_rrf",
                    "recall_at_5_cross",
                    "delta_recall_at_5_cross_vs_rrf",
                ]
            ]
            .to_string(
                index=False
            )
        )

    # ========================================================
    # CATEGORY
    # ========================================================

    rrf_cat = (
        rrf_df
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
        .add_suffix(
            "_rrf"
        )
        .reset_index()
    )

    cross_cat = (
        cross_df
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
        .add_suffix(
            "_cross"
        )
        .reset_index()
    )

    category_df = (
        rrf_cat
        .merge(
            cross_cat,
            on="categoria",
        )
    )

    # ========================================================
    # EXPORT
    # ========================================================

    global_df.to_csv(
        GLOBAL_METRICS_PATH,
        encoding="utf-8-sig",
    )

    case_df.to_csv(
        CASE_COMPARISON_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    category_df.to_csv(
        CATEGORY_METRICS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    failure_df.to_csv(
        FAILURE_ANALYSIS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # MANIFEST
    # ========================================================

    manifest = {
        "experiment": (
            "retrieval_v2_reranker_ablation"
        ),
        "total_cases": 50,
        "top_k": TOP_K,
        "candidate_k": CANDIDATE_K,
        "rrf_k": RRF_K,
        "metadata_filter": (
            "document_id"
        ),
        "ground_truth": (
            "ground_truth_v2.csv"
        ),
        "corpus": (
            "chunks_v1.csv"
        ),
        "conditions": {
            "rrf_only": {
                "vector_search": True,
                "bm25": True,
                "rrf": True,
                "cross_encoder": False,
            },
            "cross_encoder": {
                "vector_search": True,
                "bm25": True,
                "rrf": True,
                "cross_encoder": True,
                "model": (
                    "cross-encoder/"
                    "ms-marco-MiniLM-L-6-v2"
                ),
            },
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
            (
                "retrieval_results_"
                "agentes_v2.json"
            ): (
                sha256_file(
                    CROSS_ENCODER_RESULTS_PATH
                )
            ),
            (
                "retrieval_results_"
                "v2_rrf_only.json"
            ): (
                sha256_file(
                    RRF_RESULTS_PATH
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
        "=== CASOS Recall@5 = 0 ==="
    )

    print(
        "RRF-only:",
        int(
            (
                rrf_df[
                    "recall_at_5"
                ]
                == 0
            ).sum()
        ),
    )

    print(
        "Cross-Encoder:",
        int(
            (
                cross_df[
                    "recall_at_5"
                ]
                == 0
            ).sum()
        ),
    )

    print()
    print(
        "Artefactos:",
        OUTPUT_DIR,
    )


if __name__ == "__main__":
    main()