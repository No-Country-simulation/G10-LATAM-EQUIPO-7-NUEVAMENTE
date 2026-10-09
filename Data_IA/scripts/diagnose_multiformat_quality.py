from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(DATA_IA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_IA_DIR))

from data_ai.evaluation.config import (
    RATIO_ALUCINACION_BUENO,
    RATIO_ALUCINACION_EXCELENTE,
    RATIO_ALUCINACION_RECHAZO,
    UMBRAL_RELEVANCIA_ALTA,
    UMBRAL_RELEVANCIA_MEDIA,
)
from data_ai.evaluation.quality_evaluator import _palabras_significativas

RESULTS_ROOT = (
    DATA_IA_DIR
    / "data"
    / "format_corpus_v1"
    / "results"
    / "multiformat_end_to_end"
)

OUTPUT_DIR = RESULTS_ROOT / "quality_diagnostics"

SOURCE_FORMATS = ("md", "txt", "pdf")
GENERATED_FORMATS = ("quiz", "flashcards", "tldr", "video_script")

FORMAT_LANGUAGE_TERMS = {
    "tldr": {
        "resumen", "conclusion", "conclusión", "clave", "punto", "puntos",
        "principal", "principales", "importante", "importantes", "sintesis", "síntesis",
    },
    "video_script": {
        "escena", "escenas", "visual", "visuales", "pantalla", "mostrar", "muestra",
        "aparece", "imagen", "imagenes", "imágenes", "animacion", "animación",
        "narracion", "narración", "voz", "transicion", "transición", "texto",
        "destacar", "ilustrar", "representacion", "representación",
    },
    "quiz": {
        "pregunta", "preguntas", "opcion", "opción", "opciones", "elige",
        "selecciona", "justificacion", "justificación", "explicacion", "explicación",
    },
    "flashcards": {
        "tarjeta", "tarjetas", "frente", "reverso", "concepto", "definicion", "definición",
    },
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_generated_text(generated_format: str, content: dict[str, Any]) -> str:
    if generated_format == "quiz":
        parts: list[str] = []
        for question in content.get("questions", []):
            parts.extend([
                str(question.get("question", "")),
                str(question.get("correct_answer", "")),
                str(question.get("explanation", "")),
            ])
        return " ".join(parts)

    if generated_format == "flashcards":
        parts: list[str] = []
        for card in content.get("cards", []):
            parts.extend([
                str(card.get("front", "")),
                str(card.get("back", "")),
            ])
        return " ".join(parts)

    if generated_format == "tldr":
        parts = [
            str(content.get("title", "")),
            str(content.get("summary", "")),
        ]
        parts.extend(str(x) for x in content.get("key_points", []))
        parts.append(str(content.get("conclusion", "")))
        return " ".join(parts)

    if generated_format == "video_script":
        parts = [str(content.get("title", ""))]
        for scene in content.get("scenes", []):
            parts.extend([
                str(scene.get("title", "")),
                str(scene.get("visual_description", "")),
                str(scene.get("narration", "")),
            ])
        return " ".join(parts)

    raise ValueError(f"Formato generado no soportado: {generated_format}")


def classify_generated_only_term(term: str, generated_format: str) -> str:
    if term in FORMAT_LANGUAGE_TERMS.get(generated_format, set()):
        return "format_or_presentation_language"
    return "content_or_paraphrase_candidate"


def expected_support_score(ratio: float) -> tuple[int, bool, str]:
    if ratio >= RATIO_ALUCINACION_RECHAZO:
        return 1, True, "reject_threshold"
    if ratio <= RATIO_ALUCINACION_EXCELENTE:
        return 5, False, "excellent"
    if ratio <= RATIO_ALUCINACION_BUENO:
        return 4, False, "good"
    return 3, False, "review_band"


def expected_relevance_score(ratio: float) -> int:
    if ratio >= UMBRAL_RELEVANCIA_ALTA:
        return 5
    if ratio >= UMBRAL_RELEVANCIA_MEDIA:
        return 4
    return 3


def diagnose_case(
    source_format: str,
    generated_format: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    case_dir = RESULTS_ROOT / source_format
    payload_path = case_dir / f"{generated_format}_evaluation_payload.json"
    response_path = case_dir / f"{generated_format}_evaluation_response.json"

    if not payload_path.exists():
        raise FileNotFoundError(payload_path)
    if not response_path.exists():
        raise FileNotFoundError(response_path)

    payload = read_json(payload_path)
    response = read_json(response_path)

    content = payload["generated_content"]
    chunks_used = payload["chunks_used"]
    generation_context = payload["generation_context"]

    generated_text = extract_generated_text(generated_format, content)
    source_text = " ".join(str(chunk.get("text", "")) for chunk in chunks_used)

    source_terms = set(_palabras_significativas(source_text))
    generated_terms = _palabras_significativas(generated_text)

    unsupported_occurrences = [
        term for term in generated_terms if term not in source_terms
    ]

    hallucination_ratio = (
        len(unsupported_occurrences) / len(generated_terms)
        if generated_terms else 0.0
    )

    expected_support, expected_flag, support_band = expected_support_score(
        hallucination_ratio
    )

    objective = str(
        generation_context.get("learning_objective", "") or ""
    ).strip()
    niche = str(generation_context.get("niche", "") or "").strip()
    context_text = f"{objective} {niche}".strip()

    context_terms = set(_palabras_significativas(context_text))
    generated_term_set = set(generated_terms)

    matching_context_terms = context_terms & generated_term_set
    missing_context_terms = context_terms - generated_term_set

    relevance_ratio = (
        len(matching_context_terms) / len(context_terms)
        if context_terms else 1.0
    )
    expected_relevance = expected_relevance_score(relevance_ratio)

    unsupported_counts = Counter(unsupported_occurrences)

    format_language_occurrences = sum(
        count
        for term, count in unsupported_counts.items()
        if classify_generated_only_term(term, generated_format)
        == "format_or_presentation_language"
    )

    unsupported_rows: list[dict[str, Any]] = []
    for term, count in unsupported_counts.most_common():
        unsupported_rows.append({
            "source_format": source_format,
            "generated_format": generated_format,
            "term": term,
            "occurrences": count,
            "classification": classify_generated_only_term(term, generated_format),
        })

    relevance_rows: list[dict[str, Any]] = []
    for term in sorted(context_terms):
        relevance_rows.append({
            "source_format": source_format,
            "generated_format": generated_format,
            "context_term": term,
            "present_in_generated": term in generated_term_set,
        })

    scores = response.get("scores") or {}

    summary = {
        "source_format": source_format,
        "generated_format": generated_format,
        "evaluation_status": response.get("status"),
        "reported_relevance": scores.get("relevancia"),
        "recomputed_relevance": expected_relevance,
        "relevance_ratio": round(relevance_ratio, 6),
        "context_terms": len(context_terms),
        "matching_context_terms": len(matching_context_terms),
        "missing_context_terms": ", ".join(sorted(missing_context_terms)),
        "reported_support": scores.get("informacion_respaldada"),
        "recomputed_support": expected_support,
        "reported_unsupported": response.get("informacion_no_respaldada"),
        "recomputed_unsupported": expected_flag,
        "support_band": support_band,
        "generated_term_occurrences": len(generated_terms),
        "source_unique_terms": len(source_terms),
        "unsupported_occurrences": len(unsupported_occurrences),
        "unsupported_unique_terms": len(unsupported_counts),
        "hallucination_ratio": round(hallucination_ratio, 6),
        "format_language_occurrences": format_language_occurrences,
        "format_language_share_of_unsupported": (
            round(format_language_occurrences / len(unsupported_occurrences), 6)
            if unsupported_occurrences else 0.0
        ),
        "top_unsupported_terms": ", ".join(
            f"{term}({count})"
            for term, count in unsupported_counts.most_common(15)
        ),
    }

    return summary, unsupported_rows, relevance_rows


def build_readme(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Diagnóstico de calidad multiformato",
        "",
        "Este diagnóstico reproduce la lógica léxica actual del evaluator",
        "sobre los artefactos E2E ya generados. No vuelve a llamar a Gemini.",
        "",
        "## Umbrales actuales",
        "",
        f"- Relevancia alta: `{UMBRAL_RELEVANCIA_ALTA}`",
        f"- Relevancia media: `{UMBRAL_RELEVANCIA_MEDIA}`",
        f"- Alucinación/rechazo: `{RATIO_ALUCINACION_RECHAZO}`",
        f"- Respaldo excelente: `{RATIO_ALUCINACION_EXCELENTE}`",
        f"- Respaldo bueno: `{RATIO_ALUCINACION_BUENO}`",
        "",
        "## Resumen",
        "",
        "| Fuente | Generado | Estado | Rel. reportada | Rel. recalculada | Ratio rel. | Respaldo reportado | Respaldo recalculado | Ratio no respaldado |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summaries:
        lines.append(
            f"| {row['source_format'].upper()} "
            f"| {row['generated_format']} "
            f"| {row['evaluation_status']} "
            f"| {row['reported_relevance']} "
            f"| {row['recomputed_relevance']} "
            f"| {row['relevance_ratio']:.3f} "
            f"| {row['reported_support']} "
            f"| {row['recomputed_support']} "
            f"| {row['hallucination_ratio']:.3f} |"
        )

    lines.extend([
        "",
        "## Cómo interpretar los archivos",
        "",
        "- `quality_case_summary.csv`: una fila por combinación fuente/formato.",
        "- `unsupported_terms.csv`: términos generados que no aparecen literalmente en los chunks recuperados.",
        "- `relevance_terms.csv`: términos del contexto de generación y si aparecen literalmente en la salida.",
        "",
        "Los términos `format_or_presentation_language` son vocabulario propio del formato.",
        "Los `content_or_paraphrase_candidate` requieren revisión humana: pueden ser",
        "paráfrasis válidas o información realmente no respaldada.",
        "",
        "Este diagnóstico no modifica los umbrales ni el evaluator.",
    ])

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostica relevancia y respaldo léxico "
            "de los resultados multiformato E2E."
        )
    )
    parser.add_argument(
        "--source-format",
        choices=["md", "txt", "pdf", "all"],
        default="all",
    )
    parser.add_argument(
        "--generated-format",
        choices=["quiz", "flashcards", "tldr", "video_script", "all"],
        default="all",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    source_formats = (
        SOURCE_FORMATS if args.source_format == "all" else (args.source_format,)
    )
    generated_formats = (
        GENERATED_FORMATS
        if args.generated_format == "all"
        else (args.generated_format,)
    )

    summaries: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []
    relevance_rows: list[dict[str, Any]] = []

    print("=== MULTIFORMAT QUALITY DIAGNOSTICS ===")

    for source_format in source_formats:
        for generated_format in generated_formats:
            try:
                summary, case_unsupported, case_relevance = diagnose_case(
                    source_format,
                    generated_format,
                )
            except FileNotFoundError as exc:
                print(
                    f"[SKIP] {source_format.upper()} "
                    f"→ {generated_format}: {exc}"
                )
                continue

            summaries.append(summary)
            unsupported_rows.extend(case_unsupported)
            relevance_rows.extend(case_relevance)

            print(
                f"{source_format.upper():3} "
                f"{generated_format:14} "
                f"status={summary['evaluation_status']:<18} "
                f"rel={summary['reported_relevance']}"
                f"/{summary['recomputed_relevance']} "
                f"support={summary['reported_support']}"
                f"/{summary['recomputed_support']} "
                f"unsupported_ratio={summary['hallucination_ratio']:.3f}"
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(OUTPUT_DIR / "quality_case_summary.csv", summaries)
    write_csv(OUTPUT_DIR / "unsupported_terms.csv", unsupported_rows)
    write_csv(OUTPUT_DIR / "relevance_terms.csv", relevance_rows)
    (OUTPUT_DIR / "README.md").write_text(
        build_readme(summaries),
        encoding="utf-8",
    )

    print()
    print("Artefactos:")
    print(OUTPUT_DIR)
    print()
    print(f"Casos diagnosticados: {len(summaries)}")

    if summaries:
        rejected = sum(
            1 for row in summaries if row["evaluation_status"] == "rechazado"
        )
        review = sum(
            1
            for row in summaries
            if row["evaluation_status"] == "requiere_revision"
        )
        approved = sum(
            1 for row in summaries if row["evaluation_status"] == "aprobado"
        )
        print(
            f"Aprobados={approved} | "
            f"Revisión={review} | "
            f"Rechazados={rejected}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
