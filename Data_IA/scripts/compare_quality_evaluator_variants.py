from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(DATA_IA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_IA_DIR))

try:
    from data_ai.evaluation.config import (
        RATIO_ALUCINACION_BUENO,
        RATIO_ALUCINACION_EXCELENTE,
        RATIO_ALUCINACION_RECHAZO,
        UMBRAL_RELEVANCIA_ALTA,
        UMBRAL_RELEVANCIA_MEDIA,
    )
except Exception:
    # Fallback exacto a los valores actuales de QA, solo para --self-test.
    UMBRAL_RELEVANCIA_ALTA = 0.50
    UMBRAL_RELEVANCIA_MEDIA = 0.25
    RATIO_ALUCINACION_RECHAZO = 0.40
    RATIO_ALUCINACION_EXCELENTE = 0.15
    RATIO_ALUCINACION_BUENO = 0.30


RESULTS_ROOT = (
    DATA_IA_DIR
    / "data"
    / "format_corpus_v1"
    / "results"
    / "multiformat_end_to_end"
)
OUTPUT_DIR = RESULTS_ROOT / "quality_comparison"

SOURCE_FORMATS = ("md", "txt", "pdf")
GENERATED_FORMATS = ("quiz", "flashcards", "tldr", "video_script")

STOPWORDS = {
    "para", "desde", "sobre", "entre", "como", "esta", "este", "estos", "estas",
    "crear", "utiliza", "utilizado", "selecciona", "respuesta", "correcta",
    "intenta", "responder", "antes", "revisar", "conceptos", "basicos",
    "básicos", "comprender",
}

PRESENTATION_TERMS = {
    "quiz": {
        "pregunta", "preguntas", "opcion", "opción", "opciones",
        "explicacion", "explicación", "justificacion", "justificación",
        "elige", "selecciona",
    },
    "flashcards": {
        "tarjeta", "tarjetas", "frente", "reverso",
        "concepto", "definicion", "definición",
    },
    "tldr": {
        "resumen", "conclusion", "conclusión", "clave", "claves",
        "punto", "puntos", "sintesis", "síntesis",
        "principal", "principales",
    },
    "video_script": {
        "escena", "escenas", "visual", "visuales", "pantalla",
        "mostrar", "muestra", "mostrando", "aparece", "imagen", "imagenes",
        "imágenes", "animacion", "animación", "narracion", "narración",
        "voz", "transicion", "transición", "texto", "destacar",
        "ilustrar", "representacion", "representación",
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


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )


def normalize_token(token: str) -> str:
    token = strip_accents(token.lower().strip())
    token = re.sub(r"[^a-z0-9_áéíóúñü]+", "", token)

    # Normalización morfológica muy conservadora:
    # páginas -> pagina, comentarios -> comentario, fundamentos -> fundamento.
    if len(token) > 5 and token.endswith("es"):
        singular = token[:-2]
        if len(singular) >= 4:
            return singular
    if len(token) > 4 and token.endswith("s"):
        singular = token[:-1]
        if len(singular) >= 4:
            return singular

    return token


def significant_terms(text: str) -> list[str]:
    tokens = re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)
    normalized_stopwords = {normalize_token(x) for x in STOPWORDS}
    output = []
    for token in tokens:
        norm = normalize_token(token)
        if len(norm) > 3 and norm not in normalized_stopwords:
            output.append(norm)
    return output


def baseline_significant_terms(text: str) -> list[str]:
    # Reproduce la heurística V1 actual: minúsculas, >3 caracteres, stopwords,
    # sin quitar acentos ni normalizar singular/plural.
    tokens = re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)
    return [
        token
        for token in tokens
        if len(token) > 3 and token not in STOPWORDS
    ]


def baseline_generated_text(
    generated_format: str,
    content: dict[str, Any],
) -> str:
    if generated_format == "quiz":
        parts = []
        for q in content.get("questions", []):
            parts.extend([
                str(q.get("question", "")),
                str(q.get("correct_answer", "")),
                str(q.get("explanation", "")),
            ])
        return " ".join(parts)

    if generated_format == "flashcards":
        parts = []
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

    raise ValueError(generated_format)


