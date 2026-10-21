from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".md",
    ".txt",
    ".csv",
}

CSV_TEXT_COLUMNS = (
    "claim_text",
    "text",
    "content",
    "sentence",
    "summary",
    "key_point",
    "question",
    "answer",
    "explanation",
    "front",
    "back",
    "narration",
)

MIN_TEXT_LENGTH = 8
MAX_TEXT_LENGTH = 600


@dataclass(frozen=True)
class RawCandidate:
    claim_text: str
    source_domain: str
    source_reference: str
    extraction_type: str

    @property
    def normalized_text(self) -> str:
        return normalize_text(self.claim_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrae candidatos textuales para Claim Atomization "
            "External Validation v1 sin utilizar LLMs."
        )
    )

    parser.add_argument(
        "--sources-dir",
        type=Path,
        default=Path(
            "data/evaluation/atomization_external_v1/sources"
        ),
        help="Directorio con fuentes externas/nuevas.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/evaluation/atomization_external_v1/"
            "dataset/external_claim_candidates_v1.csv"
        ),
        help="CSV de candidatos para revisión humana.",
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "data/evaluation/atomization_external_v1/"
            "manifest/external_candidate_extraction_manifest_v1.json"
        ),
        help="Manifest de extracción.",
    )

    parser.add_argument(
        "--min-length",
        type=int,
        default=MIN_TEXT_LENGTH,
        help="Longitud mínima del fragmento.",
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=MAX_TEXT_LENGTH,
        help="Longitud máxima del fragmento.",
    )

    return parser.parse_args()


def normalize_text(text: str) -> str:
    text = text.strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = re.sub(r"\s+", " ", text)
    text = re.sub(
        r"[^\w\s]",
        "",
        text,
        flags=re.UNICODE,
    )

    return text.strip()


def clean_markdown_syntax(text: str) -> str:
    """
    Elimina únicamente sintaxis superficial de Markdown.

    No reescribe ni parafrasea el contenido.
    """
    text = text.strip()

    text = re.sub(
        r"^#{1,6}\s+",
        "",
        text,
    )

    text = re.sub(
        r"^>\s*",
        "",
        text,
    )

    text = re.sub(
        r"^[-*+]\s+",
        "",
        text,
    )

    text = re.sub(
        r"^\d+[.)]\s+",
        "",
        text,
    )

    text = re.sub(
        r"^\[[ xX]\]\s+",
        "",
        text,
    )

    return text.strip()


def is_probably_code(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return False

    code_signals = (
        "def ",
        "class ",
        "import ",
        "from ",
        "return ",
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "CREATE TABLE",
        "console.log(",
        "print(",
    )

    if any(
        stripped.startswith(signal)
        for signal in code_signals
    ):
        return True

    if stripped.startswith(
        ("```", "{", "}", "[", "]")
    ):
        return True

    return False


def is_noise(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return True

    if stripped in {
        "---",
        "***",
        "___",
    }:
        return True

    if re.fullmatch(
        r"[-=_#*`~\s]+",
        stripped,
    ):
        return True

    if stripped.startswith(
        (
            "http://",
            "https://",
            "www.",
        )
    ):
        return True

    return False


def split_sentences(text: str) -> list[str]:
    """
    Segmentación superficial y determinista.

    No intenta interpretar semánticamente el texto.
    """
    text = re.sub(
        r"\s+",
        " ",
        text.strip(),
    )

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡0-9])",
        text,
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def valid_length(
    text: str,
    min_length: int,
    max_length: int,
) -> bool:
    length = len(text.strip())

    return (
        min_length
        <= length
        <= max_length
    )


def infer_domain_from_path(
    file_path: Path,
    sources_dir: Path,
) -> str:
    """
    Usa la primera carpeta debajo de sources/ como dominio.

    Ejemplo:
    sources/backend/doc.md
    -> backend

    Si el archivo está directamente en sources/,
    devuelve 'unclassified'.
    """
    relative = file_path.relative_to(
        sources_dir
    )

    if len(relative.parts) >= 2:
        return relative.parts[0]

    return "unclassified"


def build_source_reference(
    file_path: Path,
    sources_dir: Path,
) -> str:
    return str(
        file_path.relative_to(sources_dir)
    ).replace("\\", "/")


def extract_from_text_file(
    path: Path,
    *,
    source_domain: str,
    source_reference: str,
    min_length: int,
    max_length: int,
) -> list[RawCandidate]:
    content = path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

    candidates: list[RawCandidate] = []

    for raw_line in content.splitlines():
        line = clean_markdown_syntax(
            raw_line
        )

        if is_noise(line):
            continue

        if is_probably_code(line):
            continue

        for sentence in split_sentences(
            line
        ):
            sentence = sentence.strip()

            if not valid_length(
                sentence,
                min_length,
                max_length,
            ):
                continue

            candidates.append(
                RawCandidate(
                    claim_text=sentence,
                    source_domain=source_domain,
                    source_reference=(
                        source_reference
                    ),
                    extraction_type=(
                        "literal_text"
                    ),
                )
            )

    return candidates


