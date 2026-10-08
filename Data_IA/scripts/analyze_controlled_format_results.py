from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"
RESULTS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1" / "results"

SUMMARY_PATH = RESULTS_DIR / "retrieval_format_summary.csv"
COMPARISON_PATH = RESULTS_DIR / "retrieval_format_comparison.csv"

FORMAT_FILES = {
    "md": RESULTS_DIR / "retrieval_md.csv",
    "txt": RESULTS_DIR / "retrieval_txt.csv",
    "pdf": RESULTS_DIR / "retrieval_pdf.csv",
}

CATEGORY_SUMMARY_PATH = RESULTS_DIR / "controlled_format_category_summary.csv"
CASE_ANALYSIS_PATH = RESULTS_DIR / "controlled_format_case_analysis.csv"
MANIFEST_PATH = RESULTS_DIR / "run_manifest.json"
README_PATH = RESULTS_DIR / "README.md"

EXPECTED_CASES = 50
EXPECTED_FORMATS = ("md", "txt", "pdf")


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


def as_float(value) -> float:
    return float(value)


def as_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs(summary: list[dict], comparison: list[dict]) -> None:
    if len(summary) != 3:
        raise RuntimeError(f"Se esperaban 3 formatos y se encontraron {len(summary)}.")

    formats = tuple(row["format"] for row in summary)
    if set(formats) != set(EXPECTED_FORMATS):
        raise RuntimeError(f"Formatos inesperados en summary: {formats}")

    if len(comparison) != EXPECTED_CASES:
        raise RuntimeError(
            f"Se esperaban {EXPECTED_CASES} casos y se encontraron {len(comparison)}."
        )

    for fmt, path in FORMAT_FILES.items():
        rows = read_csv(path)
        if len(rows) != EXPECTED_CASES:
            raise RuntimeError(
                f"{fmt}: se esperaban {EXPECTED_CASES} resultados y hay {len(rows)}."
            )


def build_category_summary(comparison: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in comparison:
        grouped[row["category"]].append(row)

    output = []

    for category in sorted(grouped):
        rows = grouped[category]
        result = {
            "category": category,
            "cases": len(rows),
        }

        for fmt in EXPECTED_FORMATS:
            coverages = [as_float(row[f"{fmt}_evidence_coverage"]) for row in rows]
            recalls = [as_float(row[f"{fmt}_reference_token_recall"]) for row in rows]
            hits = [as_bool(row[f"{fmt}_evidence_hit"]) for row in rows]

            result[f"{fmt}_evidence_hit_rate"] = round(sum(hits) / len(hits), 6)
            result[f"{fmt}_mean_evidence_coverage"] = round(
                sum(coverages) / len(coverages), 6
            )
            result[f"{fmt}_mean_reference_token_recall"] = round(
                sum(recalls) / len(recalls), 6
            )

        output.append(result)

    return output


def classify_case(row: dict) -> str | None:
    hits = [as_bool(row[f"{fmt}_evidence_hit"]) for fmt in EXPECTED_FORMATS]
    coverages = [as_float(row[f"{fmt}_evidence_coverage"]) for fmt in EXPECTED_FORMATS]

    if len(set(hits)) > 1:
        return "format_sensitive_hit_disagreement"

    if not any(hits):
        return "format_independent_failure"

    if len(set(coverages)) > 1:
        return "format_sensitive_coverage_only"

    return None


def build_case_analysis(comparison: list[dict]) -> list[dict]:
    output = []

    for row in comparison:
        classification = classify_case(row)
        if classification is None:
            continue

        output.append(
            {
                "case_id": row["case_id"],
                "document_id": row["document_id"],
                "category": row["category"],
                "query": row["query"],
                "classification": classification,
                "md_evidence_coverage": row["md_evidence_coverage"],
                "txt_evidence_coverage": row["txt_evidence_coverage"],
                "pdf_evidence_coverage": row["pdf_evidence_coverage"],
                "md_evidence_hit": row["md_evidence_hit"],
                "txt_evidence_hit": row["txt_evidence_hit"],
                "pdf_evidence_hit": row["pdf_evidence_hit"],
                "md_reference_token_recall": row["md_reference_token_recall"],
                "txt_reference_token_recall": row["txt_reference_token_recall"],
                "pdf_reference_token_recall": row["pdf_reference_token_recall"],
            }
        )

    return output


def summary_lookup(summary: list[dict]) -> dict[str, dict]:
    return {row["format"]: row for row in summary}


def build_manifest(
    summary: list[dict],
    comparison: list[dict],
    case_analysis: list[dict],
) -> dict:
    by_format = summary_lookup(summary)

    disagreements = [
        row for row in case_analysis
        if row["classification"] == "format_sensitive_hit_disagreement"
    ]
    coverage_only = [
        row for row in case_analysis
        if row["classification"] == "format_sensitive_coverage_only"
    ]
    common_failures = [
        row for row in case_analysis
        if row["classification"] == "format_independent_failure"
    ]

    files = [
        SUMMARY_PATH,
        COMPARISON_PATH,
        *FORMAT_FILES.values(),
    ]

    return {
        "experiment_name": "NuevaMente Controlled Format Retrieval Evaluation",
        "experiment_version": "v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "corpus": {
            "name": "format_corpus_v1",
            "formats": list(EXPECTED_FORMATS),
            "documents": 10,
            "semantic_content_controlled": True,
            "separate_vector_indexes": True,
        },
        "evaluation": {
            "ground_truth": "Data_IA/data/evaluation/ground_truth_v2.csv",
            "expected_cases": EXPECTED_CASES,
            "top_k": int(float(by_format["md"]["top_k"])),
            "evidence_hit_threshold": float(
                by_format["md"]["evidence_hit_threshold"]
            ),
            "primary_metric": "evidence_hit",
            "supporting_metrics": [
                "evidence_coverage",
                "reference_token_recall",
            ],
            "document_id_filter": True,
        },
        "results": {
            fmt: {
                "cases": int(by_format[fmt]["cases"]),
                "successful_queries": int(by_format[fmt]["successful_queries"]),
                "evidence_hits": int(by_format[fmt]["evidence_hits"]),
                "evidence_hit_rate": float(by_format[fmt]["evidence_hit_rate"]),
                "mean_evidence_coverage": float(
                    by_format[fmt]["mean_evidence_coverage"]
                ),
                "mean_reference_token_recall": float(
                    by_format[fmt]["mean_reference_token_recall"]
                ),
            }
            for fmt in EXPECTED_FORMATS
        },
        "case_findings": {
            "hit_disagreements": len(disagreements),
            "coverage_only_differences": len(coverage_only),
            "format_independent_failures": len(common_failures),
            "hit_disagreement_case_ids": [row["case_id"] for row in disagreements],
            "coverage_only_case_ids": [row["case_id"] for row in coverage_only],
            "format_independent_failure_case_ids": [
                row["case_id"] for row in common_failures
            ],
        },
        "input_hashes_sha256": {
            path.name: sha256(path)
            for path in files
        },
        "generated_artifacts": [
            CATEGORY_SUMMARY_PATH.name,
            CASE_ANALYSIS_PATH.name,
            MANIFEST_PATH.name,
            README_PATH.name,
        ],
        "interpretation_guardrails": [
            "No sobrescribir resultados históricos de Retrieval V1/V2.",
            "No interpretar relevant_chunk_ids como IDs directamente comparables entre formatos.",
            "No modificar chunking ni corpus antes de conservar esta corrida como baseline experimental.",
            "Un desacuerdo de hit aislado no demuestra que un formato sea globalmente inferior.",
        ],
    }