def improved_generated_text(
    generated_format: str,
    content: dict[str, Any],
) -> str:
    # Se evalúa solo conocimiento factual, no instrucciones de presentación.
    if generated_format == "quiz":
        return baseline_generated_text(generated_format, content)

    if generated_format == "flashcards":
        return baseline_generated_text(generated_format, content)

    if generated_format == "tldr":
        # Excluir el título: puede introducir framing sin ser una afirmación factual.
        parts = [str(content.get("summary", ""))]
        parts.extend(str(x) for x in content.get("key_points", []))
        parts.append(str(content.get("conclusion", "")))
        return " ".join(parts)

    if generated_format == "video_script":
        # Solo narración. Los títulos de escena y visual_description son
        # instrucciones audiovisuales, no conocimiento factual.
        parts = []
        for scene in content.get("scenes", []):
            parts.append(str(scene.get("narration", "")))
        return " ".join(parts)

    raise ValueError(generated_format)


def decision_from_scores(
    relevance: int,
    support: int,
    unsupported: bool,
) -> str:
    # Coherencia y adaptación ya fueron 5/5 en los artefactos observados,
    # así que para este comparador solo cambian relevancia y respaldo.
    if unsupported:
        return "rechazado"
    if relevance <= 2 or support <= 2:
        return "rechazado"
    if relevance == 3 or support == 3:
        return "requiere_revision"
    return "aprobado"


def support_score(ratio: float) -> tuple[int, bool]:
    if ratio >= RATIO_ALUCINACION_RECHAZO:
        return 1, True
    if ratio <= RATIO_ALUCINACION_EXCELENTE:
        return 5, False
    if ratio <= RATIO_ALUCINACION_BUENO:
        return 4, False
    return 3, False


def relevance_score(ratio: float) -> int:
    if ratio >= UMBRAL_RELEVANCIA_ALTA:
        return 5
    if ratio >= UMBRAL_RELEVANCIA_MEDIA:
        return 4
    return 3


def compute_baseline(
    generated_format: str,
    content: dict[str, Any],
    source_text: str,
    generation_context: dict[str, Any],
) -> dict[str, Any]:
    generated_text = baseline_generated_text(generated_format, content)
    source_terms = set(baseline_significant_terms(source_text))
    generated_terms = baseline_significant_terms(generated_text)

    unsupported = [
        t for t in generated_terms
        if t not in source_terms
    ]
    ratio = (
        len(unsupported) / len(generated_terms)
        if generated_terms else 0.0
    )
    support, unsupported_flag = support_score(ratio)

    context = (
        f"{generation_context.get('learning_objective') or ''} "
        f"{generation_context.get('niche') or ''}"
    ).strip()
    context_terms = set(baseline_significant_terms(context))
    generated_set = set(generated_terms)
    rel_ratio = (
        len(context_terms & generated_set) / len(context_terms)
        if context_terms else 1.0
    )
    relevance = relevance_score(rel_ratio)

    return {
        "generated_terms": generated_terms,
        "unsupported_terms": unsupported,
        "unsupported_ratio": ratio,
        "support_score": support,
        "unsupported_flag": unsupported_flag,
        "relevance_ratio": rel_ratio,
        "relevance_score": relevance,
        "status": decision_from_scores(
            relevance,
            support,
            unsupported_flag,
        ),
    }