def choose_csv_text_columns(
    fieldnames: list[str],
) -> list[str]:
    normalized_map = {
        column.lower().strip(): column
        for column in fieldnames
    }

    chosen = []

    for expected in CSV_TEXT_COLUMNS:
        actual = normalized_map.get(
            expected
        )

        if actual:
            chosen.append(actual)

    return chosen


def extract_from_csv(
    path: Path,
    *,
    source_domain: str,
    source_reference: str,
    min_length: int,
    max_length: int,
) -> list[RawCandidate]:
    candidates: list[RawCandidate] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            return candidates

        text_columns = (
            choose_csv_text_columns(
                reader.fieldnames
            )
        )

        if not text_columns:
            print(
                "WARNING: CSV sin columnas "
                "textuales reconocidas: "
                f"{source_reference}"
            )
            return candidates

        for row in reader:
            for column in text_columns:
                raw_value = (
                    row.get(column) or ""
                ).strip()

                if not raw_value:
                    continue

                for sentence in split_sentences(
                    raw_value
                ):
                    sentence = (
                        clean_markdown_syntax(
                            sentence
                        )
                    )

                    if is_noise(sentence):
                        continue

                    if is_probably_code(
                        sentence
                    ):
                        continue

                    if not valid_length(
                        sentence,
                        min_length,
                        max_length,
                    ):
                        continue

                    candidates.append(
                        RawCandidate(
                            claim_text=sentence,
                            source_domain=(
                                source_domain
                            ),
                            source_reference=(
                                source_reference
                            ),
                            extraction_type=(
                                "literal_csv:"
                                f"{column}"
                            ),
                        )
                    )

    return candidates


def extract_file(
    path: Path,
    *,
    sources_dir: Path,
    min_length: int,
    max_length: int,
) -> list[RawCandidate]:
    source_domain = (
        infer_domain_from_path(
            path,
            sources_dir,
        )
    )

    source_reference = (
        build_source_reference(
            path,
            sources_dir,
        )
    )

    if path.suffix.lower() in {
        ".md",
        ".txt",
    }:
        return extract_from_text_file(
            path,
            source_domain=source_domain,
            source_reference=(
                source_reference
            ),
            min_length=min_length,
            max_length=max_length,
        )

    if path.suffix.lower() == ".csv":
        return extract_from_csv(
            path,
            source_domain=source_domain,
            source_reference=(
                source_reference
            ),
            min_length=min_length,
            max_length=max_length,
        )

    return []


def collect_source_files(
    sources_dir: Path,
) -> list[Path]:
    if not sources_dir.exists():
        raise FileNotFoundError(
            "No existe el directorio de "
            f"fuentes: {sources_dir}"
        )

    files = [
        path
        for path in sources_dir.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )
    ]

    return sorted(files)


def deduplicate_candidates(
    candidates: list[RawCandidate],
) -> tuple[
    list[RawCandidate],
    int,
]:
    seen: set[str] = set()
    clean: list[RawCandidate] = []

    duplicates = 0

    for candidate in candidates:
        normalized = (
            candidate.normalized_text
        )

        if not normalized:
            continue

        if normalized in seen:
            duplicates += 1
            continue

        seen.add(normalized)
        clean.append(candidate)

    return clean, duplicates


def candidate_id(
    index: int,
) -> str:
    return f"EXT-CAND-V1-{index:04d}"


def normalized_hash(
    candidate: RawCandidate,
) -> str:
    return hashlib.sha256(
        candidate.normalized_text.encode(
            "utf-8"
        )
    ).hexdigest()


