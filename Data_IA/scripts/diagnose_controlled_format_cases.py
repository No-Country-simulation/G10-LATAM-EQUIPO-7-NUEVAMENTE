from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"

CORPUS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.csv"
GROUND_TRUTH_PATH = DATA_IA_DIR / "data" / "evaluation" / "ground_truth_v2.csv"

RESULTS_DIR = CORPUS_DIR / "results"
DIAGNOSTICS_DIR = RESULTS_DIR / "diagnostics"

RETRIEVAL_FILES = {
    "md": RESULTS_DIR / "retrieval_md.csv",
    "txt": RESULTS_DIR / "retrieval_txt.csv",
    "pdf": RESULTS_DIR / "retrieval_pdf.csv",
}

FORMATS = ("md", "txt", "pdf")

DEFAULT_CASE_IDS = (
    "FE-ES-001-Q01",
    "FE-ES-001-Q05",
    "CLD-ES-001-Q05",
)

DEFAULT_TOP_K = 5
DEFAULT_DIAGNOSTIC_TOP_K = 25
EVIDENCE_HIT_THRESHOLD = 0.50

# Índices diagnósticos separados de los índices del experimento principal.
# Se eliminan y reconstruyen en cada corrida para no depender del estado local previo.
DIAGNOSTIC_INDEX_DIRS = {
    "md": ROOT / ".format_diagnostic_chroma_md",
    "txt": ROOT / ".format_diagnostic_chroma_txt",
    "pdf": ROOT / ".format_diagnostic_chroma_pdf",
}

DIAGNOSTIC_COLLECTIONS = {
    "md": "format_diagnostic_md_v1",
    "txt": "format_diagnostic_txt_v1",
    "pdf": "format_diagnostic_pdf_v1",
}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentes.rag.extractor import extract_document  # noqa: E402
from agentes.rag.cleaner import clean_text  # noqa: E402
from agentes.rag.chunker import create_chunks  # noqa: E402
from agentes.rag.embeddings import MultilingualEmbedding  # noqa: E402
from agentes.rag.vector_store import VectorStore  # noqa: E402


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_semicolon_list(value: str) -> list[str]:
    return [
        item.strip()
        for item in (value or "").split(";")
        if item.strip()
    ]


def evidence_matches(
    keywords: list[str],
    text: str,
) -> tuple[list[str], float]:
    """
    Devuelve las keywords encontradas literalmente tras normalización ligera
    y la cobertura correspondiente.
    """
    normalized = normalize_text(text)

    matched = []
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in normalized:
            matched.append(keyword)

    coverage = len(matched) / len(keywords) if keywords else 0.0
    return matched, coverage


def token_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", normalize_text(text), flags=re.UNICODE))


def jaccard(a: str, b: str) -> float:
    set_a = token_set(a)
    set_b = token_set(b)

    if not set_a and not set_b:
        return 1.0

    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else 0.0


def reference_token_recall(reference_text: str, retrieved_text: str) -> float:
    reference_tokens = token_set(reference_text)
    retrieved_tokens = token_set(retrieved_text)

    if not reference_tokens:
        return 0.0

    return len(reference_tokens & retrieved_tokens) / len(reference_tokens)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def remove_existing_index(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def stringify_bool(value: bool) -> str:
    return "true" if value else "false"


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def load_manifest() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"No existe el manifest: {MANIFEST_PATH}")

    rows = read_csv(MANIFEST_PATH)
    return {row["document_id"]: row for row in rows}


def load_ground_truth() -> dict[str, dict]:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"No existe Ground Truth v2: {GROUND_TRUTH_PATH}"
        )

    rows = read_csv(GROUND_TRUTH_PATH)
    return {row["case_id"]: row for row in rows}


def load_original_retrieval_results() -> dict[str, dict[str, dict]]:
    """
    Devuelve:
        results[format][case_id] -> row
    """
    output: dict[str, dict[str, dict]] = {}

    for fmt, path in RETRIEVAL_FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el resultado de retrieval {fmt}: {path}"
            )

        rows = read_csv(path)
        output[fmt] = {row["case_id"]: row for row in rows}

    return output


