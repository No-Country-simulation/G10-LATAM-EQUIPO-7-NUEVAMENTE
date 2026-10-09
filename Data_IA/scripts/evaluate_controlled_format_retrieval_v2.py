from __future__ import annotations

import csv
import gc
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from rank_bm25 import BM25Okapi


# ============================================================
# ROOT / PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"

CORPUS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.csv"

GROUND_TRUTH_PATH = (
    DATA_IA_DIR
    / "data"
    / "evaluation"
    / "ground_truth_v2.csv"
)

REFERENCE_CHUNKS_PATH = (
    DATA_IA_DIR
    / "data"
    / "evaluation"
    / "chunks_v1.csv"
)

V1_RESULTS_DIR = CORPUS_DIR / "results"
V2_RESULTS_DIR = V1_RESULTS_DIR / "retrieval_v2"

V1_FORMAT_FILES = {
    "md": V1_RESULTS_DIR / "retrieval_md.csv",
    "txt": V1_RESULTS_DIR / "retrieval_txt.csv",
    "pdf": V1_RESULTS_DIR / "retrieval_pdf.csv",
}

V2_FORMAT_FILES = {
    "md": V2_RESULTS_DIR / "retrieval_v2_md.csv",
    "txt": V2_RESULTS_DIR / "retrieval_v2_txt.csv",
    "pdf": V2_RESULTS_DIR / "retrieval_v2_pdf.csv",
}

COMPARISON_PATH = (
    V2_RESULTS_DIR
    / "retrieval_v2_format_comparison.csv"
)

SUMMARY_PATH = (
    V2_RESULTS_DIR
    / "retrieval_v2_summary.csv"
)

V1_VS_V2_PATH = (
    V2_RESULTS_DIR
    / "retrieval_v1_vs_v2.csv"
)

REGRESSIONS_PATH = (
    V2_RESULTS_DIR
    / "retrieval_v2_regressions.csv"
)

FOCUS_CASES_PATH = (
    V2_RESULTS_DIR
    / "retrieval_v2_focus_cases.csv"
)

RUN_MANIFEST_PATH = (
    V2_RESULTS_DIR
    / "run_manifest.json"
)

README_PATH = (
    V2_RESULTS_DIR
    / "README.md"
)


# ============================================================
# EXPERIMENT CONFIG
# ============================================================

FORMATS = ("md", "txt", "pdf")

TOP_K = 5
CANDIDATE_K = TOP_K * 3
RRF_K = 60
EVIDENCE_HIT_THRESHOLD = 0.50

CROSS_ENCODER_MODEL = (
    "cross-encoder/"
    "ms-marco-MiniLM-L-6-v2"
)

FOCUS_CASE_IDS = (
    "FE-ES-001-Q01",
    "FE-ES-001-Q05",
    "CLD-ES-001-Q05",
)

INDEX_DIRS = {
    "md": ROOT / ".format_corpus_chroma_v2_md",
    "txt": ROOT / ".format_corpus_chroma_v2_txt",
    "pdf": ROOT / ".format_corpus_chroma_v2_pdf",
}

COLLECTIONS = {
    "md": "format_corpus_retrieval_v2_md",
    "txt": "format_corpus_retrieval_v2_txt",
    "pdf": "format_corpus_retrieval_v2_pdf",
}


# ============================================================
# PROJECT IMPORTS
# ============================================================

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentes.rag.extractor import extract_document  # noqa: E402
from agentes.rag.cleaner import clean_text  # noqa: E402
from agentes.rag.chunker import create_chunks  # noqa: E402
from agentes.rag.embeddings import MultilingualEmbedding  # noqa: E402
from agentes.rag.vector_store import VectorStore  # noqa: E402


# ============================================================
# GENERIC HELPERS
# ============================================================

def read_csv(path: Path) -> list[dict]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def write_csv(
    path: Path,
    rows: list[dict],
) -> None:
    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(
                rows[0].keys()
            ),
        )
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(block)

    return hasher.hexdigest()


def remove_existing_index(
    path: Path,
) -> None:
    if path.exists():
        shutil.rmtree(path)


