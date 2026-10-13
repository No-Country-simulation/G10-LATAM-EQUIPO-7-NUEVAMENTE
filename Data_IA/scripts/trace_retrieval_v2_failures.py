from pathlib import Path
import sys
import re

import pandas as pd
from rank_bm25 import BM25Okapi


# ============================================================
# RAÍZ DEL PROYECTO
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.vector_store import VectorStore
from agentes.rag.pipeline import ingest_ground_truth_v1


# ============================================================
# CONFIGURACIÓN
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
    / "trace_failures"
)

CHROMA_PATH = ROOT / ".benchmark_chroma_v2_trace"

COLLECTION_NAME = "benchmark_retrieval_v2_trace"

TOP_K = 5
CANDIDATE_K = TOP_K * 3
RRF_K = 60

TARGET_CASES = [
    "BE-ES-002-Q03",
    "CLD-ES-001-Q05",
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
    return re.findall(r"\w+", str(text).lower())


def print_stage(title, df, relevant_ids):
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)

    if df.empty:
        print("Sin resultados.")
        return

    show = df.copy()

    show["is_relevant"] = show["chunk_id"].isin(
        relevant_ids
    )

    columns = [
        col
        for col in [
            "rank",
            "chunk_id",
            "document_id",
            "score",
            "rrf_score",
            "vector_rank",
            "bm25_rank",
            "cross_score",
            "is_relevant",
        ]
        if col in show.columns
    ]

    print(
        show[columns].to_string(
            index=False
        )
    )


# ============================================================
# TRAZABILIDAD DE UN CASO
# ============================================================

