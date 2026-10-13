from __future__ import annotations

import csv
import gc
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"

CORPUS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.csv"
GROUND_TRUTH_PATH = DATA_IA_DIR / "data" / "evaluation" / "ground_truth_v2.csv"
V2_RESULTS_DIR = CORPUS_DIR / "results" / "retrieval_v2"
TRACE_OUTPUT_DIR = V2_RESULTS_DIR / "trace_focus_cases"

FORMATS = ("md", "txt", "pdf")
TARGET_CASES = ("FE-ES-001-Q01", "CLD-ES-001-Q05")

TOP_K = 5
CANDIDATE_K = TOP_K * 3
RRF_K = 60
EVIDENCE_HIT_THRESHOLD = 0.50

INDEX_DIRS = {
    "md": ROOT / ".format_trace_v2_md",
    "txt": ROOT / ".format_trace_v2_txt",
    "pdf": ROOT / ".format_trace_v2_pdf",
}

COLLECTIONS = {
    "md": "format_trace_v2_md",
    "txt": "format_trace_v2_txt",
    "pdf": "format_trace_v2_pdf",
}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentes.rag.extractor import extract_document
from agentes.rag.cleaner import clean_text
from agentes.rag.chunker import create_chunks
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.vector_store import VectorStore


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text.lower())
    return text.strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", normalize_text(text), flags=re.UNICODE)


