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

CURRENT_CROSS_PATH = (
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
    / "fusion_ablation"
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
    / "fusion_ablation_global_metrics.csv"
)

CASE_COMPARISON_PATH = (
    OUTPUT_DIR
    / "fusion_ablation_case_comparison.csv"
)

CATEGORY_METRICS_PATH = (
    OUTPUT_DIR
    / "fusion_ablation_category_metrics.csv"
)

CHANGED_CASES_PATH = (
    OUTPUT_DIR
    / "fusion_ablation_changed_cases.csv"
)

MANIFEST_PATH = (
    OUTPUT_DIR
    / "fusion_ablation_manifest.json"
)


# ============================================================
# CHROMA
# ============================================================

CHROMA_PATH = (
    ROOT
    / ".benchmark_chroma_v2_fusion_ablation"
)

COLLECTION_NAME = (
    "benchmark_retrieval_v2_fusion_ablation"
)


# ============================================================
# CONFIG
# ============================================================

TOP_K = 5
CANDIDATE_K = TOP_K * 3
RRF_K = 60

ALPHAS = [
    0.25,
    0.50,
    0.75,
]


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
    relevant_set = set(
        relevant
    )

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


def minmax_normalize(values):
    """
    Normalización min-max por query/candidate set.

    Devuelve valores en [0, 1].
    """

    values = [
        float(v)
        for v in values
    ]

    if not values:
        return []

    min_value = min(values)
    max_value = max(values)

    if max_value == min_value:
        return [
            1.0
            for _ in values
        ]

    return [
        (
            value - min_value
        )
        / (
            max_value - min_value
        )
        for value in values
    ]


# ============================================================
# GENERAR CANDIDATOS + SCORES
# ============================================================

