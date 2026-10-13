from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "data" / "format_corpus_v1"

MD_DIR = OUTPUT_DIR / "md"
TXT_DIR = OUTPUT_DIR / "txt"
PDF_DIR = OUTPUT_DIR / "pdf"

MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"
README_PATH = OUTPUT_DIR / "README.md"

EXPECTED_DOCUMENT_IDS = [
    "AI-ES-001",
    "AI-ES-002",
    "BE-ES-001",
    "BE-ES-002",
    "CLD-ES-001",
    "CLD-ES-002",
    "DS-ES-001",
    "DS-ES-002",
    "FE-ES-001",
    "FE-ES-002",
]

CATEGORY_MAP = {
    "AI": "IA",
    "BE": "Backend",
    "CLD": "Cloud / DevOps",
    "DS": "Data Science",
    "FE": "Frontend",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def markdown_to_plain_text(markdown: str) -> str:
    """
    Convierte Markdown a texto plano intentando conservar el contenido
    semántico y el orden original.

    No resume, reescribe ni modifica el significado.
    """
    text = normalize_newlines(markdown)

    # Fenced code blocks: elimina marcas ``` pero conserva el código.
    text = re.sub(r"```[a-zA-Z0-9_+-]*\n", "", text)
    text = text.replace("```", "")

    # Imágenes Markdown: ![alt](url) -> alt
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

    # Links: [texto](url) -> texto
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Encabezados Markdown.
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", text)

    # Blockquotes.
    text = re.sub(r"(?m)^\s*>\s?", "", text)

    # Listas.
    text = re.sub(r"(?m)^\s*[-*+]\s+", "- ", text)
    text = re.sub(r"(?m)^\s*(\d+)\.\s+", r"\1. ", text)

    # Énfasis inline.
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!_)(.*?)_(?!_)", r"\1", text)

    # Código inline.
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Reglas horizontales.
    text = re.sub(r"(?m)^\s*([-*_])(?:\s*\1){2,}\s*$", "", text)

    # Evita exceso de líneas en blanco.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip() + "\n"


def build_pdf(text: str, output_path: Path, document_id: str) -> None:
    """
    Genera un PDF simple a partir del mismo Markdown fuente.
    """
    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    body_style = styles["BodyText"]
    heading_style = styles["Heading2"]
    code_style = styles["Code"]

    body_style.fontName = "Helvetica"
    body_style.fontSize = 9.5
    body_style.leading = 13

    heading_style.fontName = "Helvetica-Bold"
    heading_style.fontSize = 12
    heading_style.leading = 15

    code_style.fontName = "Courier"
    code_style.fontSize = 8
    code_style.leading = 10

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=document_id,
        author="NuevaMente - Data/IA",
    )

    story = []

    lines = normalize_newlines(text).splitlines()
    in_code_block = False
    code_buffer: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                if code_buffer:
                    story.append(
                        Preformatted(
                            "\n".join(code_buffer),
                            code_style,
                        )
                    )
                    story.append(Spacer(1, 6))
                    code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        if not stripped:
            story.append(Spacer(1, 5))
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)

        if heading_match:
            heading_text = escape(heading_match.group(2))
            story.append(Paragraph(heading_text, heading_style))
            story.append(Spacer(1, 4))
            continue

        safe_line = escape(line)

        # Conserva formato inline básico.
        safe_line = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            safe_line,
        )

        safe_line = re.sub(
            r"`([^`]+)`",
            r"<font name='Courier'>\1</font>",
            safe_line,
        )

        story.append(Paragraph(safe_line, body_style))

    if code_buffer:
        story.append(
            Preformatted(
                "\n".join(code_buffer),
                code_style,
            )
        )

    doc.build(story)