def build_readme(
    summary: list[dict],
    category_rows: list[dict],
    case_rows: list[dict],
) -> str:
    by_format = summary_lookup(summary)

    disagreements = [
        row for row in case_rows
        if row["classification"] == "format_sensitive_hit_disagreement"
    ]
    coverage_only = [
        row for row in case_rows
        if row["classification"] == "format_sensitive_coverage_only"
    ]
    common_failures = [
        row for row in case_rows
        if row["classification"] == "format_independent_failure"
    ]

    lines = [
        "# Controlled Format Retrieval Evaluation v1",
        "",
        "## Objetivo",
        "",
        "Evaluar si el formato de entrada modifica el comportamiento del retrieval",
        "cuando el contenido semántico se mantiene controlado entre Markdown, TXT y PDF.",
        "",
        "Cada formato se indexa en un índice vectorial separado.",
        "",
        "## Configuración",
        "",
        "- Corpus: `format_corpus_v1`",
        "- Documentos: 10",
        "- Queries: 50 (`ground_truth_v2.csv`)",
        "- Formatos: Markdown, TXT y PDF",
        "- Top-K: 5",
        "- Filtro: `document_id`",
        "- Criterio de hit: cobertura de evidencia >= 0.50",
        "- Métricas auxiliares: evidence coverage y reference token recall",
        "",
        "## Resultados globales",
        "",
        "| Formato | Hits | Hit rate | Mean evidence coverage | Mean reference token recall |",
        "|---|---:|---:|---:|---:|",
    ]

    for fmt in EXPECTED_FORMATS:
        row = by_format[fmt]
        lines.append(
            f"| {fmt.upper()} | "
            f"{row['evidence_hits']}/{row['cases']} | "
            f"{float(row['evidence_hit_rate']):.2%} | "
            f"{float(row['mean_evidence_coverage']):.4f} | "
            f"{float(row['mean_reference_token_recall']):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Hallazgos principales",
            "",
            f"- Casos con desacuerdo de hit entre formatos: **{len(disagreements)}**.",
            f"- Casos con diferencia de coverage sin cambiar el hit: **{len(coverage_only)}**.",
            f"- Fallos comunes a los tres formatos: **{len(common_failures)}**.",
            "",
        ]
    )

    for row in disagreements:
        lines.extend(
            [
                f"### {row['case_id']} — format-sensitive hit disagreement",
                "",
                f"- Documento: `{row['document_id']}`",
                f"- Categoría: {row['category']}",
                f"- Query: {row['query']}",
                f"- Coverage MD/TXT/PDF: "
                f"{float(row['md_evidence_coverage']):.4f} / "
                f"{float(row['txt_evidence_coverage']):.4f} / "
                f"{float(row['pdf_evidence_coverage']):.4f}",
                f"- Hit MD/TXT/PDF: "
                f"{row['md_evidence_hit']} / "
                f"{row['txt_evidence_hit']} / "
                f"{row['pdf_evidence_hit']}",
                "",
                "Interpretación: el caso es sensible al formato porque cambia el resultado",
                "binario de evidencia. Debe conservarse como caso de diagnóstico.",
                "",
            ]
        )

    for row in coverage_only:
        lines.extend(
            [
                f"### {row['case_id']} — format-sensitive coverage difference",
                "",
                f"- Documento: `{row['document_id']}`",
                f"- Query: {row['query']}",
                f"- Coverage MD/TXT/PDF: "
                f"{float(row['md_evidence_coverage']):.4f} / "
                f"{float(row['txt_evidence_coverage']):.4f} / "
                f"{float(row['pdf_evidence_coverage']):.4f}",
                "- El resultado sigue siendo hit en los tres formatos.",
                "",
            ]
        )

    for row in common_failures:
        lines.extend(
            [
                f"### {row['case_id']} — format-independent retrieval failure",
                "",
                f"- Documento: `{row['document_id']}`",
                f"- Query: {row['query']}",
                f"- Coverage MD/TXT/PDF: "
                f"{float(row['md_evidence_coverage']):.4f} / "
                f"{float(row['txt_evidence_coverage']):.4f} / "
                f"{float(row['pdf_evidence_coverage']):.4f}",
                "",
                "Interpretación: el fallo aparece en los tres formatos, por lo que no debe",
                "atribuirse al tipo de archivo. Requiere análisis separado de query, evidencia,",
                "chunking o retrieval.",
                "",
            ]
        )

    lines.extend(
        [
            "## Resumen por categoría",
            "",
            "| Categoría | MD coverage | TXT coverage | PDF coverage | "
            "MD token recall | TXT token recall | PDF token recall |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in category_rows:
        lines.append(
            f"| {row['category']} | "
            f"{float(row['md_mean_evidence_coverage']):.4f} | "
            f"{float(row['txt_mean_evidence_coverage']):.4f} | "
            f"{float(row['pdf_mean_evidence_coverage']):.4f} | "
            f"{float(row['md_mean_reference_token_recall']):.4f} | "
            f"{float(row['txt_mean_reference_token_recall']):.4f} | "
            f"{float(row['pdf_mean_reference_token_recall']):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Conclusión",
            "",
            "El retrieval es altamente robusto entre Markdown, TXT y PDF cuando el",
            "contenido semántico es equivalente. Markdown obtiene el mayor reference token",
            "recall global; PDF mantiene el mismo hit rate y evidence coverage que Markdown;",
            "TXT presenta una degradación pequeña y localizada.",
            "",
            "No se modifica el chunker ni el corpus en esta fase. Esta corrida se conserva",
            "como baseline experimental antes de cualquier optimización.",
            "",
            "## Archivos",
            "",
            "- `retrieval_md.csv`",
            "- `retrieval_txt.csv`",
            "- `retrieval_pdf.csv`",
            "- `retrieval_format_comparison.csv`",
            "- `retrieval_format_summary.csv`",
            "- `controlled_format_category_summary.csv`",
            "- `controlled_format_case_analysis.csv`",
            "- `run_manifest.json`",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    required = [SUMMARY_PATH, COMPARISON_PATH, *FORMAT_FILES.values()]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"No existe archivo requerido: {path}")

    summary = read_csv(SUMMARY_PATH)
    comparison = read_csv(COMPARISON_PATH)

    validate_inputs(summary, comparison)

    category_rows = build_category_summary(comparison)
    case_rows = build_case_analysis(comparison)

    write_csv(CATEGORY_SUMMARY_PATH, category_rows)
    write_csv(CASE_ANALYSIS_PATH, case_rows)

    manifest = build_manifest(summary, comparison, case_rows)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    README_PATH.write_text(
        build_readme(summary, category_rows, case_rows),
        encoding="utf-8",
    )

    print("=== CONTROLLED FORMAT ANALYSIS v1 ===")
    print(f"Category summary: {CATEGORY_SUMMARY_PATH}")
    print(f"Case analysis:    {CASE_ANALYSIS_PATH}")
    print(f"Run manifest:     {MANIFEST_PATH}")
    print(f"README:           {README_PATH}")
    print()
    print(
        "Casos especiales:",
        len(case_rows),
        "->",
        ", ".join(row["case_id"] for row in case_rows),
    )


if __name__ == "__main__":
    main()