def normalize_text(
    text: str,
) -> str:
    text = unicodedata.normalize(
        "NFKD",
        text or "",
    )

    text = "".join(
        ch
        for ch in text
        if not unicodedata.combining(ch)
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def tokenize(
    text: str,
) -> list[str]:
    return re.findall(
        r"\w+",
        normalize_text(text),
        flags=re.UNICODE,
    )


def token_set(
    text: str,
) -> set[str]:
    return set(tokenize(text))


def parse_semicolon_list(
    value: str,
) -> list[str]:
    return [
        item.strip()
        for item in (
            value or ""
        ).split(";")
        if item.strip()
    ]


def as_bool(
    value,
) -> bool:
    if isinstance(value, bool):
        return value

    return (
        str(value)
        .strip()
        .lower()
        in {
            "true",
            "1",
            "yes",
        }
    )


# ============================================================
# EVIDENCE METRICS
# ============================================================

def evidence_coverage(
    keywords: list[str],
    retrieved_text: str,
) -> tuple[
    list[str],
    int,
    int,
    float,
]:
    if not keywords:
        return [], 0, 0, 0.0

    normalized_retrieved = (
        normalize_text(
            retrieved_text
        )
    )

    matched = []

    for keyword in keywords:
        normalized_keyword = (
            normalize_text(
                keyword
            )
        )

        if (
            normalized_keyword
            and normalized_keyword
            in normalized_retrieved
        ):
            matched.append(
                keyword
            )

    total = len(keywords)
    coverage = (
        len(matched)
        / total
    )

    return (
        matched,
        len(matched),
        total,
        coverage,
    )


def reference_token_recall(
    reference_text: str,
    retrieved_text: str,
) -> float:
    reference_tokens = token_set(
        reference_text
    )
    retrieved_tokens = token_set(
        retrieved_text
    )

    if not reference_tokens:
        return 0.0

    return (
        len(
            reference_tokens
            & retrieved_tokens
        )
        / len(reference_tokens)
    )


# ============================================================
# DATA LOADERS
# ============================================================

def load_manifest() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"No existe manifest: "
            f"{MANIFEST_PATH}"
        )

    rows = read_csv(
        MANIFEST_PATH
    )

    return {
        row["document_id"]: row
        for row in rows
    }


def load_ground_truth() -> list[dict]:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            "No existe Ground Truth: "
            f"{GROUND_TRUTH_PATH}"
        )

    rows = read_csv(
        GROUND_TRUTH_PATH
    )

    if len(rows) != 50:
        raise RuntimeError(
            "Se esperaban 50 casos "
            f"y se encontraron {len(rows)}."
        )

    case_ids = {
        row["case_id"]
        for row in rows
    }

    if len(case_ids) != 50:
        raise RuntimeError(
            "Ground Truth contiene "
            "case_id duplicados."
        )

    return rows


def load_reference_chunks() -> dict[str, str]:
    if not REFERENCE_CHUNKS_PATH.exists():
        raise FileNotFoundError(
            "No existe corpus de referencia: "
            f"{REFERENCE_CHUNKS_PATH}"
        )

    rows = read_csv(
        REFERENCE_CHUNKS_PATH
    )

    return {
        row["chunk_id"]:
        row["chunk_text"]
        for row in rows
    }


def load_v1_results() -> dict[
    str,
    dict[str, dict],
]:
    output = {}

    for fmt, path in (
        V1_FORMAT_FILES.items()
    ):
        if not path.exists():
            raise FileNotFoundError(
                "Falta baseline V1: "
                f"{path}"
            )

        rows = read_csv(path)

        if len(rows) != 50:
            raise RuntimeError(
                f"{fmt}: baseline V1 "
                f"tiene {len(rows)} casos."
            )

        output[fmt] = {
            row["case_id"]: row
            for row in rows
        }

    return output


# ============================================================
# CONTROLLED FORMAT CHUNK BUILD
# ============================================================

def build_format_chunks(
    fmt: str,
    manifest: dict[str, dict],
):
    all_chunks = []

    for (
        document_id,
        row,
    ) in manifest.items():
        relative_path = (
            row[f"{fmt}_file"]
        )

        path = (
            CORPUS_DIR
            / relative_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"No existe {fmt} "
                f"para {document_id}: "
                f"{path}"
            )

        documents = extract_document(
            str(path)
        )

        for document in documents:
            document.text = clean_text(
                document.text
            )

            document.metadata[
                "document_id"
            ] = document_id

            document.metadata[
                "category"
            ] = row["category"]

            document.metadata[
                "controlled_format"
            ] = fmt

        chunks = create_chunks(
            documents
        )

        all_chunks.extend(
            chunks
        )

    return all_chunks


# ============================================================
# RETRIEVAL V2 SIGNALS
# ============================================================

def vector_search(
    vector_store,
    query: str,
    document_id: str,
) -> list[dict]:
    where_clause = {
        "document_id":
        document_id
    }

    query_embedding = (
        vector_store
        .embedding_service
        .embed_query(query)
    )

    data = (
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

    rows = []

    if not data:
        return rows

    ids = (
        data.get("ids")
        or []
    )

    if not ids or not ids[0]:
        return rows

    for rank, chunk_id in enumerate(
        ids[0],
        start=1,
    ):
        metadata = (
            data["metadatas"][0][
                rank - 1
            ]
            or {}
        )

        rows.append(
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "document_id": (
                    metadata.get(
                        "document_id"
                    )
                ),
                "text": (
                    data[
                        "documents"
                    ][0][rank - 1]
                ),
                "metadata": metadata,
                "vector_distance": (
                    float(
                        data[
                            "distances"
                        ][0][rank - 1]
                    )
                ),
            }
        )

    return rows


