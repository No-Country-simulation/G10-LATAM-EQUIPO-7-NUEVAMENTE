from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ALLOWED_BUCKETS = {
    "atomic",
    "compound",
    "relational",
    "non_propositional",
}

ALLOWED_FORMATS = {
    "quiz",
    "flashcards",
    "tldr",
    "video_script",
}

DEFAULT_TARGET_PER_BUCKET = 20
DEFAULT_SEED = 20261021


@dataclass(frozen=True)
class Candidate:
    source_claim_id: str
    claim_text: str
    format: str
    source_domain: str
    source_reference: str
    target_bucket: str
    selection_status: str
    notes: str

    @property
    def normalized_claim(self) -> str:
        return normalize_text(self.claim_text)


def normalize_text(text: str) -> str:
    """
    Normalización utilizada únicamente para detectar duplicados exactos
    o overlap textual normalizado.

    No intenta medir similitud semántica.
    """
    text = text.strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)

    return text.strip()


def stable_hash(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Construye el dataset externo balanceado para "
            "Claim Atomization External Validation v1."
        )
    )

    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path(
            "data/evaluation/atomization_external_v1/"
            "dataset/external_claim_candidates_v1.csv"
        ),
        help="CSV con el pool de candidatos.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/evaluation/atomization_external_v1/"
            "dataset/external_dataset_v1.csv"
        ),
        help="Dataset externo final.",
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "data/evaluation/atomization_external_v1/"
            "manifest/external_dataset_build_manifest_v1.json"
        ),
        help="Manifest de construcción del dataset.",
    )

    parser.add_argument(
        "--target-per-bucket",
        type=int,
        default=DEFAULT_TARGET_PER_BUCKET,
        help="Cantidad objetivo por bucket.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Seed para selección reproducible.",
    )

    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo requerido: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"El archivo no contiene encabezado: {path}"
            )

        return [
            {
                key: (value or "").strip()
                for key, value in row.items()
            }
            for row in reader
        ]


def load_candidates(path: Path) -> list[Candidate]:
    required_columns = {
        "source_claim_id",
        "claim_text",
        "format",
        "source_domain",
        "source_reference",
        "target_bucket",
        "selection_status",
        "notes",
    }

    rows = read_csv_rows(path)

    if not rows:
        raise ValueError(
            f"El archivo de candidatos está vacío: {path}"
        )

    missing_columns = (
        required_columns - set(rows[0].keys())
    )

    if missing_columns:
        raise ValueError(
            "Faltan columnas requeridas en candidates CSV: "
            + ", ".join(sorted(missing_columns))
        )

    candidates: list[Candidate] = []

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        candidate = Candidate(
            source_claim_id=row["source_claim_id"],
            claim_text=row["claim_text"],
            format=row["format"],
            source_domain=row["source_domain"],
            source_reference=row["source_reference"],
            target_bucket=row["target_bucket"],
            selection_status=row["selection_status"],
            notes=row["notes"],
        )

        validate_candidate(
            candidate=candidate,
            row_number=row_number,
        )

        candidates.append(candidate)

    return candidates


def validate_candidate(
    candidate: Candidate,
    row_number: int,
) -> None:
    if not candidate.source_claim_id:
        raise ValueError(
            f"Fila {row_number}: source_claim_id vacío."
        )

    if not candidate.claim_text:
        raise ValueError(
            f"Fila {row_number}: claim_text vacío."
        )

    if candidate.target_bucket not in ALLOWED_BUCKETS:
        raise ValueError(
            f"Fila {row_number}: target_bucket inválido "
            f"'{candidate.target_bucket}'."
        )

    if candidate.format not in ALLOWED_FORMATS:
        raise ValueError(
            f"Fila {row_number}: format inválido "
            f"'{candidate.format}'."
        )

    if candidate.selection_status != "candidate":
        raise ValueError(
            f"Fila {row_number}: selection_status debe ser "
            "'candidate' antes de construir el dataset."
        )

    if not candidate.normalized_claim:
        raise ValueError(
            f"Fila {row_number}: claim_text queda vacío "
            "después de normalización."
        )