def parse_semicolon_list(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def evidence_matches(keywords: list[str], text: str) -> list[str]:
    normalized = normalize_text(text)
    matches = []
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in normalized:
            matches.append(keyword)
    return matches


def evidence_coverage(keywords: list[str], text: str) -> float:
    if not keywords:
        return 0.0
    return len(evidence_matches(keywords, text)) / len(keywords)


def remove_existing_index(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def load_manifest() -> dict[str, dict]:
    return {row["document_id"]: row for row in read_csv(MANIFEST_PATH)}


def load_targets() -> list[dict]:
    gt = pd.read_csv(GROUND_TRUTH_PATH, encoding="utf-8-sig")
    targets = gt[gt["case_id"].isin(TARGET_CASES)].copy()
    if targets["case_id"].nunique() != len(TARGET_CASES):
        raise RuntimeError("No se localizaron todos los TARGET_CASES.")
    return targets.to_dict("records")


def build_format_chunks(fmt: str, manifest: dict[str, dict]):
    all_chunks = []
    for document_id, row in manifest.items():
        path = CORPUS_DIR / row[f"{fmt}_file"]
        documents = extract_document(str(path))
        for document in documents:
            document.text = clean_text(document.text)
            document.metadata["document_id"] = document_id
            document.metadata["category"] = row["category"]
            document.metadata["controlled_format"] = fmt
        all_chunks.extend(create_chunks(documents))
    return all_chunks


def vector_search(vector_store, query: str, document_id: str) -> list[dict]:
    query_embedding = vector_store.embedding_service.embed_query(query)
    data = vector_store.collection.query(
        query_embeddings=[query_embedding],
        n_results=CANDIDATE_K,
        where={"document_id": document_id},
        include=["documents", "metadatas", "distances"],
    )
    rows = []
    ids = (data or {}).get("ids") or []
    if not ids or not ids[0]:
        return rows
    for rank, chunk_id in enumerate(ids[0], start=1):
        metadata = data["metadatas"][0][rank - 1] or {}
        rows.append({
            "rank": rank,
            "chunk_id": chunk_id,
            "document_id": metadata.get("document_id"),
            "score": -float(data["distances"][0][rank - 1]),
            "distance": float(data["distances"][0][rank - 1]),
            "text": data["documents"][0][rank - 1],
            "metadata": metadata,
        })
    return rows


def bm25_search(vector_store, query: str, document_id: str) -> list[dict]:
    data = vector_store.collection.get(
        where={"document_id": document_id},
        include=["documents", "metadatas"],
    )
    if not data:
        return []
    documents = data.get("documents") or []
    ids = data.get("ids") or []
    metadatas = data.get("metadatas") or []
    if not documents:
        return []

    bm25 = BM25Okapi([tokenize(document) for document in documents])
    scores = bm25.get_scores(tokenize(query))
    top_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )[:CANDIDATE_K]

    rows = []
    rank = 0
    for index in top_indices:
        score = float(scores[index])
        if score <= 0:
            continue
        rank += 1
        metadata = metadatas[index] or {}
        rows.append({
            "rank": rank,
            "chunk_id": ids[index],
            "document_id": metadata.get("document_id"),
            "score": score,
            "text": documents[index],
            "metadata": metadata,
        })
    return rows


def reciprocal_rank_fusion(vector_rows: list[dict], bm25_rows: list[dict]) -> list[dict]:
    fused = {}

    def ensure_item(row: dict) -> dict:
        chunk_id = row["chunk_id"]
        if chunk_id not in fused:
            fused[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": row.get("document_id"),
                "text": row["text"],
                "metadata": row.get("metadata") or {},
                "vector_rank": None,
                "bm25_rank": None,
                "rrf_score": 0.0,
            }
        return fused[chunk_id]

    for row in vector_rows:
        item = ensure_item(row)
        rank = int(row["rank"])
        item["vector_rank"] = rank
        item["rrf_score"] += 1.0 / (RRF_K + rank)

    for row in bm25_rows:
        item = ensure_item(row)
        rank = int(row["rank"])
        item["bm25_rank"] = rank
        item["rrf_score"] += 1.0 / (RRF_K + rank)

    rows = sorted(fused.values(), key=lambda row: row["rrf_score"], reverse=True)[:CANDIDATE_K]
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def cross_encoder_rerank(vector_store, query: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []
    pairs = [[query, row["text"]] for row in candidates]
    scores = vector_store.reranker.predict(pairs)
    rows = []
    for index, row in enumerate(candidates):
        item = dict(row)
        item["cross_score"] = float(scores[index])
        rows.append(item)
    rows = sorted(rows, key=lambda row: row["cross_score"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def enrich_rows(rows: list[dict], keywords: list[str]) -> list[dict]:
    output = []
    cumulative_text = ""
    for row in rows:
        cumulative_text += "\n\n" + row["text"]
        chunk_matches = evidence_matches(keywords, row["text"])
        cumulative_matches = evidence_matches(keywords, cumulative_text)
        chunk_coverage = len(chunk_matches) / len(keywords) if keywords else 0.0
        cumulative_coverage = len(cumulative_matches) / len(keywords) if keywords else 0.0
        output.append({
            "rank": row["rank"],
            "chunk_id": row["chunk_id"],
            "document_id": row.get("document_id"),
            "vector_rank": row.get("vector_rank"),
            "bm25_rank": row.get("bm25_rank"),
            "score": row.get("score"),
            "rrf_score": row.get("rrf_score"),
            "cross_score": row.get("cross_score"),
            "matched_keywords": ";".join(chunk_matches),
            "chunk_evidence_coverage": round(chunk_coverage, 6),
            "cumulative_matched_keywords": ";".join(cumulative_matches),
            "cumulative_evidence_coverage": round(cumulative_coverage, 6),
            "threshold_reached": cumulative_coverage >= EVIDENCE_HIT_THRESHOLD,
            "text": row["text"],
        })
    return output


def first_threshold_rank(rows: list[dict]) -> int | None:
    for row in rows:
        if row["threshold_reached"]:
            return int(row["rank"])
    return None


def stage_diagnosis(vector_rows, bm25_rows, rrf_rows, cross_rows) -> str:
    vector_rank = first_threshold_rank(vector_rows)
    bm25_rank = first_threshold_rank(bm25_rows)
    rrf_rank = first_threshold_rank(rrf_rows)
    cross_rank = first_threshold_rank(cross_rows)

    if cross_rank is not None and cross_rank <= TOP_K:
        return "retrieved_in_final_top5"
    if vector_rank is None and bm25_rank is None:
        return "candidate_generation_failure"
    if rrf_rank is None:
        return "rrf_candidate_cutoff"
    if cross_rank is None:
        return "cross_encoder_drops_evidence_outside_candidate_pool"
    if rrf_rank <= TOP_K and cross_rank > TOP_K:
        return "cross_encoder_reranking_failure"
    if rrf_rank > TOP_K and cross_rank > TOP_K:
        return "hybrid_ranking_not_sufficient"
    return "ranking_issue"


def trace_case(vector_store, fmt: str, case: dict) -> dict:
    case_id = str(case["case_id"]).strip()
    document_id = str(case["document_id"]).strip()
    query = str(case["pregunta"]).strip()
    keywords = parse_semicolon_list(str(case["palabras_clave_evidencia"]))

    vector = vector_search(vector_store, query, document_id)
    bm25 = bm25_search(vector_store, query, document_id)
    rrf = reciprocal_rank_fusion(vector, bm25)
    cross = cross_encoder_rerank(vector_store, query, rrf)

    vector_e = enrich_rows(vector, keywords)
    bm25_e = enrich_rows(bm25, keywords)
    rrf_e = enrich_rows(rrf, keywords)
    cross_e = enrich_rows(cross, keywords)
    final_e = cross_e[:TOP_K]

    case_dir = TRACE_OUTPUT_DIR / case_id / fmt
    write_csv(case_dir / "01_vector_search.csv", vector_e)
    write_csv(case_dir / "02_bm25.csv", bm25_e)
    write_csv(case_dir / "03_rrf_candidates.csv", rrf_e)
    write_csv(case_dir / "04_cross_encoder.csv", cross_e)
    write_csv(case_dir / "05_final_top5.csv", final_e)

    final_text = "\n\n".join(row["text"] for row in cross[:TOP_K])
    final_coverage = evidence_coverage(keywords, final_text)

    return {
        "case_id": case_id,
        "format": fmt,
        "document_id": document_id,
        "query": query,
        "evidence_keywords": ";".join(keywords),
        "vector_threshold_rank": first_threshold_rank(vector_e),
        "bm25_threshold_rank": first_threshold_rank(bm25_e),
        "rrf_threshold_rank": first_threshold_rank(rrf_e),
        "cross_threshold_rank": first_threshold_rank(cross_e),
        "final_top5_coverage": round(final_coverage, 6),
        "final_top5_hit": final_coverage >= EVIDENCE_HIT_THRESHOLD,
        "diagnosis": stage_diagnosis(vector_e, bm25_e, rrf_e, cross_e),
    }


def build_readme(summary_rows: list[dict]) -> str:
    lines = [
        "# Controlled Format Retrieval V2 — Focus Case Trace",
        "",
        "## Objetivo",
        "",
        "Trazar los casos foco del experimento controlado por formato a través de:",
        "",
        "```text",
        "Vector Search",
        "→ BM25",
        "→ RRF 50/50",
        "→ Cross-Encoder",
        "→ Top-5",
        "```",
        "",
        "La traza usa `palabras_clave_evidencia` porque los chunk IDs cambian",
        "al volver a extraer y chunkear cada formato.",
        "",
        "## Resumen",
        "",
        "| Caso | Formato | Vector rank | BM25 rank | RRF rank | Cross rank | Final coverage | Hit | Diagnóstico |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['case_id']} | {row['format'].upper()} | "
            f"{row['vector_threshold_rank'] or '-'} | "
            f"{row['bm25_threshold_rank'] or '-'} | "
            f"{row['rrf_threshold_rank'] or '-'} | "
            f"{row['cross_threshold_rank'] or '-'} | "
            f"{float(row['final_top5_coverage']):.2f} | "
            f"{row['final_top5_hit']} | `{row['diagnosis']}` |"
        )
    lines.extend([
        "",
        "## Archivos por caso/formato",
        "",
        "- `01_vector_search.csv`",
        "- `02_bm25.csv`",
        "- `03_rrf_candidates.csv`",
        "- `04_cross_encoder.csv`",
        "- `05_final_top5.csv`",
        "",
        "Cada archivo incluye evidencia encontrada por chunk, cobertura acumulada",
        "y el rank donde se alcanza por primera vez el threshold 0.50.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(MANIFEST_PATH)
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(GROUND_TRUTH_PATH)

    manifest = load_manifest()
    targets = load_targets()
    TRACE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== CONTROLLED FORMAT RETRIEVAL V2 TRACE ===")
    print("Casos:", ", ".join(TARGET_CASES))
    print("Formatos:", ", ".join(fmt.upper() for fmt in FORMATS))
    print("Top-K:", TOP_K)
    print("Candidate-K:", CANDIDATE_K)
    print("RRF k:", RRF_K)
    print()
    print("Cargando embeddings...")

    embedding_service = MultilingualEmbedding()
    summary_rows = []

    for fmt in FORMATS:
        print()
        print("=" * 72)
        print(f"ÍNDICE TRACE {fmt.upper()}")
        print("=" * 72)

        index_dir = INDEX_DIRS[fmt]
        remove_existing_index(index_dir)

        chunks = build_format_chunks(fmt, manifest)
        print("Chunks:", len(chunks))

        vector_store = VectorStore(
            path=str(index_dir),
            collection_name=COLLECTIONS[fmt],
            embedding_service=embedding_service,
        )
        vector_store.add_chunks(chunks)

        for case in targets:
            summary = trace_case(vector_store, fmt, case)
            summary_rows.append(summary)
            print(
                f"{summary['case_id']} [{fmt.upper()}] "
                f"vector={summary['vector_threshold_rank']} "
                f"bm25={summary['bm25_threshold_rank']} "
                f"rrf={summary['rrf_threshold_rank']} "
                f"cross={summary['cross_threshold_rank']} "
                f"final_cov={summary['final_top5_coverage']:.2f} "
                f"hit={summary['final_top5_hit']} "
                f"-> {summary['diagnosis']}"
            )

        del vector_store
        gc.collect()

    write_csv(TRACE_OUTPUT_DIR / "trace_summary.csv", summary_rows)
    (TRACE_OUTPUT_DIR / "README.md").write_text(
        build_readme(summary_rows),
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("RESUMEN FINAL")
    print("=" * 72)
    print(
        pd.DataFrame(summary_rows)[[
            "case_id",
            "format",
            "vector_threshold_rank",
            "bm25_threshold_rank",
            "rrf_threshold_rank",
            "cross_threshold_rank",
            "final_top5_coverage",
            "final_top5_hit",
            "diagnosis",
        ]].to_string(index=False)
    )
    print()
    print("Artefactos:")
    print(TRACE_OUTPUT_DIR)


if __name__ == "__main__":
    main()