def bm25_search(
    vector_store,
    query: str,
    document_id: str,
) -> list[dict]:
    where_clause = {
        "document_id":
        document_id
    }

    data = (
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

    if not data:
        return []

    documents = (
        data.get("documents")
        or []
    )

    ids = (
        data.get("ids")
        or []
    )

    metadatas = (
        data.get("metadatas")
        or []
    )

    if not documents:
        return []

    tokenized_corpus = [
        tokenize(document)
        for document
        in documents
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
        key=lambda index:
        scores[index],
        reverse=True,
    )[:CANDIDATE_K]

    rows = []
    rank = 0

    for index in top_indices:
        score = float(
            scores[index]
        )

        # Mantiene el mismo criterio
        # usado en las ablaciones V2.
        if score <= 0:
            continue

        rank += 1

        metadata = (
            metadatas[index]
            or {}
        )

        rows.append(
            {
                "rank": rank,
                "chunk_id":
                ids[index],
                "document_id":
                metadata.get(
                    "document_id"
                ),
                "text":
                documents[index],
                "metadata":
                metadata,
                "bm25_score":
                score,
            }
        )

    return rows


def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
) -> list[dict]:
    fused: dict[str, dict] = {}

    def ensure_row(
        source_row: dict,
    ) -> dict:
        chunk_id = (
            source_row[
                "chunk_id"
            ]
        )

        if chunk_id not in fused:
            fused[chunk_id] = {
                "chunk_id":
                chunk_id,
                "document_id":
                source_row.get(
                    "document_id"
                ),
                "text":
                source_row["text"],
                "metadata":
                source_row.get(
                    "metadata"
                )
                or {},
                "vector_rank":
                None,
                "bm25_rank":
                None,
                "rrf_score":
                0.0,
            }

        return fused[
            chunk_id
        ]

    for row in vector_results:
        target = ensure_row(
            row
        )

        rank = int(
            row["rank"]
        )

        target[
            "vector_rank"
        ] = rank

        target[
            "rrf_score"
        ] += (
            1.0
            / (
                RRF_K
                + rank
            )
        )

    for row in bm25_results:
        target = ensure_row(
            row
        )

        rank = int(
            row["rank"]
        )

        target[
            "bm25_rank"
        ] = rank

        target[
            "rrf_score"
        ] += (
            1.0
            / (
                RRF_K
                + rank
            )
        )

    rows = sorted(
        fused.values(),
        key=lambda row:
        row["rrf_score"],
        reverse=True,
    )[:CANDIDATE_K]

    for rank, row in enumerate(
        rows,
        start=1,
    ):
        row[
            "rrf_rank"
        ] = rank

    return rows


def cross_encoder_rerank(
    vector_store,
    query: str,
    candidates: list[dict],
) -> list[dict]:
    if not candidates:
        return []

    pairs = [
        [
            query,
            row["text"],
        ]
        for row in candidates
    ]

    scores = (
        vector_store
        .reranker
        .predict(pairs)
    )

    rows = []

    for index, row in enumerate(
        candidates
    ):
        item = dict(row)

        item[
            "cross_score"
        ] = float(
            scores[index]
        )

        rows.append(
            item
        )

    rows = sorted(
        rows,
        key=lambda row:
        row["cross_score"],
        reverse=True,
    )

    for rank, row in enumerate(
        rows,
        start=1,
    ):
        row[
            "cross_rank"
        ] = rank

    return rows


def run_retrieval_v2(
    vector_store,
    query: str,
    document_id: str,
) -> dict[str, list[dict]]:
    vector_results = (
        vector_search(
            vector_store,
            query,
            document_id,
        )
    )

    bm25_results = (
        bm25_search(
            vector_store,
            query,
            document_id,
        )
    )

    rrf_results = (
        reciprocal_rank_fusion(
            vector_results,
            bm25_results,
        )
    )

    cross_results = (
        cross_encoder_rerank(
            vector_store,
            query,
            rrf_results,
        )
    )

    return {
        "vector":
        vector_results,
        "bm25":
        bm25_results,
        "rrf":
        rrf_results,
        "cross":
        cross_results,
        "final":
        cross_results[:TOP_K],
    }


# ============================================================
# FORMAT EVALUATION
# ============================================================