def find_duplicate_ids(
    candidates: Iterable[Candidate],
) -> list[str]:
    counts = Counter(
        candidate.source_claim_id
        for candidate in candidates
    )

    return sorted(
        claim_id
        for claim_id, count in counts.items()
        if count > 1
    )


def find_duplicate_claims(
    candidates: Iterable[Candidate],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}

    for candidate in candidates:
        grouped.setdefault(
            candidate.normalized_claim,
            [],
        ).append(candidate.source_claim_id)

    return {
        normalized: ids
        for normalized, ids in grouped.items()
        if len(ids) > 1
    }


def extract_claim_texts_from_csv(
    path: Path,
) -> set[str]:
    """
    Extrae textos de claims desde artefactos anteriores.

    Busca columnas conocidas de claim/source text.
    Si el archivo no existe, devuelve set vacío.
    """
    if not path.exists():
        return set()

    rows = read_csv_rows(path)

    if not rows:
        return set()

    possible_columns = (
        "claim_text",
        "source_claim_text",
        "source_text",
        "claim",
    )

    available_column = next(
        (
            column
            for column in possible_columns
            if column in rows[0]
        ),
        None,
    )

    if available_column is None:
        return set()

    values: set[str] = set()

    for row in rows:
        raw_value = row.get(
            available_column,
            "",
        )

        normalized = normalize_text(raw_value)

        if normalized:
            values.add(normalized)

    return values


def load_previous_claims() -> tuple[set[str], list[str]]:
    """
    Reúne claims de datasets anteriores conocidos.

    Importante:
    esto comprueba overlap textual exacto normalizado.
    No es una prueba de similitud semántica.
    """
    candidate_paths = [
        Path(
            "data/evaluation/atomization_v1/"
            "atomization_dataset_v1.csv"
        ),
        Path(
            "data/evaluation/atomization_v1/"
            "holdout_v1/atomization_holdout_v1.csv"
        ),
        Path(
            "data/evaluation/atomization_v1/"
            "holdout_v1/atomization_holdout_dataset_v1.csv"
        ),
        Path(
            "data/evaluation/atomization_v1/"
            "final_eval_v1/atomization_final_eval_v1.csv"
        ),
        Path(
            "data/evaluation/atomization_v1/"
            "final_eval_v1/atomization_final_eval_dataset_v1.csv"
        ),
    ]

    previous_claims: set[str] = set()
    files_used: list[str] = []

    for path in candidate_paths:
        if not path.exists():
            continue

        extracted = extract_claim_texts_from_csv(
            path
        )

        if extracted:
            previous_claims.update(extracted)
            files_used.append(str(path))

    return previous_claims, files_used


def remove_previous_overlap(
    candidates: list[Candidate],
    previous_claims: set[str],
) -> tuple[list[Candidate], list[Candidate]]:
    clean: list[Candidate] = []
    overlap: list[Candidate] = []

    for candidate in candidates:
        if candidate.normalized_claim in previous_claims:
            overlap.append(candidate)
        else:
            clean.append(candidate)

    return clean, overlap


def select_balanced_dataset(
    candidates: list[Candidate],
    target_per_bucket: int,
    seed: int,
) -> list[Candidate]:
    grouped: dict[str, list[Candidate]] = {
        bucket: []
        for bucket in sorted(ALLOWED_BUCKETS)
    }

    for candidate in candidates:
        grouped[candidate.target_bucket].append(
            candidate
        )

    shortages: dict[str, int] = {}

    for bucket, bucket_candidates in grouped.items():
        if len(bucket_candidates) < target_per_bucket:
            shortages[bucket] = (
                target_per_bucket
                - len(bucket_candidates)
            )

    if shortages:
        detail = ", ".join(
            f"{bucket}: faltan {missing}"
            for bucket, missing
            in sorted(shortages.items())
        )

        raise ValueError(
            "No hay suficientes candidatos para "
            f"construir el dataset balanceado. {detail}"
        )

    rng = random.Random(seed)

    selected: list[Candidate] = []

    for bucket in sorted(ALLOWED_BUCKETS):
        bucket_candidates = sorted(
            grouped[bucket],
            key=lambda candidate: (
                candidate.source_claim_id,
                candidate.normalized_claim,
            ),
        )

        chosen = rng.sample(
            bucket_candidates,
            target_per_bucket,
        )

        selected.extend(chosen)

    selected.sort(
        key=lambda candidate: (
            candidate.target_bucket,
            candidate.source_claim_id,
        )
    )

    return selected


