from __future__ import annotations

import csv
import gc
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"

CORPUS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.csv"

GT_PATH = DATA_IA_DIR / "data" / "evaluation" / "ground_truth_v2.csv"
CHUNKS_V1_PATH = DATA_IA_DIR / "data" / "evaluation" / "chunks_v1.csv"

RESULTS_DIR = CORPUS_DIR / "results"

FORMATS = ("md", "txt", "pdf")
TOP_K = 5
EVIDENCE_HIT_THRESHOLD = 0.50

INDEX_DIRS = {
    "md": ROOT / ".format_corpus_chroma_md",
    "txt": ROOT / ".format_corpus_chroma_txt",
    "pdf": ROOT / ".format_corpus_chroma_pdf",
}

COLLECTIONS = {
    "md": "format_corpus_md_v1",
    "txt": "format_corpus_txt_v1",
    "pdf": "format_corpus_pdf_v1",
}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentes.rag.extractor import extract_document  # noqa: E402
from agentes.rag.cleaner import clean_text  # noqa: E402
from agentes.rag.chunker import create_chunks  # noqa: E402
from agentes.rag.embeddings import MultilingualEmbedding  # noqa: E402
from agentes.rag.vector_store import VectorStore  # noqa: E402


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def token_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", normalize_text(text), flags=re.UNICODE))


def parse_relevant_ids(value: str) -> list[str]:
    return [
        item.strip()
        for item in (value or "").split(";")
        if item.strip()
    ]


def parse_keywords(value: str) -> list[str]:
    return [
        item.strip()
        for item in (value or "").split(";")
        if item.strip()
    ]


def evidence_coverage(keywords: list[str], retrieved_text: str) -> tuple[int, int, float]:
    if not keywords:
        return 0, 0, 0.0

    normalized_retrieved = normalize_text(retrieved_text)
    matched = 0

    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in normalized_retrieved:
            matched += 1

    return matched, len(keywords), matched / len(keywords)


def reference_token_recall(reference_text: str, retrieved_text: str) -> float:
    reference_tokens = token_set(reference_text)
    retrieved_tokens = token_set(retrieved_text)

    if not reference_tokens:
        return 0.0

    return len(reference_tokens & retrieved_tokens) / len(reference_tokens)


def load_reference_chunks() -> dict[str, str]:
    mapping: dict[str, str] = {}

    with CHUNKS_V1_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            mapping[row["chunk_id"]] = row["chunk_text"]

    return mapping


def load_ground_truth() -> list[dict]:
    with GT_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if len(rows) != 50:
        raise RuntimeError(
            f"Se esperaban 50 casos en Ground Truth v2 y se encontraron {len(rows)}."
        )

    return rows


def load_manifest() -> dict[str, dict]:
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    return {row["document_id"]: row for row in rows}