def evaluate_format(
    fmt: str,
    embedding_service,
    manifest: dict[str, dict],
    ground_truth: list[dict],
    reference_chunks: dict[str, str],
) -> list[dict]:
    index_dir = (
        INDEX_DIRS[fmt]
    )

    remove_existing_index(
        index_dir
    )

    print()
    print(
        "=" * 72
    )
    print(
        f"CONSTRUYENDO ÍNDICE V2 "
        f"{fmt.upper()}"
    )
    print(
        "=" * 72
    )

    chunks = build_format_chunks(
        fmt,
        manifest,
    )

    print(
        "Chunks a indexar:",
        len(chunks),
    )

    vector_store = VectorStore(
        path=str(index_dir),
        collection_name=(
            COLLECTIONS[fmt]
        ),
        embedding_service=(
            embedding_service
        ),
    )

    vector_store.add_chunks(
        chunks
    )

    print(
        f"Índice {fmt.upper()} listo."
    )
    print(
        "Pipeline: "
        "Vector + BM25 "
        "→ RRF "
        "→ Cross-Encoder "
        "→ Top-5"
    )
    print()

    output_rows = []

    for position, case in enumerate(
        ground_truth,
        start=1,
    ):
        case_id = (
            case["case_id"]
            .strip()
        )

        document_id = (
            case["document_id"]
            .strip()
        )

        query = (
            case["pregunta"]
            .strip()
        )

        signals = run_retrieval_v2(
            vector_store,
            query,
            document_id,
        )

        final_results = (
            signals["final"]
        )

        combined_text = (
            "\n\n".join(
                row["text"]
                for row
                in final_results
            )
        )

        keywords = (
            parse_semicolon_list(
                case[
                    "palabras_clave_evidencia"
                ]
            )
        )

        (
            matched_keywords,
            matched_count,
            total_keywords,
            coverage,
        ) = evidence_coverage(
            keywords,
            combined_text,
        )

        relevant_ids = (
            parse_semicolon_list(
                case[
                    "relevant_chunk_ids"
                ]
            )
        )

        reference_text = (
            "\n\n".join(
                reference_chunks[
                    chunk_id
                ]
                for chunk_id
                in relevant_ids
                if chunk_id
                in reference_chunks
            )
        )

        token_recall = (
            reference_token_recall(
                reference_text,
                combined_text,
            )
        )

        hit = (
            coverage
            >= EVIDENCE_HIT_THRESHOLD
        )

        final_chunk_ids = [
            row["chunk_id"]
            for row
            in final_results
        ]

        final_scores = [
            float(
                row["cross_score"]
            )
            for row
            in final_results
        ]

        output_rows.append(
            {
                "case_id":
                case_id,
                "document_id":
                document_id,
                "category":
                case["categoria"],
                "query":
                query,
                "format":
                fmt,
                "status":
                (
                    "success"
                    if final_results
                    else "no_results"
                ),
                "top_k_requested":
                TOP_K,
                "candidate_k":
                CANDIDATE_K,
                "rrf_k":
                RRF_K,
                "results_count":
                len(final_results),
                "evidence_keywords":
                ";".join(
                    keywords
                ),
                "matched_keywords":
                ";".join(
                    matched_keywords
                ),
                "matched_keywords_count":
                matched_count,
                "total_keywords":
                total_keywords,
                "evidence_coverage":
                round(
                    coverage,
                    6,
                ),
                "evidence_hit_threshold":
                EVIDENCE_HIT_THRESHOLD,
                "evidence_hit":
                hit,
                "reference_chunk_ids":
                ";".join(
                    relevant_ids
                ),
                "reference_token_recall":
                round(
                    token_recall,
                    6,
                ),
                "retrieved_chunk_ids":
                ";".join(
                    final_chunk_ids
                ),
                "retrieved_scores":
                ";".join(
                    f"{score:.6f}"
                    for score
                    in final_scores
                ),
                "retrieved_pages":
                ";".join(
                    str(
                        row[
                            "metadata"
                        ].get(
                            "page",
                            "",
                        )
                    )
                    for row
                    in final_results
                ),
                "vector_candidate_ids":
                ";".join(
                    row["chunk_id"]
                    for row
                    in signals[
                        "vector"
                    ]
                ),
                "bm25_candidate_ids":
                ";".join(
                    row["chunk_id"]
                    for row
                    in signals[
                        "bm25"
                    ]
                ),
                "rrf_candidate_ids":
                ";".join(
                    row["chunk_id"]
                    for row
                    in signals[
                        "rrf"
                    ]
                ),
                "retrieved_text":
                " ||| ".join(
                    row["text"].replace(
                        "\n",
                        "\\n",
                    )
                    for row
                    in final_results
                ),
            }
        )

        print(
            f"[{fmt.upper()} "
            f"{position:02d}/50] "
            f"{case_id}: "
            f"vector="
            f"{len(signals['vector'])} "
            f"bm25="
            f"{len(signals['bm25'])} "
            f"rrf="
            f"{len(signals['rrf'])} "
            f"final="
            f"{len(final_results)} "
            f"coverage="
            f"{coverage:.2f} "
            f"hit="
            f"{'YES' if hit else 'NO'}"
        )

    output_path = (
        V2_FORMAT_FILES[fmt]
    )

    write_csv(
        output_path,
        output_rows,
    )

    del vector_store
    gc.collect()

    return output_rows


# ============================================================
# SUMMARIES / COMPARISONS
# ============================================================