def compute_improved(
    generated_format: str,
    content: dict[str, Any],
    source_text: str,
    generation_context: dict[str, Any],
) -> dict[str, Any]:
    generated_text = improved_generated_text(generated_format, content)

    source_terms = set(significant_terms(source_text))
    generated_terms = significant_terms(generated_text)

    context = (
        f"{generation_context.get('learning_objective') or ''} "
        f"{generation_context.get('niche') or ''}"
    ).strip()
    context_terms = set(significant_terms(context))

    presentation_terms = {
        normalize_token(term)
        for term in PRESENTATION_TERMS.get(generated_format, set())
    }

    allowed_terms = source_terms | context_terms | presentation_terms

    unsupported = []
    removed = []
    baseline_like_source = set(baseline_significant_terms(source_text))

    for term in generated_terms:
        if term in allowed_terms:
            reason = None

            if term in context_terms and term not in source_terms:
                reason = "generation_context_term"
            elif term in presentation_terms and term not in source_terms:
                reason = "format_presentation_term"

            if reason:
                removed.append((term, reason))
            continue

        # Diagnóstico de términos que dejan de penalizarse solo por normalización.
        raw_candidates = [
            raw for raw in baseline_like_source
            if normalize_token(raw) == term
        ]
        if raw_candidates:
            removed.append((term, "accent_or_morphology_normalization"))
            continue

        unsupported.append(term)

    ratio = (
        len(unsupported) / len(generated_terms)
        if generated_terms else 0.0
    )
    support, unsupported_flag = support_score(ratio)

    generated_set = set(generated_terms)
    rel_ratio = (
        len(context_terms & generated_set) / len(context_terms)
        if context_terms else 1.0
    )
    relevance = relevance_score(rel_ratio)

    return {
        "generated_terms": generated_terms,
        "unsupported_terms": unsupported,
        "removed_terms": removed,
        "unsupported_ratio": ratio,
        "support_score": support,
        "unsupported_flag": unsupported_flag,
        "relevance_ratio": rel_ratio,
        "relevance_score": relevance,
        "status": decision_from_scores(
            relevance,
            support,
            unsupported_flag,
        ),
    }


