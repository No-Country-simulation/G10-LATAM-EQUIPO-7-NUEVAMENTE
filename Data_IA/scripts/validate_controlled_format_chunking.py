from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"
CORPUS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.csv"
RESULTS_DIR = CORPUS_DIR / "validation"
SUMMARY_PATH = RESULTS_DIR / "chunking_validation_summary.csv"
DETAIL_PATH = RESULTS_DIR / "chunking_validation_detail.csv"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentes.rag.extractor import extract_document  # noqa: E402
from agentes.rag.cleaner import clean_text  # noqa: E402
from agentes.rag.chunker import create_chunks  # noqa: E402
from agentes.rag.config import CONFIG  # noqa: E402


def build_chunks(path: Path, document_id: str):
    documents = extract_document(str(path))

    for document in documents:
        document.text = clean_text(document.text)
        document.metadata["document_id"] = document_id

    chunks = create_chunks(documents)
    return documents, chunks


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"No existe el manifest: {MANIFEST_PATH}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(MANIFEST_PATH.open("r", encoding="utf-8")))
    summary_rows = []
    detail_rows = []

    for row in rows:
        document_id = row["document_id"]

        paths = {
            "md": CORPUS_DIR / row["md_file"],
            "txt": CORPUS_DIR / row["txt_file"],
            "pdf": CORPUS_DIR / row["pdf_file"],
        }

        per_format_counts = {}

        for fmt, path in paths.items():
            documents, chunks = build_chunks(path, document_id)

            chunk_lengths = [len(chunk.text) for chunk in chunks]
            per_format_counts[fmt] = len(chunks)

            summary_rows.append(
                {
                    "document_id": document_id,
                    "format": fmt,
                    "source_units": len(documents),
                    "chunks": len(chunks),
                    "min_chunk_chars": min(chunk_lengths) if chunk_lengths else 0,
                    "max_chunk_chars": max(chunk_lengths) if chunk_lengths else 0,
                    "mean_chunk_chars": round(statistics.mean(chunk_lengths), 2)
                    if chunk_lengths
                    else 0,
                    "median_chunk_chars": round(statistics.median(chunk_lengths), 2)
                    if chunk_lengths
                    else 0,
                    "chunk_size_config": CONFIG.chunk_size,
                    "chunk_overlap_config": CONFIG.chunk_overlap,
                }
            )

            for index, chunk in enumerate(chunks):
                detail_rows.append(
                    {
                        "document_id": document_id,
                        "format": fmt,
                        "chunk_order": index,
                        "chunk_id": chunk.id,
                        "page": chunk.metadata.get("page"),
                        "file_type": chunk.metadata.get("file_type"),
                        "chunk_index": chunk.metadata.get("chunk_index"),
                        "chars": len(chunk.text),
                        "text": chunk.text,
                    }
                )

        md = per_format_counts["md"]
        txt = per_format_counts["txt"]
        pdf = per_format_counts["pdf"]

        print(
            f"{document_id}: "
            f"MD={md} chunks | TXT={txt} chunks | PDF={pdf} chunks"
        )

    with SUMMARY_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    with DETAIL_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)

    grouped: dict[str, dict[str, int]] = defaultdict(dict)

    for row in summary_rows:
        grouped[row["document_id"]][row["format"]] = int(row["chunks"])

    identical_counts = sum(
        1
        for values in grouped.values()
        if len({values["md"], values["txt"], values["pdf"]}) == 1
    )

    print()
    print("=== RESUMEN CHUNKING CONTROLADO ===")
    print(f"Documentos evaluados: {len(grouped)}")
    print(
        "Mismo número de chunks en MD/TXT/PDF: "
        f"{identical_counts}/{len(grouped)}"
    )
    print(
        f"Configuración: chunk_size={CONFIG.chunk_size}, "
        f"chunk_overlap={CONFIG.chunk_overlap}"
    )
    print(f"Resumen: {SUMMARY_PATH}")
    print(f"Detalle: {DETAIL_PATH}")


if __name__ == "__main__":
    main()