def build_summary(
    all_results: dict[
        str,
        list[dict],
    ],
) -> list[dict]:
    rows = []

    for fmt in FORMATS:
        results = (
            all_results[fmt]
        )

        successful = sum(
            row["status"]
            == "success"
            for row
            in results
        )

        hits = sum(
            bool(
                row[
                    "evidence_hit"
                ]
            )
            for row
            in results
        )

        mean_coverage = (
            sum(
                float(
                    row[
                        "evidence_coverage"
                    ]
                )
                for row
                in results
            )
            / len(results)
        )

        mean_token_recall = (
            sum(
                float(
                    row[
                        "reference_token_recall"
                    ]
                )
                for row
                in results
            )
            / len(results)
        )

        rows.append(
            {
                "format":
                fmt,
                "cases":
                len(results),
                "successful_queries":
                successful,
                "evidence_hits":
                hits,
                "evidence_hit_rate":
                round(
                    hits
                    / len(results),
                    6,
                ),
                "mean_evidence_coverage":
                round(
                    mean_coverage,
                    6,
                ),
                "mean_reference_token_recall":
                round(
                    mean_token_recall,
                    6,
                ),
                "top_k":
                TOP_K,
                "candidate_k":
                CANDIDATE_K,
                "rrf_k":
                RRF_K,
                "evidence_hit_threshold":
                EVIDENCE_HIT_THRESHOLD,
            }
        )

    return rows


def build_format_comparison(
    all_results: dict[
        str,
        list[dict],
    ],
) -> list[dict]:
    by_case: dict[
        str,
        dict[str, dict],
    ] = defaultdict(dict)

    for fmt, rows in (
        all_results.items()
    ):
        for row in rows:
            by_case[
                row["case_id"]
            ][fmt] = row

    output = []

    for case_id in sorted(
        by_case
    ):
        case = by_case[
            case_id
        ]

        md = case["md"]
        txt = case["txt"]
        pdf = case["pdf"]

        hit_values = {
            bool(
                md[
                    "evidence_hit"
                ]
            ),
            bool(
                txt[
                    "evidence_hit"
                ]
            ),
            bool(
                pdf[
                    "evidence_hit"
                ]
            ),
        }

        coverage_values = {
            float(
                md[
                    "evidence_coverage"
                ]
            ),
            float(
                txt[
                    "evidence_coverage"
                ]
            ),
            float(
                pdf[
                    "evidence_coverage"
                ]
            ),
        }

        output.append(
            {
                "case_id":
                case_id,
                "document_id":
                md["document_id"],
                "category":
                md["category"],
                "query":
                md["query"],
                "md_evidence_coverage":
                md[
                    "evidence_coverage"
                ],
                "txt_evidence_coverage":
                txt[
                    "evidence_coverage"
                ],
                "pdf_evidence_coverage":
                pdf[
                    "evidence_coverage"
                ],
                "md_evidence_hit":
                md[
                    "evidence_hit"
                ],
                "txt_evidence_hit":
                txt[
                    "evidence_hit"
                ],
                "pdf_evidence_hit":
                pdf[
                    "evidence_hit"
                ],
                "md_reference_token_recall":
                md[
                    "reference_token_recall"
                ],
                "txt_reference_token_recall":
                txt[
                    "reference_token_recall"
                ],
                "pdf_reference_token_recall":
                pdf[
                    "reference_token_recall"
                ],
                "format_hit_disagreement":
                len(
                    hit_values
                )
                > 1,
                "format_coverage_difference":
                len(
                    coverage_values
                )
                > 1,
            }
        )

    return output


def build_v1_vs_v2(
    all_results: dict[
        str,
        list[dict],
    ],
    v1_results: dict[
        str,
        dict[str, dict],
    ],
) -> tuple[
    list[dict],
    list[dict],
]:
    comparison = []
    regressions = []

    for fmt in FORMATS:
        for v2 in (
            all_results[fmt]
        ):
            case_id = (
                v2["case_id"]
            )

            v1 = (
                v1_results[
                    fmt
                ][case_id]
            )

            v1_hit = as_bool(
                v1[
                    "evidence_hit"
                ]
            )

            v2_hit = bool(
                v2[
                    "evidence_hit"
                ]
            )

            v1_coverage = float(
                v1[
                    "evidence_coverage"
                ]
            )

            v2_coverage = float(
                v2[
                    "evidence_coverage"
                ]
            )

            v1_token = float(
                v1[
                    "reference_token_recall"
                ]
            )

            v2_token = float(
                v2[
                    "reference_token_recall"
                ]
            )

            if (
                not v1_hit
                and v2_hit
            ):
                change = (
                    "improved_hit"
                )
            elif (
                v1_hit
                and not v2_hit
            ):
                change = (
                    "regressed_hit"
                )
            elif (
                v2_coverage
                > v1_coverage
            ):
                change = (
                    "improved_coverage"
                )
            elif (
                v2_coverage
                < v1_coverage
            ):
                change = (
                    "regressed_coverage"
                )
            else:
                change = (
                    "unchanged_hit_coverage"
                )

            row = {
                "case_id":
                case_id,
                "document_id":
                v2[
                    "document_id"
                ],
                "category":
                v2[
                    "category"
                ],
                "format":
                fmt,
                "query":
                v2[
                    "query"
                ],
                "v1_evidence_hit":
                v1_hit,
                "v2_evidence_hit":
                v2_hit,
                "v1_evidence_coverage":
                round(
                    v1_coverage,
                    6,
                ),
                "v2_evidence_coverage":
                round(
                    v2_coverage,
                    6,
                ),
                "delta_evidence_coverage":
                round(
                    v2_coverage
                    - v1_coverage,
                    6,
                ),
                "v1_reference_token_recall":
                round(
                    v1_token,
                    6,
                ),
                "v2_reference_token_recall":
                round(
                    v2_token,
                    6,
                ),
                "delta_reference_token_recall":
                round(
                    v2_token
                    - v1_token,
                    6,
                ),
                "change":
                change,
            }

            comparison.append(
                row
            )

            # Regresión primaria:
            # hit V1 pasa a no-hit V2.
            # También guardamos caídas
            # de coverage para revisión.
            if change in {
                "regressed_hit",
                "regressed_coverage",
            }:
                regressions.append(
                    row
                )

    return (
        comparison,
        regressions,
    )