def build_scored_candidates(
    vector_store,
    query,
    document_id,
):
    """
    Replica:

    Vector
    + BM25
    + RRF
    + Cross-Encoder

    pero devuelve los candidate_k completos
    con ambos scores para permitir fusiones.
    """

    embedding = (
        vector_store
        .embedding_service
        .embed_query(query)
    )

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
            n_results=CANDIDATE_K,
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

        doc_scores = (
            bm25.get_scores(
                tokenized_query
            )
        )

        top_indices = sorted(
            range(
                len(doc_scores)
            ),
            key=lambda i: doc_scores[i],
            reverse=True,
        )[:CANDIDATE_K]

        for i in top_indices:
            if doc_scores[i] <= 0:
                continue

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
                rrf_scores[
                    chunk_id
                ] = {
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

            rrf_scores[
                chunk_id
            ][
                "vector_rank"
            ] = rank + 1

            rrf_scores[
                chunk_id
            ][
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
        chunk_id = res[
            "chunk_id"
        ]

        if (
            chunk_id
            not in rrf_scores
        ):
            rrf_scores[
                chunk_id
            ] = {
                "rrf_score": 0.0,
                "text": res["text"],
                "metadata": (
                    res["metadata"]
                ),
                "vector_rank": None,
                "bm25_rank": None,
            }

        rrf_scores[
            chunk_id
        ][
            "bm25_rank"
        ] = rank + 1

        rrf_scores[
            chunk_id
        ][
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
    )[:CANDIDATE_K]

    if not hybrid_candidates:
        return []

    # ========================================================
    # 4. CROSS-ENCODER
    # ========================================================

    cross_input = [
        [
            query,
            data["text"],
        ]
        for _, data
        in hybrid_candidates
    ]

    cross_scores = (
        vector_store
        .reranker
        .predict(
            cross_input
        )
    )

    candidates = []

    for index, (
        chunk_id,
        data,
    ) in enumerate(
        hybrid_candidates
    ):
        candidates.append(
            {
                "chunk_id": chunk_id,
                "document_id": (
                    data[
                        "metadata"
                    ].get(
                        "document_id"
                    )
                ),
                "text": data["text"],
                "metadata": (
                    data["metadata"]
                ),
                "rrf_score": float(
                    data[
                        "rrf_score"
                    ]
                ),
                "cross_score": float(
                    cross_scores[index]
                ),
                "vector_rank": (
                    data[
                        "vector_rank"
                    ]
                ),
                "bm25_rank": (
                    data[
                        "bm25_rank"
                    ]
                ),
            }
        )

    # ========================================================
    # 5. NORMALIZAR
    # ========================================================

    normalized_rrf = (
        minmax_normalize(
            [
                candidate[
                    "rrf_score"
                ]
                for candidate
                in candidates
            ]
        )
    )

    normalized_cross = (
        minmax_normalize(
            [
                candidate[
                    "cross_score"
                ]
                for candidate
                in candidates
            ]
        )
    )

    for index, candidate in enumerate(
        candidates
    ):
        candidate[
            "rrf_normalized"
        ] = normalized_rrf[index]

        candidate[
            "cross_normalized"
        ] = normalized_cross[index]

    return candidates


# ============================================================
# RANKING METHODS
# ============================================================

def rank_rrf_only(
    candidates,
):
    ranked = sorted(
        candidates,
        key=lambda x: x[
            "rrf_score"
        ],
        reverse=True,
    )

    return ranked[:TOP_K]


def rank_cross_only(
    candidates,
):
    ranked = sorted(
        candidates,
        key=lambda x: x[
            "cross_score"
        ],
        reverse=True,
    )

    return ranked[:TOP_K]


def rank_fusion(
    candidates,
    alpha,
):
    """
    alpha = peso del Cross-Encoder.

    1-alpha = peso de RRF.
    """

    scored = []

    for candidate in candidates:
        item = dict(
            candidate
        )

        item[
            "fusion_score"
        ] = (
            alpha
            * item[
                "cross_normalized"
            ]
            +
            (
                1.0 - alpha
            )
            * item[
                "rrf_normalized"
            ]
        )

        scored.append(
            item
        )

    ranked = sorted(
        scored,
        key=lambda x: x[
            "fusion_score"
        ],
        reverse=True,
    )

    return ranked[:TOP_K]


# ============================================================
# RESULT FORMAT
# ============================================================

def make_result_list(
    ranked,
    score_type,
):
    results = []

    for rank, item in enumerate(
        ranked,
        start=1,
    ):
        if (
            score_type
            == "rrf"
        ):
            score = (
                item[
                    "rrf_score"
                ]
            )

        elif (
            score_type
            == "cross_encoder"
        ):
            score = (
                item[
                    "cross_score"
                ]
            )

        else:
            score = (
                item[
                    "fusion_score"
                ]
            )

        results.append(
            {
                "rank": rank,
                "chunk_id": (
                    item[
                        "chunk_id"
                    ]
                ),
                "document_id": (
                    item[
                        "document_id"
                    ]
                ),
                "score": float(
                    score
                ),
                "rrf_score": float(
                    item[
                        "rrf_score"
                    ]
                ),
                "cross_score": float(
                    item[
                        "cross_score"
                    ]
                ),
                "rrf_normalized": float(
                    item[
                        "rrf_normalized"
                    ]
                ),
                "cross_normalized": float(
                    item[
                        "cross_normalized"
                    ]
                ),
                "vector_rank": (
                    item[
                        "vector_rank"
                    ]
                ),
                "bm25_rank": (
                    item[
                        "bm25_rank"
                    ]
                ),
                "text": item[
                    "text"
                ],
                "metadata": item[
                    "metadata"
                ],
            }
        )

    return results


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
            case["case_id"]
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
            in case["results"]
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
            str(CHUNKS_PATH),
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
        "RRF-only": [],
        "Cross-Encoder": [],
    }

    for alpha in ALPHAS:
        batches[
            f"Fusion alpha={alpha:.2f}"
        ] = []

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

        candidates = (
            build_scored_candidates(
                vector_store,
                query,
                document_id,
            )
        )

        # ----------------------------------------------------
        # RRF
        # ----------------------------------------------------

        rrf_ranked = (
            rank_rrf_only(
                candidates
            )
        )

        batches[
            "RRF-only"
        ].append(
            {
                "case_id": case_id,
                "query": query,
                "results": (
                    make_result_list(
                        rrf_ranked,
                        "rrf",
                    )
                ),
            }
        )

        # ----------------------------------------------------
        # CROSS
        # ----------------------------------------------------

        cross_ranked = (
            rank_cross_only(
                candidates
            )
        )

        batches[
            "Cross-Encoder"
        ].append(
            {
                "case_id": case_id,
                "query": query,
                "results": (
                    make_result_list(
                        cross_ranked,
                        "cross_encoder",
                    )
                ),
            }
        )

        # ----------------------------------------------------
        # FUSIONS
        # ----------------------------------------------------

        for alpha in ALPHAS:
            name = (
                f"Fusion alpha="
                f"{alpha:.2f}"
            )

            fusion_ranked = (
                rank_fusion(
                    candidates,
                    alpha,
                )
            )

            batches[
                name
            ].append(
                {
                    "case_id": (
                        case_id
                    ),
                    "query": (
                        query
                    ),
                    "results": (
                        make_result_list(
                            fusion_ranked,
                            "fusion",
                        )
                    ),
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
                "=",
                "_",
            )
            .replace(
                ".",
                "_",
            )
        )

        path = (
            OUTPUT_DIR
            / (
                f"retrieval_"
                f"{safe_name}.json"
            )
        )

        with path.open(
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
        "=== FUSION ABLATION ==="
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
    # CASE COMPARISON
    # ========================================================

    base = (
        evaluation_frames[
            "RRF-only"
        ][
            [
                "case_id",
                "document_id",
                "categoria",
                "pregunta",
                "relevant_chunk_ids",
            ]
        ]
        .copy()
    )

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
                "=",
                "_",
            )
            .replace(
                ".",
                "_",
            )
            .replace(
                "-",
                "_",
            )
        )

        metric_part = df[
            [
                "case_id",
                "retrieved_chunk_ids",
                "recall_at_3",
                "recall_at_5",
                "precision_at_3",
                "precision_at_5",
            ]
        ].copy()

        metric_part = (
            metric_part.rename(
                columns={
                    col: (
                        f"{col}_"
                        f"{short_name}"
                    )
                    for col
                    in metric_part.columns
                    if col
                    != "case_id"
                }
            )
        )

        base = base.merge(
            metric_part,
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
        category = (
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

        category[
            "condition"
        ] = condition

        category_frames.append(
            category
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
    # CHANGED CASES VS CROSS-ENCODER
    # ========================================================

    cross_df = (
        evaluation_frames[
            "Cross-Encoder"
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
            == "Cross-Encoder"
        ):
            continue

        current = (
            df
            .set_index(
                "case_id"
            )
        )

        for case_id in (
            current.index
        ):
            cross_r3 = (
                cross_df.loc[
                    case_id,
                    "recall_at_3",
                ]
            )

            cross_r5 = (
                cross_df.loc[
                    case_id,
                    "recall_at_5",
                ]
            )

            current_r3 = (
                current.loc[
                    case_id,
                    "recall_at_3",
                ]
            )

            current_r5 = (
                current.loc[
                    case_id,
                    "recall_at_5",
                ]
            )

            if (
                current_r3
                != cross_r3
                or current_r5
                != cross_r5
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
                            current.loc[
                                case_id,
                                "categoria",
                            ]
                        ),
                        "recall_at_3_condition": (
                            current_r3
                        ),
                        "recall_at_3_cross": (
                            cross_r3
                        ),
                        "delta_recall_at_3": (
                            current_r3
                            - cross_r3
                        ),
                        "recall_at_5_condition": (
                            current_r5
                        ),
                        "recall_at_5_cross": (
                            cross_r5
                        ),
                        "delta_recall_at_5": (
                            current_r5
                            - cross_r5
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
    # MANIFEST
    # ========================================================

    manifest = {
        "experiment": (
            "retrieval_v2_rrf_cross_fusion_ablation"
        ),
        "total_cases": 50,
        "top_k": TOP_K,
        "candidate_k": (
            CANDIDATE_K
        ),
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
        "normalization": (
            "per-query min-max "
            "over candidate set"
        ),
        "fusion_formula": (
            "alpha * cross_normalized "
            "+ (1-alpha) * rrf_normalized"
        ),
        "alpha_meaning": (
            "Cross-Encoder weight"
        ),
        "alphas": ALPHAS,
        "conditions": [
            "RRF-only",
            "Fusion alpha=0.25",
            "Fusion alpha=0.50",
            "Fusion alpha=0.75",
            "Cross-Encoder",
        ],
        "models": {
            "cross_encoder": (
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
            (
                "retrieval_results_"
                "agentes_v2.json"
            ): (
                sha256_file(
                    CURRENT_CROSS_PATH
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