def remove_existing_index(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def build_format_chunks(fmt: str, manifest: dict[str, dict]):
    all_chunks = []

    for document_id, row in manifest.items():
        relative_path = row[f"{fmt}_file"]
        path = CORPUS_DIR / relative_path

        if not path.exists():
            raise FileNotFoundError(f"No existe {fmt} para {document_id}: {path}")

        documents = extract_document(str(path))

        for document in documents:
            document.text = clean_text(document.text)
            document.metadata["document_id"] = document_id
            document.metadata["category"] = row["category"]
            document.metadata["controlled_format"] = fmt

        chunks = create_chunks(documents)
        all_chunks.extend(chunks)

    return all_chunks


def save_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def evaluate_format(
    fmt: str,
    embedding_service,
    manifest: dict[str, dict],
    ground_truth: list[dict],
    reference_chunks: dict[str, str],
) -> list[dict]:
    index_dir = INDEX_DIRS[fmt]
    remove_existing_index(index_dir)

    print()
    print(f"=== CONSTRUYENDO ÍNDICE {fmt.upper()} ===")

    chunks = build_format_chunks(fmt, manifest)

    print(f"Chunks a indexar: {len(chunks)}")

    vector_store = VectorStore(
        path=str(index_dir),
        collection_name=COLLECTIONS[fmt],
        embedding_service=embedding_service,
    )

    vector_store.add_chunks(chunks)

    print(f"Índice {fmt.upper()} listo.")
    print(f"Ejecutando {len(ground_truth)} consultas...")

    rows = []

    for position, case in enumerate(ground_truth, start=1):
        case_id = case["case_id"]
        document_id = case["document_id"]
        query = case["pregunta"]

        results = vector_store.search(
            query=query,
            top_k=TOP_K,
            filters={"document_id": document_id},
        )

        combined_retrieved_text = "\n\n".join(result.text for result in results)

        keywords = parse_keywords(case["palabras_clave_evidencia"])
        matched_keywords, total_keywords, coverage = evidence_coverage(
            keywords,
            combined_retrieved_text,
        )

        relevant_ids = parse_relevant_ids(case["relevant_chunk_ids"])
        reference_text = "\n\n".join(
            reference_chunks[chunk_id]
            for chunk_id in relevant_ids
            if chunk_id in reference_chunks
        )

        token_recall = reference_token_recall(
            reference_text,
            combined_retrieved_text,
        )

        hit = coverage >= EVIDENCE_HIT_THRESHOLD

        rows.append(
            {
                "case_id": case_id,
                "document_id": document_id,
                "category": case["categoria"],
                "query": query,
                "format": fmt,
                "status": "success" if results else "no_results",
                "top_k_requested": TOP_K,
                "results_count": len(results),
                "evidence_keywords": ";".join(keywords),
                "matched_keywords": matched_keywords,
                "total_keywords": total_keywords,
                "evidence_coverage": round(coverage, 6),
                "evidence_hit_threshold": EVIDENCE_HIT_THRESHOLD,
                "evidence_hit": hit,
                "reference_chunk_ids": ";".join(relevant_ids),
                "reference_token_recall": round(token_recall, 6),
                "retrieved_chunk_ids": ";".join(
                    result.chunk_id for result in results
                ),
                "retrieved_scores": ";".join(
                    f"{result.score:.6f}" for result in results
                ),
                "retrieved_pages": ";".join(
                    str(result.metadata.get("page", ""))
                    for result in results
                ),
                "retrieved_text": " ||| ".join(
                    result.text.replace("\n", "\\n")
                    for result in results
                ),
            }
        )

        print(
            f"[{fmt.upper()} {position:02d}/50] {case_id}: "
            f"results={len(results)} "
            f"evidence={coverage:.2f} "
            f"hit={'YES' if hit else 'NO'}"
        )

    output_path = RESULTS_DIR / f"retrieval_{fmt}.csv"
    save_rows(output_path, rows)

    # Liberar el store antes de pasar al siguiente formato.
    del vector_store
    gc.collect()

    return rows


def build_comparison(all_results: dict[str, list[dict]]) -> list[dict]:
    by_case: dict[str, dict[str, dict]] = defaultdict(dict)

    for fmt, rows in all_results.items():
        for row in rows:
            by_case[row["case_id"]][fmt] = row

    comparison = []

    for case_id in sorted(by_case):
        case = by_case[case_id]

        md = case["md"]
        txt = case["txt"]
        pdf = case["pdf"]

        hit_values = {
            bool(md["evidence_hit"]),
            bool(txt["evidence_hit"]),
            bool(pdf["evidence_hit"]),
        }

        comparison.append(
            {
                "case_id": case_id,
                "document_id": md["document_id"],
                "category": md["category"],
                "query": md["query"],
                "md_evidence_coverage": md["evidence_coverage"],
                "txt_evidence_coverage": txt["evidence_coverage"],
                "pdf_evidence_coverage": pdf["evidence_coverage"],
                "md_evidence_hit": md["evidence_hit"],
                "txt_evidence_hit": txt["evidence_hit"],
                "pdf_evidence_hit": pdf["evidence_hit"],
                "md_reference_token_recall": md["reference_token_recall"],
                "txt_reference_token_recall": txt["reference_token_recall"],
                "pdf_reference_token_recall": pdf["reference_token_recall"],
                "format_disagreement": len(hit_values) > 1,
            }
        )

    return comparison


def build_summary(all_results: dict[str, list[dict]]) -> list[dict]:
    summary = []

    for fmt in FORMATS:
        rows = all_results[fmt]
        successful = sum(row["status"] == "success" for row in rows)
        hits = sum(bool(row["evidence_hit"]) for row in rows)

        mean_coverage = (
            sum(float(row["evidence_coverage"]) for row in rows) / len(rows)
        )
        mean_reference_recall = (
            sum(float(row["reference_token_recall"]) for row in rows) / len(rows)
        )

        summary.append(
            {
                "format": fmt,
                "cases": len(rows),
                "successful_queries": successful,
                "evidence_hits": hits,
                "evidence_hit_rate": round(hits / len(rows), 6),
                "mean_evidence_coverage": round(mean_coverage, 6),
                "mean_reference_token_recall": round(mean_reference_recall, 6),
                "top_k": TOP_K,
                "evidence_hit_threshold": EVIDENCE_HIT_THRESHOLD,
            }
        )

    return summary


def main() -> None:
    for required in (MANIFEST_PATH, GT_PATH, CHUNKS_V1_PATH):
        if not required.exists():
            raise FileNotFoundError(f"No existe archivo requerido: {required}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    ground_truth = load_ground_truth()
    reference_chunks = load_reference_chunks()

    print("=== RETRIEVAL CONTROLADO PDF / MD / TXT ===")
    print(f"Casos Ground Truth: {len(ground_truth)}")
    print(f"Documentos corpus: {len(manifest)}")
    print(f"Top-K: {TOP_K}")
    print(
        "Criterio primario de hit: "
        f"cobertura de evidencia >= {EVIDENCE_HIT_THRESHOLD:.0%}"
    )
    print()
    print("Cargando modelo de embeddings una sola vez...")

    embedding_service = MultilingualEmbedding()

    all_results: dict[str, list[dict]] = {}

    for fmt in FORMATS:
        all_results[fmt] = evaluate_format(
            fmt=fmt,
            embedding_service=embedding_service,
            manifest=manifest,
            ground_truth=ground_truth,
            reference_chunks=reference_chunks,
        )

    comparison = build_comparison(all_results)
    summary = build_summary(all_results)

    save_rows(
        RESULTS_DIR / "retrieval_format_comparison.csv",
        comparison,
    )
    save_rows(
        RESULTS_DIR / "retrieval_format_summary.csv",
        summary,
    )

    disagreements = [
        row for row in comparison if row["format_disagreement"]
    ]

    print()
    print("=== RESUMEN FINAL ===")

    for row in summary:
        print(
            f"{row['format'].upper()}: "
            f"{row['evidence_hits']}/{row['cases']} hits "
            f"({row['evidence_hit_rate']:.2%}) | "
            f"coverage={row['mean_evidence_coverage']:.4f} | "
            f"reference_recall={row['mean_reference_token_recall']:.4f}"
        )

    print()
    print(
        "Casos con desacuerdo entre formatos: "
        f"{len(disagreements)}/{len(comparison)}"
    )

    if disagreements:
        print("IDs con desacuerdo:")
        for row in disagreements:
            print(
                f"  {row['case_id']}: "
                f"MD={row['md_evidence_hit']} "
                f"TXT={row['txt_evidence_hit']} "
                f"PDF={row['pdf_evidence_hit']}"
            )

    print()
    print(f"Resultados: {RESULTS_DIR}")
    print("Archivos generados:")
    print("  retrieval_md.csv")
    print("  retrieval_txt.csv")
    print("  retrieval_pdf.csv")
    print("  retrieval_format_comparison.csv")
    print("  retrieval_format_summary.csv")


if __name__ == "__main__":
    main()
