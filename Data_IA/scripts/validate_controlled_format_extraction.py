from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"
CORPUS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.csv"
RESULTS_DIR = CORPUS_DIR / "validation"
RESULTS_PATH = RESULTS_DIR / "extraction_validation.csv"

# Permite importar el pipeline real de Agentes desde la raíz del repo.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentes.rag.extractor import extract_document  # noqa: E402


def normalize_for_comparison(text: str) -> str:
    """
    Normalización ligera para comparar contenido extraído entre formatos.

    No se usa para modificar los documentos ni para alimentar el pipeline.
    Solo sirve para métricas de equivalencia textual.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text(path: Path) -> tuple[str, int, set[str]]:
    documents = extract_document(str(path))
    text = "\n".join(doc.text for doc in documents)
    file_types = {doc.metadata.get("file_type", "") for doc in documents}
    return text, len(documents), file_types


def token_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower(), flags=re.UNICODE))


def jaccard(a: str, b: str) -> float:
    set_a = token_set(a)
    set_b = token_set(b)

    if not set_a and not set_b:
        return 1.0

    union = set_a | set_b
    if not union:
        return 0.0

    return len(set_a & set_b) / len(union)


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"No existe el manifest: {MANIFEST_PATH}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(MANIFEST_PATH.open("r", encoding="utf-8")))

    results = []

    for row in rows:
        document_id = row["document_id"]

        paths = {
            "md": CORPUS_DIR / row["md_file"],
            "txt": CORPUS_DIR / row["txt_file"],
            "pdf": CORPUS_DIR / row["pdf_file"],
        }

        extracted = {}

        for fmt, path in paths.items():
            if not path.exists():
                raise FileNotFoundError(f"Falta {fmt} para {document_id}: {path}")

            text, document_count, file_types = extract_text(path)

            extracted[fmt] = {
                "text": text,
                "normalized": normalize_for_comparison(text),
                "documents": document_count,
                "file_types": ",".join(sorted(file_types)),
            }

        txt_ref = extracted["txt"]["normalized"]

        result = {
            "document_id": document_id,
            "md_documents": extracted["md"]["documents"],
            "txt_documents": extracted["txt"]["documents"],
            "pdf_documents": extracted["pdf"]["documents"],
            "md_file_type": extracted["md"]["file_types"],
            "txt_file_type": extracted["txt"]["file_types"],
            "pdf_file_type": extracted["pdf"]["file_types"],
            "md_chars": len(extracted["md"]["normalized"]),
            "txt_chars": len(extracted["txt"]["normalized"]),
            "pdf_chars": len(extracted["pdf"]["normalized"]),
            "md_nonempty": bool(extracted["md"]["normalized"]),
            "txt_nonempty": bool(extracted["txt"]["normalized"]),
            "pdf_nonempty": bool(extracted["pdf"]["normalized"]),
            "md_vs_txt_jaccard": round(
                jaccard(extracted["md"]["normalized"], txt_ref), 6
            ),
            "pdf_vs_txt_jaccard": round(
                jaccard(extracted["pdf"]["normalized"], txt_ref), 6
            ),
        }

        results.append(result)

    fieldnames = list(results[0].keys())

    with RESULTS_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("=== VALIDACIÓN DE EXTRACCIÓN PDF / MD / TXT ===")
    print(f"Documentos evaluados: {len(results)}")
    print()

    for result in results:
        print(
            f"{result['document_id']}: "
            f"MD={result['md_documents']} doc(s), "
            f"TXT={result['txt_documents']} doc(s), "
            f"PDF={result['pdf_documents']} página(s), "
            f"Jaccard MD/TXT={result['md_vs_txt_jaccard']:.4f}, "
            f"PDF/TXT={result['pdf_vs_txt_jaccard']:.4f}"
        )

    print()
    print("No vacíos:")
    print(
        f"MD  {sum(r['md_nonempty'] for r in results)}/{len(results)} | "
        f"TXT {sum(r['txt_nonempty'] for r in results)}/{len(results)} | "
        f"PDF {sum(r['pdf_nonempty'] for r in results)}/{len(results)}"
    )

    print()
    print(f"Resultados guardados en: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