def trace_case(
    vector_store,
    case_id,
    query,
    document_id,
    relevant_ids,
):
    print()
    print("#" * 100)
    print("CASE:", case_id)
    print("DOCUMENT:", document_id)
    print("QUERY:", query)
    print("RELEVANT:", relevant_ids)
    print("#" * 100)

    where_clause = {
        "document_id": document_id
    }

    # ========================================================
    # 1. EMBEDDING DE QUERY
    # ========================================================

    query_embedding = (
        vector_store
        .embedding_service
        .embed_query(query)
    )

    # ========================================================
    # 2. VECTOR SEARCH
    # ========================================================

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

    vector_rows = []

    vector_ids = (
        vector_data["ids"][0]
        if vector_data
        and vector_data.get("ids")
        else []
    )

    for index, chunk_id in enumerate(
        vector_ids
    ):
        metadata = (
            vector_data["metadatas"][0][index]
            or {}
        )

        vector_rows.append(
            {
                "rank": index + 1,
                "chunk_id": chunk_id,
                "document_id": metadata.get(
                    "document_id"
                ),
                "score": (
                    vector_data[
                        "distances"
                    ][0][index]
                ),
                "text": (
                    vector_data[
                        "documents"
                    ][0][index]
                ),
            }
        )

    vector_df = pd.DataFrame(
        vector_rows
    )

    print_stage(
        "FASE 1 — VECTOR SEARCH",
        vector_df,
        relevant_ids,
    )

    # ========================================================
    # 3. BM25
    # ========================================================

    filtered_data = (
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

    documents = (
        filtered_data.get(
            "documents",
            []
        )
        or []
    )

    ids = (
        filtered_data.get(
            "ids",
            []
        )
        or []
    )

    metadatas = (
        filtered_data.get(
            "metadatas",
            []
        )
        or []
    )

    bm25_rows = []

    if documents:
        tokenized_corpus = [
            tokenize(doc)
            for doc in documents
        ]

        bm25 = BM25Okapi(
            tokenized_corpus
        )

        query_tokens = tokenize(query)

        bm25_scores = bm25.get_scores(
            query_tokens
        )

        sorted_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:CANDIDATE_K]

        bm25_rank = 0

        for i in sorted_indices:
            if bm25_scores[i] <= 0:
                continue

            bm25_rank += 1

            metadata = (
                metadatas[i]
                or {}
            )

            bm25_rows.append(
                {
                    "rank": bm25_rank,
                    "chunk_id": ids[i],
                    "document_id": metadata.get(
                        "document_id"
                    ),
                    "score": float(
                        bm25_scores[i]
                    ),
                    "text": documents[i],
                }
            )

    bm25_df = pd.DataFrame(
        bm25_rows
    )

    print_stage(
        "FASE 2 — BM25",
        bm25_df,
        relevant_ids,
    )

    # ========================================================
    # 4. RRF
    # ========================================================

    rrf = {}

    for index, row in enumerate(
        vector_rows
    ):
        chunk_id = row["chunk_id"]

        if chunk_id not in rrf:
            rrf[chunk_id] = {
                "chunk_id": chunk_id,
                "text": row["text"],
                "document_id": row[
                    "document_id"
                ],
                "rrf_score": 0.0,
                "vector_rank": None,
                "bm25_rank": None,
            }

        rrf[chunk_id][
            "vector_rank"
        ] = index + 1

        rrf[chunk_id][
            "rrf_score"
        ] += (
            1.0
            / (
                RRF_K
                + index
                + 1
            )
        )

    for index, row in enumerate(
        bm25_rows
    ):
        chunk_id = row["chunk_id"]

        if chunk_id not in rrf:
            rrf[chunk_id] = {
                "chunk_id": chunk_id,
                "text": row["text"],
                "document_id": row[
                    "document_id"
                ],
                "rrf_score": 0.0,
                "vector_rank": None,
                "bm25_rank": None,
            }

        rrf[chunk_id][
            "bm25_rank"
        ] = index + 1

        rrf[chunk_id][
            "rrf_score"
        ] += (
            1.0
            / (
                RRF_K
                + index
                + 1
            )
        )

    hybrid_candidates = sorted(
        rrf.values(),
        key=lambda x: x[
            "rrf_score"
        ],
        reverse=True,
    )[:CANDIDATE_K]

    rrf_rows = []

    for index, candidate in enumerate(
        hybrid_candidates
    ):
        rrf_rows.append(
            {
                "rank": index + 1,
                **candidate,
            }
        )

    rrf_df = pd.DataFrame(
        rrf_rows
    )

    print_stage(
        "FASE 3 — RRF / CANDIDATOS AL CROSS-ENCODER",
        rrf_df,
        relevant_ids,
    )

    # ========================================================
    # 5. CROSS-ENCODER
    # ========================================================

    cross_pairs = [
        [
            query,
            candidate["text"],
        ]
        for candidate
        in hybrid_candidates
    ]

    cross_scores = (
        vector_store
        .reranker
        .predict(cross_pairs)
    )

    cross_rows = []

    for index, candidate in enumerate(
        hybrid_candidates
    ):
        cross_rows.append(
            {
                "chunk_id": candidate[
                    "chunk_id"
                ],
                "document_id": candidate[
                    "document_id"
                ],
                "vector_rank": candidate[
                    "vector_rank"
                ],
                "bm25_rank": candidate[
                    "bm25_rank"
                ],
                "rrf_score": candidate[
                    "rrf_score"
                ],
                "cross_score": float(
                    cross_scores[index]
                ),
                "text": candidate[
                    "text"
                ],
            }
        )

    cross_rows = sorted(
        cross_rows,
        key=lambda x: x[
            "cross_score"
        ],
        reverse=True,
    )

    for index, row in enumerate(
        cross_rows
    ):
        row["rank"] = index + 1

    cross_df = pd.DataFrame(
        cross_rows
    )

    print_stage(
        "FASE 4 — CROSS-ENCODER",
        cross_df,
        relevant_ids,
    )

    # ========================================================
    # 6. TOP 5 FINAL
    # ========================================================

    final_df = (
        cross_df
        .head(TOP_K)
        .copy()
    )

    print_stage(
        "TOP-5 FINAL",
        final_df,
        relevant_ids,
    )

    # ========================================================
    # 7. DIAGNÓSTICO AUTOMÁTICO
    # ========================================================

    relevant_set = set(
        relevant_ids
    )

    vector_found = bool(
        relevant_set.intersection(
            set(
                vector_df.get(
                    "chunk_id",
                    []
                )
            )
        )
    )

    bm25_found = bool(
        relevant_set.intersection(
            set(
                bm25_df.get(
                    "chunk_id",
                    []
                )
            )
        )
    )

    rrf_found = bool(
        relevant_set.intersection(
            set(
                rrf_df.get(
                    "chunk_id",
                    []
                )
            )
        )
    )

    final_found = bool(
        relevant_set.intersection(
            set(
                final_df.get(
                    "chunk_id",
                    []
                )
            )
        )
    )

    if not vector_found and not bm25_found:
        diagnosis = (
            "candidate_generation_failure"
        )

    elif (
        vector_found
        or bm25_found
    ) and not rrf_found:
        diagnosis = (
            "rrf_candidate_cutoff"
        )

    elif rrf_found and not final_found:
        diagnosis = (
            "cross_encoder_reranking_failure"
        )

    else:
        diagnosis = (
            "retrieved_in_top5"
        )

    print()
    print("DIAGNÓSTICO")
    print("-" * 60)
    print(
        "Relevant in vector:",
        vector_found,
    )
    print(
        "Relevant in BM25:",
        bm25_found,
    )
    print(
        "Relevant after RRF:",
        rrf_found,
    )
    print(
        "Relevant in final Top-5:",
        final_found,
    )
    print(
        "Root cause:",
        diagnosis,
    )

    # ========================================================
    # 8. EXPORTAR TRACE
    # ========================================================

    case_dir = (
        OUTPUT_DIR
        / case_id
    )

    case_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    vector_df.to_csv(
        case_dir
        / "01_vector_search.csv",
        index=False,
        encoding="utf-8-sig",
    )

    bm25_df.to_csv(
        case_dir
        / "02_bm25.csv",
        index=False,
        encoding="utf-8-sig",
    )

    rrf_df.to_csv(
        case_dir
        / "03_rrf_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )

    cross_df.to_csv(
        case_dir
        / "04_cross_encoder.csv",
        index=False,
        encoding="utf-8-sig",
    )

    final_df.to_csv(
        case_dir
        / "05_final_top5.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return {
        "case_id": case_id,
        "document_id": document_id,
        "relevant_chunk_ids": ";".join(
            relevant_ids
        ),
        "relevant_in_vector": vector_found,
        "relevant_in_bm25": bm25_found,
        "relevant_after_rrf": rrf_found,
        "relevant_in_final_top5": final_found,
        "diagnosis": diagnosis,
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

    gt = pd.read_csv(
        GROUND_TRUTH_PATH,
        encoding="utf-8-sig",
    )

    targets = gt[
        gt["case_id"].isin(
            TARGET_CASES
        )
    ].copy()

    assert len(targets) == 2, (
        "No se localizaron los dos casos objetivo."
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
        path=str(CHROMA_PATH),
        collection_name=COLLECTION_NAME,
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

    summaries = []

    for _, row in targets.iterrows():
        summaries.append(
            trace_case(
                vector_store=vector_store,
                case_id=str(
                    row["case_id"]
                ).strip(),
                query=str(
                    row["pregunta"]
                ).strip(),
                document_id=str(
                    row["document_id"]
                ).strip(),
                relevant_ids=(
                    parse_relevant_ids(
                        row[
                            "relevant_chunk_ids"
                        ]
                    )
                ),
            )
        )

    summary_df = pd.DataFrame(
        summaries
    )

    summary_path = (
        OUTPUT_DIR
        / "trace_summary.csv"
    )

    summary_df.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 90)
    print("RESUMEN FINAL")
    print("=" * 90)
    print(
        summary_df.to_string(
            index=False
        )
    )

    print()
    print(
        "Artefactos:",
        OUTPUT_DIR,
    )


if __name__ == "__main__":
    main()