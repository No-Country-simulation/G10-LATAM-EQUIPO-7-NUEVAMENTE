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
    / "signal_ablation"
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
    / "signal_ablation_global_metrics.csv"
)

CASE_COMPARISON_PATH = (
    OUTPUT_DIR
    / "signal_ablation_case_comparison.csv"
)

CATEGORY_METRICS_PATH = (
    OUTPUT_DIR
    / "signal_ablation_category_metrics.csv"
)

CHANGED_CASES_PATH = (
    OUTPUT_DIR
    / "signal_ablation_changed_cases.csv"
)

MANIFEST_PATH = (
    OUTPUT_DIR
    / "signal_ablation_manifest.json"
)


# ============================================================
# CHROMA
# ============================================================

CHROMA_PATH = (
    ROOT
    / ".benchmark_chroma_v2_signal_ablation"
)

COLLECTION_NAME = (
    "benchmark_retrieval_v2_signal_ablation"
)


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
# BUILD SIGNALS
# ============================================================

def build_signals(
    vector_store,
    query,
    document_id,
):
    """
    Genera:
    - ranking vectorial
    - ranking BM25
    - ranking RRF
    - ranking final Cross-Encoder

    usando el mismo filtro document_id.
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
                    "vector_distance": float(
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

        bm25_rank = 0

        for i in top_indices:
            if doc_scores[i] <= 0:
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
                        doc_scores[i]
                    ),
                }
            )

    # ========================================================
    # 3. RRF
    # ========================================================

    rrf_scores = {}

    for row in vector_results:
        chunk_id = row["chunk_id"]
        rank = row["rank"]

        if chunk_id not in rrf_scores:
            rrf_scores[
                chunk_id
            ] = {
                "chunk_id": chunk_id,
                "text": row["text"],
                "metadata": (
                    row["metadata"]
                ),
                "document_id": (
                    row[
                        "document_id"
                    ]
                ),
                "rrf_score": 0.0,
                "vector_rank": None,
                "bm25_rank": None,
            }

        rrf_scores[
            chunk_id
        ][
            "vector_rank"
        ] = rank

        rrf_scores[
            chunk_id
        ][
            "rrf_score"
        ] += (
            1.0
            / (
                RRF_K
                + rank
            )
        )

    for row in bm25_results:
        chunk_id = row["chunk_id"]
        rank = row["rank"]

        if chunk_id not in rrf_scores:
            rrf_scores[
                chunk_id
            ] = {
                "chunk_id": chunk_id,
                "text": row["text"],
                "metadata": (
                    row["metadata"]
                ),
                "document_id": (
                    row[
                        "document_id"
                    ]
                ),
                "rrf_score": 0.0,
                "vector_rank": None,
                "bm25_rank": None,
            }

        rrf_scores[
            chunk_id
        ][
            "bm25_rank"
        ] = rank

        rrf_scores[
            chunk_id
        ][
            "rrf_score"
        ] += (
            1.0
            / (
                RRF_K
                + rank
            )
        )

    rrf_results = sorted(
        rrf_scores.values(),
        key=lambda x: x[
            "rrf_score"
        ],
        reverse=True,
    )[:CANDIDATE_K]

    for rank, row in enumerate(
        rrf_results,
        start=1,
    ):
        row["rank"] = rank

    # ========================================================
    # 4. CROSS-ENCODER
    # ========================================================

    cross_results = []

    if rrf_results:
        cross_input = [
            [
                query,
                row["text"],
            ]
            for row
            in rrf_results
        ]

        cross_scores = (
            vector_store
            .reranker
            .predict(
                cross_input
            )
        )

        for index, row in enumerate(
            rrf_results
        ):
            item = dict(row)

            item[
                "cross_score"
            ] = float(
                cross_scores[index]
            )

            cross_results.append(
                item
            )

        cross_results = sorted(
            cross_results,
            key=lambda x: x[
                "cross_score"
            ],
            reverse=True,
        )

        for rank, row in enumerate(
            cross_results,
            start=1,
        ):
            row["rank"] = rank

    return {
        "vector": vector_results,
        "bm25": bm25_results,
        "rrf": rrf_results,
        "cross": cross_results,
    }


# ============================================================
# TOP-K FORMAT
# ============================================================

def top_k_results(
    results,
    mode,
):
    selected = (
        results[:TOP_K]
    )

    output = []

    for rank, row in enumerate(
        selected,
        start=1,
    ):
        if mode == "vector":
            score = (
                -float(
                    row[
                        "vector_distance"
                    ]
                )
            )

        elif mode == "bm25":
            score = float(
                row[
                    "bm25_score"
                ]
            )

        elif mode == "rrf":
            score = float(
                row[
                    "rrf_score"
                ]
            )

        elif mode == "cross":
            score = float(
                row[
                    "cross_score"
                ]
            )

        else:
            raise ValueError(
                f"Modo no soportado: {mode}"
            )

        output.append(
            {
                "rank": rank,
                "chunk_id": (
                    row["chunk_id"]
                ),
                "document_id": (
                    row[
                        "document_id"
                    ]
                ),
                "score": score,
                "text": row["text"],
                "metadata": (
                    row["metadata"]
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
            case["case_id"]
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
                "condition": condition,
                "case_id": case_id,
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
        "Vector-only": [],
        "BM25-only": [],
        "RRF": [],
        "RRF + Cross-Encoder": [],
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

        signals = (
            build_signals(
                vector_store,
                query,
                document_id,
            )
        )

        variants = {
            "Vector-only": (
                "vector",
                signals[
                    "vector"
                ],
            ),
            "BM25-only": (
                "bm25",
                signals[
                    "bm25"
                ],
            ),
            "RRF": (
                "rrf",
                signals[
                    "rrf"
                ],
            ),
            "RRF + Cross-Encoder": (
                "cross",
                signals[
                    "cross"
                ],
            ),
        }

        for (
            condition,
            (
                mode,
                result_list,
            ),
        ) in variants.items():
            results = (
                top_k_results(
                    result_list,
                    mode,
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
                    "query": query,
                    "top_k": TOP_K,
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
                    "score_type": (
                        condition
                    ),
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
                "+",
                "plus",
            )
            .replace(
                "-",
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
    # GLOBAL
    # ========================================================

    global_df = pd.DataFrame(
        summaries
    )

    print()
    print(
        "=== SIGNAL ABLATION ==="
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
    # FAILURES
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

    base = (
        gt[
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
        short = (
            condition
            .lower()
            .replace(
                " ",
                "_",
            )
            .replace(
                "+",
                "plus",
            )
            .replace(
                "-",
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

        part = (
            part.rename(
                columns={
                    col: (
                        f"{col}_{short}"
                    )
                    for col
                    in part.columns
                    if col
                    != "case_id"
                }
            )
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
    # CATEGORY
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
    # CHANGED CASES VS FULL PIPELINE
    # ========================================================

    full_df = (
        evaluation_frames[
            "RRF + Cross-Encoder"
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
            == "RRF + Cross-Encoder"
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
            full_r3 = (
                full_df.loc[
                    case_id,
                    "recall_at_3",
                ]
            )

            full_r5 = (
                full_df.loc[
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
                != full_r3
                or current_r5
                != full_r5
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
                        "recall_at_3_full": (
                            full_r3
                        ),
                        "delta_recall_at_3": (
                            current_r3
                            - full_r3
                        ),
                        "recall_at_5_condition": (
                            current_r5
                        ),
                        "recall_at_5_full": (
                            full_r5
                        ),
                        "delta_recall_at_5": (
                            current_r5
                            - full_r5
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
        print(case_id)

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
            "retrieval_v2_signal_ablation"
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
        "conditions": {
            "vector_only": {
                "vector_search": True,
                "bm25": False,
                "rrf": False,
                "cross_encoder": False,
            },
            "bm25_only": {
                "vector_search": False,
                "bm25": True,
                "rrf": False,
                "cross_encoder": False,
            },
            "rrf": {
                "vector_search": True,
                "bm25": True,
                "rrf": True,
                "cross_encoder": False,
            },
            "rrf_plus_cross_encoder": {
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