def write_dataset(
    path: Path,
    selected: list[Candidate],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "external_claim_id",
        "source_claim_id",
        "claim_text",
        "format",
        "source_domain",
        "source_reference",
        "target_bucket",
        "selection_status",
        "notes",
        "normalized_claim_sha256",
    ]

    counters: Counter[str] = Counter()

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for candidate in selected:
            counters[candidate.target_bucket] += 1

            prefix = {
                "atomic": "ATOM",
                "compound": "COMP",
                "relational": "REL",
                "non_propositional": "NONPROP",
            }[candidate.target_bucket]

            external_claim_id = (
                f"EXT-V1-{prefix}-"
                f"{counters[candidate.target_bucket]:03d}"
            )

            writer.writerow(
                {
                    "external_claim_id": external_claim_id,
                    "source_claim_id": candidate.source_claim_id,
                    "claim_text": candidate.claim_text,
                    "format": candidate.format,
                    "source_domain": candidate.source_domain,
                    "source_reference": candidate.source_reference,
                    "target_bucket": candidate.target_bucket,
                    "selection_status": "selected",
                    "notes": candidate.notes,
                    "normalized_claim_sha256": stable_hash(
                        candidate.normalized_claim
                    ),
                }
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(65536),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def write_manifest(
    path: Path,
    *,
    candidates_path: Path,
    output_path: Path,
    candidates: list[Candidate],
    clean_candidates: list[Candidate],
    overlap_candidates: list[Candidate],
    selected: list[Candidate],
    duplicate_claims: dict[str, list[str]],
    previous_files_used: list[str],
    target_per_bucket: int,
    seed: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    selected_distribution = Counter(
        candidate.target_bucket
        for candidate in selected
    )

    source_domain_distribution = Counter(
        candidate.source_domain
        for candidate in selected
    )

    format_distribution = Counter(
        candidate.format
        for candidate in selected
    )

    manifest = {
        "experiment": (
            "claim_atomization_external_validation_v1"
        ),
        "stage": "dataset_build",
        "component_under_test": (
            "claim-atomizer-v0.4"
        ),
        "model_executed": False,
        "prompt_tuning_performed": False,
        "selection_seed": seed,
        "target_per_bucket": target_per_bucket,
        "target_total": (
            target_per_bucket
            * len(ALLOWED_BUCKETS)
        ),
        "candidate_pool": {
            "input_file": str(candidates_path),
            "input_sha256": sha256_file(
                candidates_path
            ),
            "total_candidates": len(candidates),
            "after_overlap_filter": len(
                clean_candidates
            ),
            "excluded_previous_overlap": len(
                overlap_candidates
            ),
            "duplicate_normalized_claim_groups": len(
                duplicate_claims
            ),
        },
        "previous_claim_sources_checked": (
            previous_files_used
        ),
        "selection": {
            "selected_total": len(selected),
            "bucket_distribution": dict(
                sorted(
                    selected_distribution.items()
                )
            ),
            "format_distribution": dict(
                sorted(
                    format_distribution.items()
                )
            ),
            "source_domain_distribution": dict(
                sorted(
                    source_domain_distribution.items()
                )
            ),
        },
        "output": {
            "dataset_file": str(output_path),
            "dataset_sha256": sha256_file(
                output_path
            ),
        },
        "methodological_notes": [
            (
                "Selection is deterministic for the "
                "configured random seed."
            ),
            (
                "Exact normalized textual overlap is "
                "excluded before sampling."
            ),
            (
                "This script does not execute "
                "claim-atomizer-v0.4."
            ),
            (
                "This script does not create or modify "
                "ground truth."
            ),
            (
                "Semantic near-duplicate detection is "
                "outside the scope of this builder."
            ),
        ],
        "status": "dataset_built_not_frozen",
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
    candidates: list[Candidate],
    clean_candidates: list[Candidate],
    overlap_candidates: list[Candidate],
    selected: list[Candidate],
    previous_files_used: list[str],
    output_path: Path,
    manifest_path: Path,
) -> None:
    distribution = Counter(
        candidate.target_bucket
        for candidate in selected
    )

    formats = Counter(
        candidate.format
        for candidate in selected
    )

    print()
    print(
        "Claim Atomization External Dataset v1"
    )
    print("=" * 44)

    print(
        f"Candidate pool: {len(candidates)}"
    )

    print(
        "Previous-overlap excluded: "
        f"{len(overlap_candidates)}"
    )

    print(
        "Eligible after filtering: "
        f"{len(clean_candidates)}"
    )

    print(
        f"Selected: {len(selected)}"
    )

    print()
    print("Bucket distribution:")

    for bucket in sorted(distribution):
        print(
            f"  {bucket}: "
            f"{distribution[bucket]}"
        )

    print()
    print("Format distribution:")

    for format_name in sorted(formats):
        print(
            f"  {format_name}: "
            f"{formats[format_name]}"
        )

    print()
    print(
        "Previous datasets used for "
        "overlap checking:"
    )

    if previous_files_used:
        for path in previous_files_used:
            print(f"  - {path}")
    else:
        print(
            "  WARNING: no previous claim dataset "
            "was detected automatically."
        )

    print()
    print(f"Dataset: {output_path}")
    print(f"Manifest: {manifest_path}")

    print()
    print(
        "IMPORTANT: dataset status is "
        "'dataset_built_not_frozen'."
    )

    print(
        "Review and validate it before committing "
        "it as the frozen external dataset."
    )


def main() -> None:
    args = parse_args()

    if args.target_per_bucket <= 0:
        raise ValueError(
            "--target-per-bucket debe ser > 0."
        )

    candidates = load_candidates(
        args.candidates
    )

    duplicate_ids = find_duplicate_ids(
        candidates
    )

    if duplicate_ids:
        raise ValueError(
            "source_claim_id duplicados: "
            + ", ".join(duplicate_ids)
        )

    duplicate_claims = find_duplicate_claims(
        candidates
    )

    if duplicate_claims:
        print(
            "ERROR: se detectaron claims duplicados "
            "dentro del pool de candidatos."
        )

        for _, claim_ids in sorted(
            duplicate_claims.items()
        ):
            print(
                "  - "
                + ", ".join(claim_ids)
            )

        raise ValueError(
            "Elimina o resuelve duplicados antes "
            "de construir el dataset."
        )

    (
        previous_claims,
        previous_files_used,
    ) = load_previous_claims()

    (
        clean_candidates,
        overlap_candidates,
    ) = remove_previous_overlap(
        candidates,
        previous_claims,
    )

    if overlap_candidates:
        print(
            "Claims excluidos por overlap "
            "con corpus anterior:"
        )

        for candidate in overlap_candidates:
            print(
                f"  - {candidate.source_claim_id}"
            )

    selected = select_balanced_dataset(
        candidates=clean_candidates,
        target_per_bucket=(
            args.target_per_bucket
        ),
        seed=args.seed,
    )

    write_dataset(
        path=args.output,
        selected=selected,
    )

    write_manifest(
        path=args.manifest,
        candidates_path=args.candidates,
        output_path=args.output,
        candidates=candidates,
        clean_candidates=clean_candidates,
        overlap_candidates=overlap_candidates,
        selected=selected,
        duplicate_claims=duplicate_claims,
        previous_files_used=previous_files_used,
        target_per_bucket=(
            args.target_per_bucket
        ),
        seed=args.seed,
    )

    print_summary(
        candidates=candidates,
        clean_candidates=clean_candidates,
        overlap_candidates=overlap_candidates,
        selected=selected,
        previous_files_used=previous_files_used,
        output_path=args.output,
        manifest_path=args.manifest,
    )


if __name__ == "__main__":
    main()