def diagnose_case(
    source_format: str,
    generated_format: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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
    chunks = payload["chunks_used"]
    context = payload["generation_context"]
    source_text = " ".join(str(x.get("text", "")) for x in chunks)

    baseline = compute_baseline(
        generated_format,
        content,
        source_text,
        context,
    )
    improved = compute_improved(
        generated_format,
        content,
        source_text,
        context,
    )

    scores = response.get("scores") or {}

    summary = {
        "source_format": source_format,
        "generated_format": generated_format,
        "reported_status": response.get("status"),
        "baseline_status": baseline["status"],
        "improved_status": improved["status"],
        "reported_relevance": scores.get("relevancia"),
        "baseline_relevance": baseline["relevance_score"],
        "improved_relevance": improved["relevance_score"],
        "baseline_relevance_ratio": round(
            baseline["relevance_ratio"], 6
        ),
        "improved_relevance_ratio": round(
            improved["relevance_ratio"], 6
        ),
        "reported_support": scores.get("informacion_respaldada"),
        "baseline_support": baseline["support_score"],
        "improved_support": improved["support_score"],
        "baseline_unsupported_ratio": round(
            baseline["unsupported_ratio"], 6
        ),
        "improved_unsupported_ratio": round(
            improved["unsupported_ratio"], 6
        ),
        "baseline_unsupported_flag": baseline["unsupported_flag"],
        "improved_unsupported_flag": improved["unsupported_flag"],
        "baseline_unsupported_occurrences": len(
            baseline["unsupported_terms"]
        ),
        "improved_unsupported_occurrences": len(
            improved["unsupported_terms"]
        ),
        "removed_occurrences": len(improved["removed_terms"]),
        "delta_unsupported_ratio": round(
            improved["unsupported_ratio"]
            - baseline["unsupported_ratio"],
            6,
        ),
    }

    removed_rows = []
    counts = Counter(improved["removed_terms"])
    for (term, reason), occurrences in counts.most_common():
        removed_rows.append({
            "source_format": source_format,
            "generated_format": generated_format,
            "term": term,
            "reason": reason,
            "occurrences": occurrences,
        })

    return summary, removed_rows


def build_readme(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Comparación experimental del evaluator de calidad",
        "",
        "Compara la heurística léxica actual contra una variante experimental.",
        "No modifica el evaluator de producción y no llama a Gemini.",
        "",
        "## Variante experimental",
        "",
        "- normaliza acentos;",
        "- aplica singularización básica conservadora;",
        "- acepta términos procedentes de `generation_context`;",
        "- excluye vocabulario estructural/presentacional;",
        "- para `video_script`, evalúa respaldo factual sobre `narration`;",
        "- para `tldr`, excluye el título del chequeo factual.",
        "",
        "## Resultados",
        "",
        "| Fuente | Formato | Reportado | Baseline | Mejorado | Ratio base | Ratio mejorado | Support base | Support mejorado |",
        "|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['source_format'].upper()} "
            f"| {row['generated_format']} "
            f"| {row['reported_status']} "
            f"| {row['baseline_status']} "
            f"| {row['improved_status']} "
            f"| {row['baseline_unsupported_ratio']:.3f} "
            f"| {row['improved_unsupported_ratio']:.3f} "
            f"| {row['baseline_support']} "
            f"| {row['improved_support']} |"
        )

    lines.extend([
        "",
        "## Interpretación",
        "",
        "El baseline debe coincidir con el evaluator actual. Si no coincide,",
        "la comparación no debe usarse para proponer cambios.",
        "",
        "Una mejora es prometedora si reduce falsos positivos sin convertir",
        "automáticamente todos los casos en aprobados.",
    ])
    return "\n".join(lines) + "\n"


def run_self_test() -> int:
    source = "HTML define la estructura de una página. CSS da estilo a la página."
    content = {
        "title": "Resumen de frontend",
        "summary": "HTML estructura páginas y CSS controla la apariencia visual.",
        "key_points": ["HTML estructura páginas", "CSS controla estilos"],
        "conclusion": "Son fundamentos de frontend.",
    }
    context = {
        "learning_objective": "Comprender los fundamentos del documento",
        "niche": "frontend",
    }

    base = compute_baseline("tldr", content, source, context)
    improved = compute_improved("tldr", content, source, context)

    print("SELF-TEST")
    print("baseline_ratio =", round(base["unsupported_ratio"], 3))
    print("improved_ratio =", round(improved["unsupported_ratio"], 3))
    print("baseline_status =", base["status"])
    print("improved_status =", improved["status"])

    assert improved["unsupported_ratio"] <= base["unsupported_ratio"]
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compara evaluator léxico actual vs variante experimental "
            "sobre artefactos multiformato ya generados."
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
    parser.add_argument(
        "--self-test",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.self_test:
        return run_self_test()

    source_formats = (
        SOURCE_FORMATS
        if args.source_format == "all"
        else (args.source_format,)
    )
    generated_formats = (
        GENERATED_FORMATS
        if args.generated_format == "all"
        else (args.generated_format,)
    )

    rows = []
    removed_rows = []

    print("=== QUALITY EVALUATOR VARIANT COMPARISON ===")

    for source_format in source_formats:
        for generated_format in generated_formats:
            try:
                summary, removed = diagnose_case(
                    source_format,
                    generated_format,
                )
            except FileNotFoundError as exc:
                print(
                    f"[SKIP] {source_format.upper()} "
                    f"→ {generated_format}: {exc}"
                )
                continue

            rows.append(summary)
            removed_rows.extend(removed)

            print(
                f"{source_format.upper():3} "
                f"{generated_format:14} "
                f"status={summary['reported_status']} "
                f"→ {summary['improved_status']} | "
                f"unsupported="
                f"{summary['baseline_unsupported_ratio']:.3f}"
                f"→{summary['improved_unsupported_ratio']:.3f} | "
                f"support="
                f"{summary['baseline_support']}"
                f"→{summary['improved_support']}"
            )

    if not rows:
        print("No se encontraron artefactos E2E.")
        return 1

    # Guardrail: el baseline experimental debe reproducir el evaluator actual.
    mismatches = [
        row for row in rows
        if row["reported_status"] != row["baseline_status"]
        or row["reported_relevance"] != row["baseline_relevance"]
        or row["reported_support"] != row["baseline_support"]
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "quality_evaluator_comparison.csv", rows)
    write_csv(OUTPUT_DIR / "removed_terms_by_reason.csv", removed_rows)
    (OUTPUT_DIR / "README.md").write_text(
        build_readme(rows),
        encoding="utf-8",
    )

    print()
    print("Casos:", len(rows))
    print("Baseline mismatches:", len(mismatches))
    print("Artefactos:", OUTPUT_DIR)

    if mismatches:
        print(
            "ADVERTENCIA: el baseline no reproduce exactamente "
            "el evaluator actual; no interpretar la variante mejorada todavía."
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