def write_candidates(
    output_path: Path,
    candidates: list[RawCandidate],
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "source_claim_id",
        "claim_text",
        "format",
        "source_domain",
        "source_reference",
        "target_bucket",
        "selection_status",
        "notes",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):
            writer.writerow(
                {
                    "source_claim_id": (
                        candidate_id(index)
                    ),
                    "claim_text": (
                        candidate.claim_text
                    ),
                    "format": (
                        "needs_review"
                    ),
                    "source_domain": (
                        candidate.source_domain
                    ),
                    "source_reference": (
                        candidate.source_reference
                    ),
                    "target_bucket": (
                        "needs_review"
                    ),
                    "selection_status": (
                        "needs_review"
                    ),
                    "notes": (
                        "extraction_type="
                        f"{candidate.extraction_type};"
                        " normalized_sha256="
                        f"{normalized_hash(candidate)}"
                    ),
                }
            )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(65536),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def write_manifest(
    *,
    path: Path,
    sources_dir: Path,
    source_files: list[Path],
    raw_count: int,
    final_count: int,
    duplicate_count: int,
    output_path: Path,
    min_length: int,
    max_length: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    extension_counts = Counter(
        source_file.suffix.lower()
        for source_file in source_files
    )

    domain_counts = Counter(
        infer_domain_from_path(
            source_file,
            sources_dir,
        )
        for source_file in source_files
    )

    manifest = {
        "experiment": (
            "claim_atomization_external_validation_v1"
        ),
        "stage": (
            "candidate_extraction"
        ),
        "component_under_test": (
            "claim-atomizer-v0.4"
        ),
        "model_executed": False,
        "llm_used_for_extraction": False,
        "prompt_tuning_performed": False,
        "extraction_policy": (
            "literal_source_text_only"
        ),
        "source_directory": str(
            sources_dir
        ),
        "supported_extensions": sorted(
            SUPPORTED_EXTENSIONS
        ),
        "source_file_count": len(
            source_files
        ),
        "source_extension_distribution": (
            dict(
                sorted(
                    extension_counts.items()
                )
            )
        ),
        "source_domain_distribution": (
            dict(
                sorted(
                    domain_counts.items()
                )
            )
        ),
        "filters": {
            "minimum_character_length": (
                min_length
            ),
            "maximum_character_length": (
                max_length
            ),
            "code_filter_enabled": True,
            "noise_filter_enabled": True,
        },
        "candidate_counts": {
            "raw_extracted": raw_count,
            "duplicate_removed": (
                duplicate_count
            ),
            "final_review_pool": (
                final_count
            ),
        },
        "output": {
            "candidate_file": str(
                output_path
            ),
            "candidate_file_sha256": (
                sha256_file(output_path)
            ),
        },
        "human_review_required_for": [
            "format",
            "target_bucket",
            "selection_status",
        ],
        "methodological_notes": [
            (
                "No LLM is used during "
                "candidate extraction."
            ),
            (
                "Candidate text is extracted "
                "literally from source files."
            ),
            (
                "The extractor does not assign "
                "atomization classes."
            ),
            (
                "The extractor does not create "
                "ground truth."
            ),
            (
                "Duplicate removal uses "
                "normalized exact text only."
            ),
            (
                "Previous-corpus overlap is "
                "validated later by the "
                "external dataset builder."
            ),
        ],
        "status": (
            "candidate_pool_requires_"
            "human_review"
        ),
    }

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")


def print_summary(
    *,
    source_files: list[Path],
    raw_count: int,
    final_count: int,
    duplicate_count: int,
    output_path: Path,
    manifest_path: Path,
) -> None:
    print()
    print(
        "External Claim Candidate "
        "Extraction v1"
    )
    print("=" * 42)

    print(
        f"Source files: {len(source_files)}"
    )

    print(
        f"Raw candidates: {raw_count}"
    )

    print(
        "Duplicates removed: "
        f"{duplicate_count}"
    )

    print(
        "Review candidates: "
        f"{final_count}"
    )

    print()
    print(
        f"Candidates: {output_path}"
    )
    print(
        f"Manifest: {manifest_path}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "format, target_bucket and "
        "selection_status require "
        "human review."
    )

    print(
        "Do not execute the dataset "
        "builder before completing "
        "that review."
    )


def main() -> None:
    args = parse_args()

    if args.min_length <= 0:
        raise ValueError(
            "--min-length debe ser > 0."
        )

    if (
        args.max_length
        < args.min_length
    ):
        raise ValueError(
            "--max-length debe ser "
            ">= --min-length."
        )

    source_files = (
        collect_source_files(
            args.sources_dir
        )
    )

    if not source_files:
        raise ValueError(
            "No se encontraron archivos "
            "compatibles en "
            f"{args.sources_dir}. "
            "Extensiones soportadas: "
            + ", ".join(
                sorted(
                    SUPPORTED_EXTENSIONS
                )
            )
        )

    raw_candidates: list[
        RawCandidate
    ] = []

    for source_file in source_files:
        extracted = extract_file(
            source_file,
            sources_dir=args.sources_dir,
            min_length=args.min_length,
            max_length=args.max_length,
        )

        print(
            f"{source_file}: "
            f"{len(extracted)} candidatos"
        )

        raw_candidates.extend(
            extracted
        )

    (
        clean_candidates,
        duplicate_count,
    ) = deduplicate_candidates(
        raw_candidates
    )

    write_candidates(
        output_path=args.output,
        candidates=clean_candidates,
    )

    write_manifest(
        path=args.manifest,
        sources_dir=args.sources_dir,
        source_files=source_files,
        raw_count=len(
            raw_candidates
        ),
        final_count=len(
            clean_candidates
        ),
        duplicate_count=(
            duplicate_count
        ),
        output_path=args.output,
        min_length=args.min_length,
        max_length=args.max_length,
    )

    print_summary(
        source_files=source_files,
        raw_count=len(raw_candidates),
        final_count=len(
            clean_candidates
        ),
        duplicate_count=(
            duplicate_count
        ),
        output_path=args.output,
        manifest_path=args.manifest,
    )


if __name__ == "__main__":
    main()