def build_focus_cases(
    v1_vs_v2: list[dict],
) -> list[dict]:
    return [
        row
        for row
        in v1_vs_v2
        if row["case_id"]
        in FOCUS_CASE_IDS
    ]


# ============================================================
# DOCUMENTATION
# ============================================================

def build_readme(
    summary: list[dict],
    v1_vs_v2: list[dict],
    regressions: list[dict],
    focus_rows: list[dict],
) -> str:
    summary_by_format = {
        row["format"]:
        row
        for row in summary
    }

    improved_hits = [
        row
        for row
        in v1_vs_v2
        if row["change"]
        == "improved_hit"
    ]

    regressed_hits = [
        row
        for row
        in v1_vs_v2
        if row["change"]
        == "regressed_hit"
    ]

    lines = [
        "# Controlled Format Retrieval v2",
        "",
        "## Objetivo",
        "",
        "Evaluar el corpus controlado Markdown/TXT/PDF con el pipeline híbrido",
        "de Retrieval V2 ya validado para NuevaMente.",
        "",
        "Pipeline:",
        "",
        "```text",
        "document_id filter",
        "→ Vector Search",
        "+ BM25",
        "→ RRF 50/50",
        "→ candidate overfetch (Top-K × 3)",
        "→ Cross-Encoder",
        "→ Top-5",
        "```",
        "",
        "## Configuración",
        "",
        f"- Queries: 50",
        f"- Formatos: MD, TXT, PDF",
        f"- Top-K final: {TOP_K}",
        f"- Candidate-K: {CANDIDATE_K}",
        f"- RRF k: {RRF_K}",
        f"- Cross-Encoder: `{CROSS_ENCODER_MODEL}`",
        f"- Evidence hit threshold: {EVIDENCE_HIT_THRESHOLD:.2f}",
        "",
        "## Resultados V2",
        "",
        "| Formato | Hits | Hit rate | Evidence coverage | Reference token recall |",
        "|---|---:|---:|---:|---:|",
    ]

    for fmt in FORMATS:
        row = summary_by_format[
            fmt
        ]

        lines.append(
            f"| {fmt.upper()} | "
            f"{row['evidence_hits']}/"
            f"{row['cases']} | "
            f"{float(row['evidence_hit_rate']):.2%} | "
            f"{float(row['mean_evidence_coverage']):.4f} | "
            f"{float(row['mean_reference_token_recall']):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Cambios frente a Vector-only v1",
            "",
            f"- Casos/formato que pasan de NO HIT a HIT: **{len(improved_hits)}**.",
            f"- Regresiones de HIT a NO HIT: **{len(regressed_hits)}**.",
            f"- Filas marcadas para revisión por hit/coverage: **{len(regressions)}**.",
            "",
            "## Casos foco",
            "",
            "| Caso | Formato | V1 hit | V2 hit | V1 coverage | V2 coverage | Cambio |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )

    for row in focus_rows:
        lines.append(
            f"| {row['case_id']} | "
            f"{row['format'].upper()} | "
            f"{row['v1_evidence_hit']} | "
            f"{row['v2_evidence_hit']} | "
            f"{float(row['v1_evidence_coverage']):.4f} | "
            f"{float(row['v2_evidence_coverage']):.4f} | "
            f"`{row['change']}` |"
        )

    lines.extend(
        [
            "",
            "## Artefactos",
            "",
            "- `retrieval_v2_md.csv`",
            "- `retrieval_v2_txt.csv`",
            "- `retrieval_v2_pdf.csv`",
            "- `retrieval_v2_format_comparison.csv`",
            "- `retrieval_v2_summary.csv`",
            "- `retrieval_v1_vs_v2.csv`",
            "- `retrieval_v2_regressions.csv`",
            "- `retrieval_v2_focus_cases.csv`",
            "- `run_manifest.json`",
            "",
            "## Nota metodológica",
            "",
            "Esta evaluación no usa `relevant_chunk_ids` como métrica primaria",
            "porque el corpus controlado se vuelve a extraer y chunkear por formato.",
            "La comparación se basa en evidencia textual equivalente y",
            "`reference_token_recall`.",
            "",
            "El benchmark histórico Retrieval V1/V2 permanece sin modificaciones.",
        ]
    )

    return (
        "\n".join(lines)
        + "\n"
    )


def build_run_manifest(
    summary: list[dict],
    v1_vs_v2: list[dict],
) -> dict:
    improved_hits = [
        row
        for row
        in v1_vs_v2
        if row["change"]
        == "improved_hit"
    ]

    regressed_hits = [
        row
        for row
        in v1_vs_v2
        if row["change"]
        == "regressed_hit"
    ]

    return {
        "experiment_name":
        (
            "NuevaMente Controlled "
            "Format Retrieval v2"
        ),
        "experiment_version":
        "v2",
        "generated_at_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),
        "baseline":
        {
            "name":
            (
                "Controlled Format "
                "Retrieval v1"
            ),
            "retrieval":
            "vector_only",
        },
        "corpus":
        {
            "name":
            "format_corpus_v1",
            "documents":
            len(
                load_manifest()
            ),
            "formats":
            list(FORMATS),
            "separate_indexes":
            True,
        },
        "query_policy":
        {
            "source":
            (
                "ground_truth_v2."
                "pregunta"
            ),
            "cases":
            50,
            "metadata_filter":
            "document_id",
        },
        "retrieval_v2":
        {
            "vector_search":
            True,
            "bm25":
            True,
            "rrf":
            True,
            "rrf_k":
            RRF_K,
            "vector_weight":
            0.50,
            "bm25_weight":
            0.50,
            "candidate_overfetch_factor":
            3,
            "candidate_k":
            CANDIDATE_K,
            "cross_encoder":
            True,
            "cross_encoder_model":
            CROSS_ENCODER_MODEL,
            "top_k":
            TOP_K,
        },
        "evaluation":
        {
            "primary_metric":
            "evidence_hit",
            "evidence_hit_threshold":
            EVIDENCE_HIT_THRESHOLD,
            "supporting_metrics":
            [
                "evidence_coverage",
                "reference_token_recall",
            ],
        },
        "results":
        {
            row["format"]:
            {
                "cases":
                row["cases"],
                "evidence_hits":
                row[
                    "evidence_hits"
                ],
                "evidence_hit_rate":
                row[
                    "evidence_hit_rate"
                ],
                "mean_evidence_coverage":
                row[
                    "mean_evidence_coverage"
                ],
                "mean_reference_token_recall":
                row[
                    "mean_reference_token_recall"
                ],
            }
            for row
            in summary
        },
        "v1_vs_v2":
        {
            "improved_hit_rows":
            len(improved_hits),
            "regressed_hit_rows":
            len(regressed_hits),
            "improved_hit_cases":
            sorted(
                {
                    row["case_id"]
                    for row
                    in improved_hits
                }
            ),
            "regressed_hit_cases":
            sorted(
                {
                    row["case_id"]
                    for row
                    in regressed_hits
                }
            ),
        },
        "hashes_sha256":
        {
            "ground_truth_v2.csv":
            sha256_file(
                GROUND_TRUTH_PATH
            ),
            "chunks_v1.csv":
            sha256_file(
                REFERENCE_CHUNKS_PATH
            ),
            "format_corpus_manifest.csv":
            sha256_file(
                MANIFEST_PATH
            ),
            "retrieval_v1_md.csv":
            sha256_file(
                V1_FORMAT_FILES["md"]
            ),
            "retrieval_v1_txt.csv":
            sha256_file(
                V1_FORMAT_FILES["txt"]
            ),
            "retrieval_v1_pdf.csv":
            sha256_file(
                V1_FORMAT_FILES["pdf"]
            ),
        },
        "guardrails":
        [
            (
                "No sobrescribir "
                "Controlled Format v1."
            ),
            (
                "No modificar "
                "ground_truth_v2.csv."
            ),
            (
                "No modificar "
                "chunks_v1.csv."
            ),
            (
                "No versionar "
                "índices Chroma locales."
            ),
            (
                "No concluir mejora "
                "solo por casos foco; "
                "revisar las 150 "
                "comparaciones formato/caso."
            ),
        ],
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_required_files() -> None:
    required = [
        MANIFEST_PATH,
        GROUND_TRUTH_PATH,
        REFERENCE_CHUNKS_PATH,
        *V1_FORMAT_FILES.values(),
    ]

    missing = [
        path
        for path in required
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Faltan archivos requeridos:\n"
            + "\n".join(
                str(path)
                for path
                in missing
            )
        )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    validate_required_files()

    V2_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = load_manifest()
    ground_truth = (
        load_ground_truth()
    )
    reference_chunks = (
        load_reference_chunks()
    )
    v1_results = (
        load_v1_results()
    )

    print(
        "=== CONTROLLED FORMAT "
        "RETRIEVAL V2 ==="
    )
    print(
        "Casos:",
        len(ground_truth),
    )
    print(
        "Documentos:",
        len(manifest),
    )
    print(
        "Formatos:",
        ", ".join(
            fmt.upper()
            for fmt
            in FORMATS
        ),
    )
    print(
        "Top-K:",
        TOP_K,
    )
    print(
        "Candidate-K:",
        CANDIDATE_K,
    )
    print(
        "RRF k:",
        RRF_K,
    )
    print(
        "Pipeline: "
        "Vector + BM25 "
        "→ RRF 50/50 "
        "→ Cross-Encoder "
        "→ Top-5"
    )
    print(
        "Evidence hit threshold:",
        EVIDENCE_HIT_THRESHOLD,
    )
    print()
    print(
        "Cargando embeddings "
        "una sola vez..."
    )

    embedding_service = (
        MultilingualEmbedding()
    )

    all_results: dict[
        str,
        list[dict],
    ] = {}

    for fmt in FORMATS:
        all_results[fmt] = (
            evaluate_format(
                fmt=fmt,
                embedding_service=(
                    embedding_service
                ),
                manifest=manifest,
                ground_truth=(
                    ground_truth
                ),
                reference_chunks=(
                    reference_chunks
                ),
            )
        )

    summary = build_summary(
        all_results
    )

    format_comparison = (
        build_format_comparison(
            all_results
        )
    )

    (
        v1_vs_v2,
        regressions,
    ) = build_v1_vs_v2(
        all_results,
        v1_results,
    )

    focus_rows = (
        build_focus_cases(
            v1_vs_v2
        )
    )

    write_csv(
        SUMMARY_PATH,
        summary,
    )

    write_csv(
        COMPARISON_PATH,
        format_comparison,
    )

    write_csv(
        V1_VS_V2_PATH,
        v1_vs_v2,
    )

    # Queremos crear el archivo
    # aun cuando no existan regresiones.
    if regressions:
        write_csv(
            REGRESSIONS_PATH,
            regressions,
        )
    else:
        REGRESSIONS_PATH.write_text(
            (
                "case_id,document_id,"
                "category,format,query,"
                "v1_evidence_hit,"
                "v2_evidence_hit,"
                "v1_evidence_coverage,"
                "v2_evidence_coverage,"
                "delta_evidence_coverage,"
                "v1_reference_token_recall,"
                "v2_reference_token_recall,"
                "delta_reference_token_recall,"
                "change\n"
            ),
            encoding="utf-8",
        )

    write_csv(
        FOCUS_CASES_PATH,
        focus_rows,
    )

    run_manifest = (
        build_run_manifest(
            summary,
            v1_vs_v2,
        )
    )

    RUN_MANIFEST_PATH.write_text(
        json.dumps(
            run_manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    README_PATH.write_text(
        build_readme(
            summary,
            v1_vs_v2,
            regressions,
            focus_rows,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=" * 72
    )
    print(
        "RESUMEN FINAL"
    )
    print(
        "=" * 72
    )

    for row in summary:
        print(
            f"{row['format'].upper()}: "
            f"{row['evidence_hits']}/"
            f"{row['cases']} hits "
            f"("
            f"{row['evidence_hit_rate']:.2%}"
            f") | "
            f"coverage="
            f"{row['mean_evidence_coverage']:.4f} | "
            f"reference_recall="
            f"{row['mean_reference_token_recall']:.4f}"
        )

    improved_hits = [
        row
        for row
        in v1_vs_v2
        if row["change"]
        == "improved_hit"
    ]

    regressed_hits = [
        row
        for row
        in v1_vs_v2
        if row["change"]
        == "regressed_hit"
    ]

    print()
    print(
        "V1 → V2:"
    )
    print(
        "  Improved hit rows:",
        len(improved_hits),
    )
    print(
        "  Regressed hit rows:",
        len(regressed_hits),
    )
    print(
        "  Total review rows "
        "(hit/coverage regression):",
        len(regressions),
    )

    print()
    print(
        "Casos foco:"
    )

    for row in focus_rows:
        print(
            f"  {row['case_id']} "
            f"[{row['format'].upper()}] "
            f"V1="
            f"{row['v1_evidence_coverage']:.2f}/"
            f"{'HIT' if row['v1_evidence_hit'] else 'NO'} "
            f"→ "
            f"V2="
            f"{row['v2_evidence_coverage']:.2f}/"
            f"{'HIT' if row['v2_evidence_hit'] else 'NO'} "
            f"({row['change']})"
        )

    print()
    print(
        "Artefactos:"
    )
    print(
        V2_RESULTS_DIR
    )
    print(
        "  retrieval_v2_md.csv"
    )
    print(
        "  retrieval_v2_txt.csv"
    )
    print(
        "  retrieval_v2_pdf.csv"
    )
    print(
        "  retrieval_v2_format_comparison.csv"
    )
    print(
        "  retrieval_v2_summary.csv"
    )
    print(
        "  retrieval_v1_vs_v2.csv"
    )
    print(
        "  retrieval_v2_regressions.csv"
    )
    print(
        "  retrieval_v2_focus_cases.csv"
    )
    print(
        "  run_manifest.json"
    )
    print(
        "  README.md"
    )


if __name__ == "__main__":
    main()