def build_readme() -> None:
    content = """# Controlled Format Corpus v1

## Objetivo

Este corpus se creó para evaluar el comportamiento del pipeline de NuevaMente
frente a distintos formatos de entrada:

- Markdown (`.md`)
- Texto plano (`.txt`)
- PDF (`.pdf`)

Cada documento parte de la misma fuente ubicada en:

`Data_IA/data/processed/`

El contenido del benchmark original ubicado en:

`Data_IA/data/evaluation/`

no se modifica.

## Principio experimental

La variable controlada es el formato del archivo.

Cada `document_id` tiene tres representaciones equivalentes:

- `md/<document_id>.md`
- `txt/<document_id>.txt`
- `pdf/<document_id>.pdf`

Esto permite comparar extracción, chunking, retrieval y generación
manteniendo constante el contenido semántico.

## Documentos

El corpus contiene 10 documentos y 30 archivos en total:

- 10 Markdown
- 10 TXT
- 10 PDF

## Reproducibilidad

`manifest.csv` registra:

- `document_id`
- categoría
- archivo fuente
- archivos generados
- hashes SHA-256
- versión del corpus

El corpus puede regenerarse ejecutando:

```bash
python Data_IA/scripts/build_controlled_format_corpus.py
```

## Importante

Este corpus es independiente del benchmark congelado.

No deben modificarse como parte de estas pruebas:

- `ground_truth_v2.csv`
- `chunks_v1.csv`
- manifests históricos del benchmark
- resultados oficiales de Retrieval V1/V2
"""
    README_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    MD_DIR.mkdir(parents=True, exist_ok=True)
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    source_files = sorted(SOURCE_DIR.glob("*.md"))
    source_ids = [path.stem for path in source_files]

    missing = sorted(set(EXPECTED_DOCUMENT_IDS) - set(source_ids))
    unexpected = sorted(set(source_ids) - set(EXPECTED_DOCUMENT_IDS))

    if missing:
        raise RuntimeError(
            f"Faltan documentos esperados en {SOURCE_DIR}: {missing}"
        )

    if unexpected:
        print(
            "ADVERTENCIA: se encontraron documentos adicionales "
            f"que no forman parte del corpus v1: {unexpected}"
        )

    manifest_rows = []

    for document_id in EXPECTED_DOCUMENT_IDS:
        source_path = SOURCE_DIR / f"{document_id}.md"

        print(f"Procesando {document_id}...")

        markdown = source_path.read_text(encoding="utf-8")
        markdown = normalize_newlines(markdown)

        md_path = MD_DIR / f"{document_id}.md"
        txt_path = TXT_DIR / f"{document_id}.txt"
        pdf_path = PDF_DIR / f"{document_id}.pdf"

        # Markdown controlado.
        md_path.write_text(markdown, encoding="utf-8")

        # Texto plano equivalente.
        plain_text = markdown_to_plain_text(markdown)
        txt_path.write_text(plain_text, encoding="utf-8")

        # PDF derivado del mismo Markdown fuente.
        build_pdf(markdown, pdf_path, document_id)

        prefix = document_id.split("-")[0]
        category = CATEGORY_MAP[prefix]

        manifest_rows.append(
            {
                "document_id": document_id,
                "category": category,
                "source_file": source_path.relative_to(ROOT).as_posix(),
                "md_file": md_path.relative_to(OUTPUT_DIR).as_posix(),
                "txt_file": txt_path.relative_to(OUTPUT_DIR).as_posix(),
                "pdf_file": pdf_path.relative_to(OUTPUT_DIR).as_posix(),
                "source_sha256": sha256_file(source_path),
                "md_sha256": sha256_file(md_path),
                "txt_sha256": sha256_file(txt_path),
                "pdf_sha256": sha256_file(pdf_path),
                "content_version": "v1",
            }
        )

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "document_id",
                "category",
                "source_file",
                "md_file",
                "txt_file",
                "pdf_file",
                "source_sha256",
                "md_sha256",
                "txt_sha256",
                "pdf_sha256",
                "content_version",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    build_readme()

    print()
    print("Corpus generado correctamente.")
    print(f"Documentos fuente: {len(EXPECTED_DOCUMENT_IDS)}")
    print(f"Markdown: {len(list(MD_DIR.glob('*.md')))}")
    print(f"TXT: {len(list(TXT_DIR.glob('*.txt')))}")
    print(f"PDF: {len(list(PDF_DIR.glob('*.pdf')))}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"README: {README_PATH}")


if __name__ == "__main__":
    main()