# ---------------------------------------------------------------------------
# Reconstrucción controlada de chunks
# ---------------------------------------------------------------------------

def build_document_chunks(
    fmt: str,
    document_id: str,
    manifest_row: dict,
):
    relative_path = manifest_row[f"{fmt}_file"]
    path = CORPUS_DIR / relative_path

    if not path.exists():
        raise FileNotFoundError(
            f"No existe {fmt} para {document_id}: {path}"
        )

    documents = extract_document(str(path))

    for document in documents:
        document.text = clean_text(document.text)
        document.metadata["document_id"] = document_id
        document.metadata["category"] = manifest_row["category"]
        document.metadata["controlled_format"] = fmt

    chunks = create_chunks(documents)

    return path, documents, chunks


def chunk_rows_for_case(
    fmt: str,
    case: dict,
    chunks,
    keywords: list[str],
) -> list[dict]:
    rows = []

    for order, chunk in enumerate(chunks):
        matched, coverage = evidence_matches(keywords, chunk.text)

        rows.append(
            {
                "case_id": case["case_id"],
                "document_id": case["document_id"],
                "format": fmt,
                "chunk_order": order,
                "chunk_id": chunk.id,
                "page": chunk.metadata.get("page", ""),
                "chunk_index": chunk.metadata.get("chunk_index", ""),
                "chars": len(chunk.text),
                "matched_keywords": ";".join(matched),
                "matched_keywords_count": len(matched),
                "evidence_coverage_in_chunk": round(coverage, 6),
                "evidence_hit_in_chunk": stringify_bool(
                    coverage >= EVIDENCE_HIT_THRESHOLD
                ),
                "text": chunk.text.replace("\n", "\\n"),
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Índice diagnóstico y ranking completo
# ---------------------------------------------------------------------------

def build_diagnostic_store(
    fmt: str,
    embedding_service,
    chunks_by_document: dict[str, list],
):
    index_dir = DIAGNOSTIC_INDEX_DIRS[fmt]
    remove_existing_index(index_dir)

    all_chunks = []
    for chunks in chunks_by_document.values():
        all_chunks.extend(chunks)

    store = VectorStore(
        path=str(index_dir),
        collection_name=DIAGNOSTIC_COLLECTIONS[fmt],
        embedding_service=embedding_service,
    )
    store.add_chunks(all_chunks)

    return store


def run_full_ranking(
    store,
    case: dict,
    keywords: list[str],
    total_document_chunks: int,
    diagnostic_top_k: int,
) -> list[dict]:
    """
    Recupera suficientes resultados para conocer la posición real de los
    chunks que contienen la evidencia dentro del documento objetivo.
    """
    search_k = min(
        max(diagnostic_top_k, DEFAULT_TOP_K),
        total_document_chunks,
    )

    results = store.search(
        query=case["pregunta"],
        top_k=search_k,
        filters={"document_id": case["document_id"]},
    )

    rows = []

    for rank, result in enumerate(results, start=1):
        matched, coverage = evidence_matches(keywords, result.text)

        rows.append(
            {
                "rank": rank,
                "chunk_id": result.chunk_id,
                "score": round(float(result.score), 8),
                "page": result.metadata.get("page", ""),
                "matched_keywords": matched,
                "matched_keywords_count": len(matched),
                "evidence_coverage_in_chunk": coverage,
                "text": result.text,
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Diagnóstico causal
# ---------------------------------------------------------------------------

def aggregate_keyword_presence(
    keywords: list[str],
    chunks,
) -> dict[str, list[str]]:
    """
    keyword -> chunk_ids donde está presente.
    """
    presence: dict[str, list[str]] = {keyword: [] for keyword in keywords}

    for chunk in chunks:
        normalized_text = normalize_text(chunk.text)

        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)
            if normalized_keyword and normalized_keyword in normalized_text:
                presence[keyword].append(chunk.id)

    return presence


def first_rank_with_any_evidence(ranking_rows: list[dict]) -> int | None:
    for row in ranking_rows:
        if row["matched_keywords_count"] > 0:
            return row["rank"]
    return None


def first_rank_reaching_threshold(ranking_rows: list[dict]) -> int | None:
    """
    Primer rank acumulado cuyo texto combinado alcanza el threshold.
    Esto replica mejor la métrica original, que usa el texto combinado del Top-K.
    """
    combined = []

    if not ranking_rows:
        return None

    # Las keywords se reconstruyen desde matched keywords no alcanza para detectar
    # frases completas no presentes en un único chunk, por lo que la función
    # principal calcula esta parte de forma separada.
    return None


def cumulative_coverage_by_rank(
    keywords: list[str],
    ranking_rows: list[dict],
) -> list[tuple[int, float, list[str]]]:
    combined_texts: list[str] = []
    output = []

    for row in ranking_rows:
        combined_texts.append(row["text"])
        matched, coverage = evidence_matches(
            keywords,
            "\n\n".join(combined_texts),
        )
        output.append((row["rank"], coverage, matched))

    return output


def diagnose_format_case(
    fmt: str,
    case: dict,
    chunks,
    ranking_rows: list[dict],
    original_result: dict,
) -> dict:
    keywords = parse_semicolon_list(case["palabras_clave_evidencia"])

    full_document_text = "\n\n".join(chunk.text for chunk in chunks)
    document_matches, document_coverage = evidence_matches(
        keywords,
        full_document_text,
    )

    keyword_presence = aggregate_keyword_presence(keywords, chunks)

    cumulative = cumulative_coverage_by_rank(keywords, ranking_rows)

    first_threshold_rank = None
    for rank, coverage, _matched in cumulative:
        if coverage >= EVIDENCE_HIT_THRESHOLD:
            first_threshold_rank = rank
            break

    first_any_rank = first_rank_with_any_evidence(ranking_rows)

    top5_text = "\n\n".join(
        row["text"] for row in ranking_rows[:DEFAULT_TOP_K]
    )
    top5_matches, top5_coverage = evidence_matches(keywords, top5_text)

    original_coverage = float(original_result["evidence_coverage"])
    original_hit = str(original_result["evidence_hit"]).strip().lower() == "true"

    all_keywords_present = (
        document_coverage == 1.0 if keywords else False
    )

    evidence_present_somewhere = document_coverage > 0.0

    if not evidence_present_somewhere:
        diagnosis = "evidence_absent_after_extraction_cleaning_chunking"
    elif document_coverage < EVIDENCE_HIT_THRESHOLD:
        diagnosis = "insufficient_evidence_present_in_document_chunks"
    elif first_threshold_rank is None:
        diagnosis = "evidence_present_but_not_retrieved_within_diagnostic_top_k"
    elif first_threshold_rank > DEFAULT_TOP_K:
        diagnosis = "ranking_issue_evidence_below_top5"
    elif abs(top5_coverage - original_coverage) > 1e-9:
        diagnosis = "reproduction_mismatch_check_pipeline_state"
    elif original_hit:
        diagnosis = "top5_contains_sufficient_evidence"
    else:
        diagnosis = "top5_contains_partial_evidence_below_threshold"

    return {
        "case_id": case["case_id"],
        "document_id": case["document_id"],
        "category": case["categoria"],
        "query": case["pregunta"],
        "format": fmt,
        "keywords": ";".join(keywords),
        "document_keyword_matches": ";".join(document_matches),
        "document_evidence_coverage": round(document_coverage, 6),
        "all_keywords_present_in_chunks": all_keywords_present,
        "original_top5_evidence_coverage": round(original_coverage, 6),
        "reproduced_top5_evidence_coverage": round(top5_coverage, 6),
        "reproduced_top5_keyword_matches": ";".join(top5_matches),
        "original_top5_hit": original_hit,
        "first_rank_with_any_evidence": (
            first_any_rank if first_any_rank is not None else ""
        ),
        "first_rank_reaching_hit_threshold": (
            first_threshold_rank if first_threshold_rank is not None else ""
        ),
        "evidence_within_top5": (
            first_threshold_rank is not None
            and first_threshold_rank <= DEFAULT_TOP_K
        ),
        "total_document_chunks": len(chunks),
        "diagnostic_results_returned": len(ranking_rows),
        "diagnosis": diagnosis,
        "keyword_presence_json": json.dumps(
            keyword_presence,
            ensure_ascii=False,
            sort_keys=True,
        ),
    }


def compare_chunk_structure(
    case: dict,
    chunks_by_format: dict[str, list],
) -> list[dict]:
    """
    Comparación aproximada por posición de chunks entre formatos.
    No asume que IDs ni límites sean equivalentes.
    """
    max_chunks = max(len(chunks) for chunks in chunks_by_format.values())
    rows = []

    for order in range(max_chunks):
        texts = {}

        for fmt in FORMATS:
            chunks = chunks_by_format[fmt]
            texts[fmt] = chunks[order].text if order < len(chunks) else ""

        rows.append(
            {
                "case_id": case["case_id"],
                "document_id": case["document_id"],
                "chunk_order": order,
                "md_chunk_exists": bool(texts["md"]),
                "txt_chunk_exists": bool(texts["txt"]),
                "pdf_chunk_exists": bool(texts["pdf"]),
                "md_txt_jaccard": round(jaccard(texts["md"], texts["txt"]), 6)
                if texts["md"] and texts["txt"]
                else "",
                "md_pdf_jaccard": round(jaccard(texts["md"], texts["pdf"]), 6)
                if texts["md"] and texts["pdf"]
                else "",
                "txt_pdf_jaccard": round(jaccard(texts["txt"], texts["pdf"]), 6)
                if texts["txt"] and texts["pdf"]
                else "",
                "md_chars": len(texts["md"]),
                "txt_chars": len(texts["txt"]),
                "pdf_chars": len(texts["pdf"]),
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def build_markdown_report(
    cases: list[dict],
    diagnosis_rows: list[dict],
) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)

    for row in diagnosis_rows:
        grouped[row["case_id"]].append(row)

    lines = [
        "# Diagnóstico de casos sensibles al formato",
        "",
        "## Objetivo",
        "",
        "Determinar si los casos especiales de Controlled Format Retrieval v1",
        "se explican por pérdida de evidencia durante extracción/limpieza/chunking",
        "o por ranking del retrieval.",
        "",
        "El diagnóstico reconstruye los chunks por formato, crea índices diagnósticos",
        "separados y busca más allá del Top-5 para localizar la evidencia.",
        "",
        "## Casos analizados",
        "",
    ]

    for case in cases:
        lines.append(
            f"- `{case['case_id']}` — {case['pregunta']}"
        )

    lines.extend(
        [
            "",
            "## Resumen",
            "",
            "| Caso | Formato | Coverage documento | Coverage Top-5 | "
            "Primer rank con evidencia | Primer rank que alcanza hit | Diagnóstico |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )

    for case in cases:
        for row in sorted(
            grouped[case["case_id"]],
            key=lambda item: FORMATS.index(item["format"]),
        ):
            lines.append(
                f"| {row['case_id']} | {row['format'].upper()} | "
                f"{float(row['document_evidence_coverage']):.4f} | "
                f"{float(row['reproduced_top5_evidence_coverage']):.4f} | "
                f"{row['first_rank_with_any_evidence'] or '-'} | "
                f"{row['first_rank_reaching_hit_threshold'] or '-'} | "
                f"`{row['diagnosis']}` |"
            )

    lines.extend(
        [
            "",
            "## Interpretación de diagnósticos",
            "",
            "- `evidence_absent_after_extraction_cleaning_chunking`: la evidencia no está",
            "  presente en los chunks reconstruidos; revisar extracción/normalización.",
            "- `insufficient_evidence_present_in_document_chunks`: existe evidencia parcial,",
            "  pero ni todo el documento alcanza el umbral definido.",
            "- `ranking_issue_evidence_below_top5`: la evidencia existe y puede alcanzar el",
            "  umbral, pero aparece después del Top-5.",
            "- `evidence_present_but_not_retrieved_within_diagnostic_top_k`: la evidencia",
            "  existe en los chunks pero no apareció en la ventana diagnóstica solicitada.",
            "- `top5_contains_sufficient_evidence`: el Top-5 contiene evidencia suficiente.",
            "- `top5_contains_partial_evidence_below_threshold`: el Top-5 recupera evidencia",
            "  parcial, pero no alcanza el threshold.",
            "- `reproduction_mismatch_check_pipeline_state`: la reconstrucción actual no",
            "  reproduce exactamente la corrida guardada; revisar versiones/estado del pipeline.",
            "",
            "## Regla de decisión",
            "",
            "No se modifica el chunker ni el retrieval con este script. Su propósito es",
            "aislar la causa del fallo antes de abrir un experimento v2.",
        ]
    )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostica casos especiales de Controlled Format Retrieval v1 "
            "comparando extracción, chunking y ranking entre MD/TXT/PDF."
        )
    )

    parser.add_argument(
        "--cases",
        nargs="+",
        default=list(DEFAULT_CASE_IDS),
        help=(
            "case_id a diagnosticar. "
            f"Default: {' '.join(DEFAULT_CASE_IDS)}"
        ),
    )

    parser.add_argument(
        "--diagnostic-top-k",
        type=int,
        default=DEFAULT_DIAGNOSTIC_TOP_K,
        help=(
            "Cantidad máxima de resultados por documento para diagnóstico "
            f"(default: {DEFAULT_DIAGNOSTIC_TOP_K})."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.diagnostic_top_k < DEFAULT_TOP_K:
        raise ValueError(
            f"--diagnostic-top-k debe ser >= {DEFAULT_TOP_K}"
        )

    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    ground_truth = load_ground_truth()
    original_results = load_original_retrieval_results()

    missing_cases = [
        case_id for case_id in args.cases
        if case_id not in ground_truth
    ]
    if missing_cases:
        raise KeyError(
            f"case_id no encontrados en Ground Truth: {missing_cases}"
        )

    cases = [ground_truth[case_id] for case_id in args.cases]

    print("=== CONTROLLED FORMAT DIAGNOSTICS ===")
    print("Casos:", ", ".join(args.cases))
    print(f"Diagnostic Top-K: {args.diagnostic_top_k}")
    print()

    # Solo reconstruimos los documentos requeridos por los casos seleccionados.
    target_document_ids = sorted(
        {case["document_id"] for case in cases}
    )

    for document_id in target_document_ids:
        if document_id not in manifest:
            raise KeyError(
                f"{document_id} no existe en manifest.csv"
            )

    print("Documentos objetivo:", ", ".join(target_document_ids))
    print("Cargando embeddings...")
    embedding_service = MultilingualEmbedding()

    diagnosis_rows: list[dict] = []
    chunk_evidence_rows: list[dict] = []
    ranking_rows_output: list[dict] = []
    structure_rows: list[dict] = []

    # format -> document_id -> chunks
    all_chunks_by_format: dict[str, dict[str, list]] = {
        fmt: {} for fmt in FORMATS
    }

    # 1. Reconstruir chunks de documentos relevantes.
    for fmt in FORMATS:
        print()
        print(f"=== RECONSTRUYENDO {fmt.upper()} ===")

        for document_id in target_document_ids:
            path, documents, chunks = build_document_chunks(
                fmt,
                document_id,
                manifest[document_id],
            )

            all_chunks_by_format[fmt][document_id] = chunks

            print(
                f"{document_id}: "
                f"source_units={len(documents)} "
                f"chunks={len(chunks)} "
                f"path={path.name}"
            )

    # 2. Comparación estructural por documento/case.
    for case in cases:
        document_id = case["document_id"]

        chunks_by_format = {
            fmt: all_chunks_by_format[fmt][document_id]
            for fmt in FORMATS
        }

        structure_rows.extend(
            compare_chunk_structure(case, chunks_by_format)
        )

    # 3. Construir índices diagnósticos y ejecutar ranking extendido.
    stores = {}

    try:
        for fmt in FORMATS:
            print()
            print(f"=== ÍNDICE DIAGNÓSTICO {fmt.upper()} ===")

            stores[fmt] = build_diagnostic_store(
                fmt,
                embedding_service,
                all_chunks_by_format[fmt],
            )

            for case in cases:
                document_id = case["document_id"]
                keywords = parse_semicolon_list(
                    case["palabras_clave_evidencia"]
                )
                chunks = all_chunks_by_format[fmt][document_id]

                # Exportar presencia de evidencia chunk por chunk.
                chunk_evidence_rows.extend(
                    chunk_rows_for_case(
                        fmt=fmt,
                        case=case,
                        chunks=chunks,
                        keywords=keywords,
                    )
                )

                ranking_rows = run_full_ranking(
                    store=stores[fmt],
                    case=case,
                    keywords=keywords,
                    total_document_chunks=len(chunks),
                    diagnostic_top_k=args.diagnostic_top_k,
                )

                for row in ranking_rows:
                    ranking_rows_output.append(
                        {
                            "case_id": case["case_id"],
                            "document_id": document_id,
                            "format": fmt,
                            "rank": row["rank"],
                            "chunk_id": row["chunk_id"],
                            "score": row["score"],
                            "page": row["page"],
                            "matched_keywords": ";".join(
                                row["matched_keywords"]
                            ),
                            "matched_keywords_count": row[
                                "matched_keywords_count"
                            ],
                            "evidence_coverage_in_chunk": round(
                                row["evidence_coverage_in_chunk"], 6
                            ),
                            "text": row["text"].replace("\n", "\\n"),
                        }
                    )

                diagnosis = diagnose_format_case(
                    fmt=fmt,
                    case=case,
                    chunks=chunks,
                    ranking_rows=ranking_rows,
                    original_result=original_results[fmt][case["case_id"]],
                )
                diagnosis_rows.append(diagnosis)

                print(
                    f"{case['case_id']}: "
                    f"doc_cov={diagnosis['document_evidence_coverage']:.2f} "
                    f"top5={diagnosis['reproduced_top5_evidence_coverage']:.2f} "
                    f"first_hit_rank="
                    f"{diagnosis['first_rank_reaching_hit_threshold'] or '-'} "
                    f"-> {diagnosis['diagnosis']}"
                )

    finally:
        stores.clear()
        gc.collect()

    # 4. Guardar resultados.
    diagnosis_path = DIAGNOSTICS_DIR / "case_diagnosis_summary.csv"
    chunk_evidence_path = DIAGNOSTICS_DIR / "chunk_evidence_map.csv"
    ranking_path = DIAGNOSTICS_DIR / "extended_ranking.csv"
    structure_path = DIAGNOSTICS_DIR / "chunk_structure_comparison.csv"
    report_path = DIAGNOSTICS_DIR / "README.md"

    write_csv(diagnosis_path, diagnosis_rows)
    write_csv(chunk_evidence_path, chunk_evidence_rows)
    write_csv(ranking_path, ranking_rows_output)
    write_csv(structure_path, structure_rows)

    report_path.write_text(
        build_markdown_report(cases, diagnosis_rows),
        encoding="utf-8",
    )

    print()
    print("=== DIAGNÓSTICO COMPLETADO ===")
    print(f"Summary:   {diagnosis_path}")
    print(f"Evidence:  {chunk_evidence_path}")
    print(f"Ranking:   {ranking_path}")
    print(f"Structure: {structure_path}")
    print(f"README:    {report_path}")
    print()
    print("No se modificó el corpus ni el benchmark original.")


if __name__ == "__main__":
    main()
