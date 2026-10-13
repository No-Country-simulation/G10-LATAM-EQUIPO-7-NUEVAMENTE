from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient


# ============================================================
# ROOT / PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DATA_IA_DIR = ROOT / "Data_IA"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(DATA_IA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_IA_DIR))

CORPUS_DIR = DATA_IA_DIR / "data" / "format_corpus_v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.csv"

OUTPUT_DIR = (
    CORPUS_DIR
    / "results"
    / "multiformat_end_to_end"
)

FORMATS = ("md", "txt", "pdf")

GENERATED_FORMATS = (
    "quiz",
    "flashcards",
    "tldr",
    "video_script",
)

DEFAULT_DOCUMENT_ID = "FE-ES-001"

DEFAULT_PROFILE = "student"
DEFAULT_NICHE = "frontend"
DEFAULT_DETAIL_LEVEL = "medium"
DEFAULT_LEARNING_OBJECTIVE = (
    "Comprender los conceptos principales del documento "
    "y poder explicarlos correctamente."
)

TOP_K = 5

INDEX_DIRS = {
    "md": ROOT / ".multiformat_e2e_chroma_md",
    "txt": ROOT / ".multiformat_e2e_chroma_txt",
    "pdf": ROOT / ".multiformat_e2e_chroma_pdf",
}

COLLECTIONS = {
    "md": "multiformat_e2e_md",
    "txt": "multiformat_e2e_txt",
    "pdf": "multiformat_e2e_pdf",
}


# ============================================================
# PROJECT IMPORTS
# ============================================================

from agentes.rag.extractor import extract_document
from agentes.rag.cleaner import clean_text
from agentes.rag.chunker import create_chunks
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.vector_store import VectorStore
from agentes.agent_v1 import AgentV1

from data_ai.api.app import app as data_ia_app
from data_ai.schemas.format_evaluation import EvaluationRequest

try:
    from pydantic import TypeAdapter
except ImportError as exc:
    raise RuntimeError(
        "Este script requiere Pydantic v2."
    ) from exc


# ============================================================
# IO HELPERS
# ============================================================

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fieldnames: list[str] = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(
    path: Path,
    data: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def remove_existing_index(
    path: Path,
) -> None:
    if path.exists():
        shutil.rmtree(path)


# ============================================================
# MANIFEST / CORPUS
# ============================================================

def load_manifest_row(
    document_id: str,
) -> dict[str, str]:
    rows = read_csv(
        MANIFEST_PATH
    )

    matches = [
        row
        for row in rows
        if row.get(
            "document_id"
        ) == document_id
    ]

    if not matches:
        available = ", ".join(
            sorted(
                row.get(
                    "document_id",
                    "",
                )
                for row in rows
            )
        )
        raise ValueError(
            f"document_id '{document_id}' "
            f"no está en manifest.csv. "
            f"Disponibles: {available}"
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"document_id duplicado en manifest: "
            f"{document_id}"
        )

    return matches[0]


def resolve_format_path(
    manifest_row: dict[str, str],
    fmt: str,
) -> Path:
    column = f"{fmt}_file"

    if column not in manifest_row:
        raise KeyError(
            f"manifest.csv no contiene "
            f"la columna '{column}'."
        )

    path = (
        CORPUS_DIR
        / manifest_row[column]
    )

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return path


# ============================================================
# EXTRACTION / CHUNKING
# ============================================================

def build_chunks_for_file(
    *,
    path: Path,
    document_id: str,
    category: str,
    fmt: str,
):
    documents = extract_document(
        str(path)
    )

    if not documents:
        raise RuntimeError(
            f"{fmt.upper()}: "
            "extract_document no devolvió documentos."
        )

    total_chars_before = sum(
        len(
            document.text
            or ""
        )
        for document in documents
    )

    for document in documents:
        document.text = clean_text(
            document.text
        )

        document.metadata[
            "document_id"
        ] = document_id

        document.metadata[
            "category"
        ] = category

        document.metadata[
            "controlled_format"
        ] = fmt

        document.metadata[
            "source"
        ] = path.name

    total_chars_after = sum(
        len(
            document.text
            or ""
        )
        for document in documents
    )

    chunks = create_chunks(
        documents
    )

    if not chunks:
        raise RuntimeError(
            f"{fmt.upper()}: "
            "create_chunks no produjo chunks."
        )

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        if not getattr(
            chunk,
            "metadata",
            None,
        ):
            chunk.metadata = {}

        chunk.metadata[
            "document_id"
        ] = document_id

        chunk.metadata[
            "category"
        ] = category

        chunk.metadata[
            "controlled_format"
        ] = fmt

        chunk.metadata[
            "source"
        ] = path.name

        # Fallback útil si el chunker no conserva un identificador estable.
        if not getattr(
            chunk,
            "chunk_id",
            None,
        ):
            chunk.chunk_id = (
                f"{document_id}_{fmt}_"
                f"CH_{index:03d}"
            )

    stats = {
        "format": fmt,
        "source_file": path.name,
        "documents_extracted": len(
            documents
        ),
        "chars_before_cleaning": (
            total_chars_before
        ),
        "chars_after_cleaning": (
            total_chars_after
        ),
        "chunks_created": len(
            chunks
        ),
    }

    return chunks, stats


# ============================================================
# GENERATION / DATA-IA CONTRACT
# ============================================================

def build_generation_query(
    *,
    niche: str,
    profile: str,
    detail_level: str,
    learning_objective: str | None,
) -> str:
    query = (
        f"Explica los conceptos principales sobre "
        f"{niche} para un perfil {profile} "
        f"con nivel {detail_level}."
    )

    if learning_objective:
        query += (
            " Objetivo de aprendizaje: "
            + learning_objective
        )

    return query


def build_data_ia_payload(
    *,
    document_id: str,
    generated_format: str,
    content: dict[str, Any],
    sources_used: list[dict[str, Any]],
    profile: str,
    niche: str,
    detail_level: str,
    learning_objective: str | None,
) -> dict[str, Any]:
    generation_context: dict[
        str,
        Any,
    ] = {
        "profile": profile,
        "niche": niche,
        "detail_level": (
            detail_level
        ),
    }

    if learning_objective:
        generation_context[
            "learning_objective"
        ] = learning_objective

    chunks_used = []

    for rank, source in enumerate(
        sources_used,
        start=1,
    ):
        chunks_used.append(
            {
                "chunk_id": str(
                    source.get(
                        "chunk_id"
                    )
                    or (
                        f"{document_id}"
                        f"_retrieved_"
                        f"{rank:03d}"
                    )
                ),
                "document_id": str(
                    source.get(
                        "document_id"
                    )
                    or document_id
                ),
                "rank": int(
                    source.get(
                        "rank"
                    )
                    or rank
                ),
                "score": float(
                    source.get(
                        "score"
                    )
                    or 0.0
                ),
                "text": str(
                    source.get(
                        "text"
                    )
                    or ""
                ),
            }
        )

    return {
        "document_id":
            document_id,
        "format":
            generated_format,
        "generated_content":
            content,
        "generation_context":
            generation_context,
        "chunks_used":
            chunks_used,
    }


def validate_payload_locally(
    payload: dict[str, Any],
) -> tuple[bool, str | None]:
    try:
        adapter = TypeAdapter(
            EvaluationRequest
        )
        adapter.validate_python(
            payload
        )
        return True, None
    except Exception as exc:
        return (
            False,
            f"{type(exc).__name__}: "
            f"{exc}",
        )


def evaluate_with_data_ia(
    *,
    client: TestClient,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        "/evaluate",
        json=payload,
    )

    body: Any

    try:
        body = response.json()
    except Exception:
        body = {
            "raw_text":
                response.text
        }

    return {
        "http_status":
            response.status_code,
        "body":
            body,
    }


# ============================================================
# ONE FORMAT RUN
# ============================================================

def run_one_file_format(
    *,
    fmt: str,
    source_path: Path,
    document_id: str,
    category: str,
    embedding_service,
    data_ia_client: TestClient,
    profile: str,
    niche: str,
    detail_level: str,
    learning_objective: str | None,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
]:
    started = time.perf_counter()

    index_dir = (
        INDEX_DIRS[fmt]
    )

    remove_existing_index(
        index_dir
    )

    chunks, extraction_stats = (
        build_chunks_for_file(
            path=source_path,
            document_id=document_id,
            category=category,
            fmt=fmt,
        )
    )

    vector_store = VectorStore(
        path=str(
            index_dir
        ),
        collection_name=(
            COLLECTIONS[
                fmt
            ]
        ),
        embedding_service=(
            embedding_service
        ),
    )

    vector_store.add_chunks(
        chunks
    )

    agent = AgentV1(
        vector_store=vector_store
    )

    query = build_generation_query(
        niche=niche,
        profile=profile,
        detail_level=detail_level,
        learning_objective=(
            learning_objective
        ),
    )

    generation_rows = []

    format_output_dir = (
        OUTPUT_DIR
        / fmt
    )

    format_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for generated_format in (
        GENERATED_FORMATS
    ):
        print(
            f"  → {generated_format}"
        )

        generation_started = (
            time.perf_counter()
        )

        raw_result = agent.answer(
            query=query,
            document_id=document_id,
            formato=generated_format,
            perfil=profile,
            nicho=niche,
            nivel=detail_level,
            learning_objective=(
                learning_objective
            ),
            top_k=TOP_K,
        )

        generation_seconds = (
            time.perf_counter()
            - generation_started
        )

        raw_path = (
            format_output_dir
            / (
                f"{generated_format}"
                "_generation.json"
            )
        )

        write_json(
            raw_path,
            raw_result,
        )

        generation_status = (
            raw_result.get(
                "status"
            )
        )

        content = raw_result.get(
            "content"
        )

        sources_used = (
            raw_result.get(
                "sources_used"
            )
            or []
        )

        schema_valid = False
        schema_error = None
        evaluation_http_status = None
        evaluation_status = None
        unsupported_information = None
        evaluation_error = None
        scores = {}

        payload = None
        evaluation_body = None

        if (
            generation_status
            == "success"
            and isinstance(
                content,
                dict,
            )
            and sources_used
        ):
            payload = (
                build_data_ia_payload(
                    document_id=(
                        document_id
                    ),
                    generated_format=(
                        generated_format
                    ),
                    content=content,
                    sources_used=(
                        sources_used
                    ),
                    profile=profile,
                    niche=niche,
                    detail_level=(
                        detail_level
                    ),
                    learning_objective=(
                        learning_objective
                    ),
                )
            )

            payload_path = (
                format_output_dir
                / (
                    f"{generated_format}"
                    "_evaluation_payload.json"
                )
            )

            write_json(
                payload_path,
                payload,
            )

            (
                schema_valid,
                schema_error,
            ) = (
                validate_payload_locally(
                    payload
                )
            )

            if schema_valid:
                evaluation = (
                    evaluate_with_data_ia(
                        client=(
                            data_ia_client
                        ),
                        payload=payload,
                    )
                )

                evaluation_http_status = (
                    evaluation[
                        "http_status"
                    ]
                )

                evaluation_body = (
                    evaluation[
                        "body"
                    ]
                )

                write_json(
                    format_output_dir
                    / (
                        f"{generated_format}"
                        "_evaluation_response.json"
                    ),
                    evaluation_body,
                )

                if (
                    evaluation_http_status
                    == 200
                    and isinstance(
                        evaluation_body,
                        dict,
                    )
                ):
                    evaluation_status = (
                        evaluation_body.get(
                            "status"
                        )
                    )

                    unsupported_information = (
                        evaluation_body.get(
                            "informacion_no_respaldada"
                        )
                    )

                    scores = (
                        evaluation_body.get(
                            "scores"
                        )
                        or {}
                    )
                else:
                    evaluation_error = (
                        json.dumps(
                            evaluation_body,
                            ensure_ascii=False,
                        )
                    )

        technical_pass = bool(
            generation_status
            == "success"
            and isinstance(
                content,
                dict,
            )
            and len(
                sources_used
            ) > 0
            and schema_valid
            and evaluation_http_status
            == 200
        )

        generation_rows.append(
            {
                "document_id":
                    document_id,
                "source_format":
                    fmt,
                "generated_format":
                    generated_format,
                "source_file":
                    source_path.name,
                "generation_status":
                    generation_status,
                "generation_seconds":
                    round(
                        generation_seconds,
                        3,
                    ),
                "sources_used":
                    len(
                        sources_used
                    ),
                "schema_valid":
                    schema_valid,
                "schema_error":
                    schema_error,
                "evaluation_http_status":
                    evaluation_http_status,
                "evaluation_status":
                    evaluation_status,
                "informacion_no_respaldada":
                    unsupported_information,
                "relevancia":
                    scores.get(
                        "relevancia"
                    ),
                "coherencia":
                    scores.get(
                        "coherencia"
                    ),
                "adaptacion_didactica":
                    scores.get(
                        "adaptacion_didactica"
                    ),
                "informacion_respaldada":
                    scores.get(
                        "informacion_respaldada"
                    ),
                "technical_pass":
                    technical_pass,
                "generation_error":
                    raw_result.get(
                        "error_message"
                    ),
                "evaluation_error":
                    evaluation_error,
            }
        )

    elapsed = (
        time.perf_counter()
        - started
    )

    format_summary = {
        **extraction_stats,
        "index_dir":
            str(index_dir),
        "generated_formats":
            len(
                GENERATION_FORMATS
            )
            if False
            else len(
                GENERATED_FORMATS
            ),
        "technical_passes":
            sum(
                1
                for row
                in generation_rows
                if row[
                    "technical_pass"
                ]
            ),
        "elapsed_seconds":
            round(
                elapsed,
                3,
            ),
    }

    del agent
    del vector_store
    gc.collect()

    return (
        format_summary,
        generation_rows,
    )


# ============================================================
# REPORTING
# ============================================================

def build_cross_format_summary(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []

    for generated_format in (
        GENERATED_FORMATS
    ):
        selected = [
            row
            for row in rows
            if row[
                "generated_format"
            ]
            == generated_format
        ]

        output.append(
            {
                "generated_format":
                    generated_format,
                "formats_tested":
                    len(
                        selected
                    ),
                "technical_passes":
                    sum(
                        1
                        for row
                        in selected
                        if row[
                            "technical_pass"
                        ]
                    ),
                "technical_pass_rate":
                    round(
                        (
                            sum(
                                1
                                for row
                                in selected
                                if row[
                                    "technical_pass"
                                ]
                            )
                            / len(
                                selected
                            )
                        )
                        if selected
                        else 0.0,
                        6,
                    ),
                "approved":
                    sum(
                        1
                        for row
                        in selected
                        if row[
                            "evaluation_status"
                        ]
                        == "aprobado"
                    ),
                "review":
                    sum(
                        1
                        for row
                        in selected
                        if row[
                            "evaluation_status"
                        ]
                        == "requiere_revision"
                    ),
                "rejected":
                    sum(
                        1
                        for row
                        in selected
                        if row[
                            "evaluation_status"
                        ]
                        == "rechazado"
                    ),
            }
        )

    return output


def build_readme(
    *,
    document_id: str,
    category: str,
    source_summaries: list[
        dict[str, Any]
    ],
    rows: list[
        dict[str, Any]
    ],
    cross_format: list[
        dict[str, Any]
    ],
) -> str:
    technical_total = sum(
        1
        for row in rows
        if row[
            "technical_pass"
        ]
    )

    lines = [
        "# Multiformat End-to-End Validation",
        "",
        "## Objetivo",
        "",
        "Validar el flujo técnico completo de NuevaMente para un mismo contenido",
        "equivalente en Markdown, TXT y PDF.",
        "",
        "```text",
        "archivo",
        "→ extracción",
        "→ limpieza",
        "→ chunking",
        "→ embeddings / indexación",
        "→ retrieval",
        "→ generación",
        "→ contrato Backend → Data/IA",
        "→ validación Pydantic",
        "→ POST /evaluate",
        "```",
        "",
        f"- Documento: `{document_id}`",
        f"- Categoría: `{category}`",
        f"- Top-K: `{TOP_K}`",
        f"- Combinaciones: `{len(rows)}`",
        f"- Technical passes: `{technical_total}/{len(rows)}`",
        "",
        "Un `technical_pass` exige generación `success`, evidencia recuperada,",
        "payload válido y respuesta HTTP 200 de Data/IA. Un resultado de calidad",
        "`rechazado` puede seguir siendo un technical pass: calidad y contrato",
        "se reportan por separado.",
        "",
        "## Extracción e indexación",
        "",
        "| Formato | Archivo | Docs | Chunks | Technical passes | Tiempo (s) |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for row in source_summaries:
        lines.append(
            f"| {row['format'].upper()} | "
            f"{row['source_file']} | "
            f"{row['documents_extracted']} | "
            f"{row['chunks_created']} | "
            f"{row['technical_passes']}/{len(GENERATED_FORMATS)} | "
            f"{row['elapsed_seconds']} |"
        )

    lines.extend(
        [
            "",
            "## Resultado por combinación",
            "",
            "| Source | Generated | Gen | Sources | Schema | HTTP | Quality | Technical |",
            "|---|---|---|---:|---|---:|---|---|",
        ]
    )

    for row in rows:
        lines.append(
            f"| {row['source_format'].upper()} | "
            f"{row['generated_format']} | "
            f"{row['generation_status']} | "
            f"{row['sources_used']} | "
            f"{row['schema_valid']} | "
            f"{row['evaluation_http_status'] or '-'} | "
            f"{row['evaluation_status'] or '-'} | "
            f"{row['technical_pass']} |"
        )

    lines.extend(
        [
            "",
            "## Resumen por contenido generado",
            "",
            "| Formato generado | Tested | Technical pass rate | Approved | Review | Rejected |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )

    for row in cross_format:
        lines.append(
            f"| {row['generated_format']} | "
            f"{row['formats_tested']} | "
            f"{row['technical_pass_rate']:.2%} | "
            f"{row['approved']} | "
            f"{row['review']} | "
            f"{row['rejected']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretación",
            "",
            "- `technical_pass=True`: el flujo de integración llegó correctamente hasta Data/IA.",
            "- `aprobado/requiere_revision/rechazado`: resultado de calidad, no de conectividad.",
            "- Revisar los JSON individuales cuando un schema o evaluación falle.",
            "",
            "Los índices Chroma creados por este script son regenerables y no deben versionarse.",
        ]
    )

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


# ============================================================
# CLI / MAIN
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida NuevaMente end-to-end "
            "para MD/TXT/PDF y los cuatro "
            "formatos generados."
        )
    )

    parser.add_argument(
        "--document-id",
        default=DEFAULT_DOCUMENT_ID,
    )

    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
    )

    parser.add_argument(
        "--niche",
        default=DEFAULT_NICHE,
    )

    parser.add_argument(
        "--detail-level",
        default=DEFAULT_DETAIL_LEVEL,
    )

    parser.add_argument(
        "--learning-objective",
        default=(
            DEFAULT_LEARNING_OBJECTIVE
        ),
    )

    parser.add_argument(
        "--source-format",
        choices=["md", "txt", "pdf", "all"],
        default="all",
    )
    
    return parser.parse_args()


def validate_environment() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            MANIFEST_PATH
        )

    if not os.getenv(
        "GEMINI_API_KEY"
    ):
        raise RuntimeError(
            "Falta GEMINI_API_KEY "
            "en el entorno/.env."
        )

    if not os.getenv(
        "GEMINI_MODEL"
    ):
        raise RuntimeError(
            "Falta GEMINI_MODEL "
            "en el entorno/.env."
        )


def main() -> int:
    args = parse_args()

    formats_to_run = (
        FORMATS
        if args.source_format == "all"
        else (args.source_format,)
    )
    
    validate_environment()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_row = (
        load_manifest_row(
            args.document_id
        )
    )

    category = (
        manifest_row.get(
            "category"
        )
        or ""
    )

    print(
        "=== MULTIFORMAT "
        "END-TO-END VALIDATION ==="
    )
    print(
        "Document:",
        args.document_id,
    )
    print(
        "Category:",
        category,
    )
    print(
        "Source formats:",
        ", ".join(
            fmt.upper()
            for fmt
            in formats_to_run
        ),
    )
    print(
        "Generated formats:",
        ", ".join(
            GENERATED_FORMATS
        ),
    )
    print(
        "Combinations:",
        len(formats_to_run)
        * len(
            GENERATED_FORMATS
        ),
    )
    print()

    print(
        "Cargando embeddings..."
    )

    embedding_service = (
        MultilingualEmbedding()
    )

    data_ia_client = TestClient(
        data_ia_app
    )

    source_summaries = []
    all_rows = []


    
    for fmt in formats_to_run:
        source_path = (
            resolve_format_path(
                manifest_row,
                fmt,
            )
        )

        print()
        print(
            "=" * 72
        )
        print(
            f"{fmt.upper()} "
            f"→ {source_path.name}"
        )
        print(
            "=" * 72
        )

        try:
            (
                source_summary,
                generation_rows,
            ) = (
                run_one_file_format(
                    fmt=fmt,
                    source_path=(
                        source_path
                    ),
                    document_id=(
                        args.document_id
                    ),
                    category=category,
                    embedding_service=(
                        embedding_service
                    ),
                    data_ia_client=(
                        data_ia_client
                    ),
                    profile=(
                        args.profile
                    ),
                    niche=args.niche,
                    detail_level=(
                        args.detail_level
                    ),
                    learning_objective=(
                        args.learning_objective
                    ),
                )
            )

            source_summaries.append(
                source_summary
            )

            all_rows.extend(
                generation_rows
            )

        except Exception as exc:
            print(
                f"[ERROR {fmt.upper()}] "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            source_summaries.append(
                {
                    "format":
                        fmt,
                    "source_file":
                        source_path.name,
                    "documents_extracted":
                        None,
                    "chars_before_cleaning":
                        None,
                    "chars_after_cleaning":
                        None,
                    "chunks_created":
                        None,
                    "index_dir":
                        str(
                            INDEX_DIRS[
                                fmt
                            ]
                        ),
                    "generated_formats":
                        0,
                    "technical_passes":
                        0,
                    "elapsed_seconds":
                        None,
                    "error":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                }
            )

    cross_format = (
        build_cross_format_summary(
            all_rows
        )
    )

    write_csv(
        OUTPUT_DIR
        / "source_pipeline_summary.csv",
        source_summaries,
    )

    write_csv(
        OUTPUT_DIR
        / "end_to_end_results.csv",
        all_rows,
    )

    write_csv(
        OUTPUT_DIR
        / "generated_format_summary.csv",
        cross_format,
    )

    manifest_output = {
        "experiment":
            "multiformat_end_to_end_v1",
        "timestamp_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),
        "document_id":
            args.document_id,
        "category":
            category,
        "source_formats":
            list(
                FORMATS
            ),
        "generated_formats":
            list(
                GENERATED_FORMATS
            ),
        "top_k":
            TOP_K,
        "profile":
            args.profile,
        "niche":
            args.niche,
        "detail_level":
            args.detail_level,
        "learning_objective":
            args.learning_objective,
        "technical_pass_definition": (
            "generation success + "
            "sources_used > 0 + "
            "EvaluationRequest valid + "
            "POST /evaluate HTTP 200"
        ),
    }

    write_json(
        OUTPUT_DIR
        / "run_manifest.json",
        manifest_output,
    )

    readme = build_readme(
        document_id=(
            args.document_id
        ),
        category=category,
        source_summaries=(
            source_summaries
        ),
        rows=all_rows,
        cross_format=(
            cross_format
        ),
    )

    (
        OUTPUT_DIR
        / "README.md"
    ).write_text(
        readme,
        encoding="utf-8",
    )

    print()
    print(
        "=" * 72
    )
    print(
        "RESUMEN FINAL"
    )
    print(
        "=" * 72
    )

    if all_rows:
        display_columns = [
            "source_format",
            "generated_format",
            "generation_status",
            "sources_used",
            "schema_valid",
            "evaluation_http_status",
            "evaluation_status",
            "technical_pass",
        ]

        print(
            pd.DataFrame(
                all_rows
            )[
                display_columns
            ].to_string(
                index=False
            )
        )

    technical_passes = sum(
        1
        for row in all_rows
        if row[
            "technical_pass"
        ]
    )

    expected = (
        len(formats_to_run)
        * len(
            GENERATED_FORMATS
        )
    )

    print()
    print(
        "Technical passes:",
        f"{technical_passes}/{expected}",
    )
    print(
        "Artefactos:",
        OUTPUT_DIR,
    )

    # Exit code 0 únicamente si las 12 combinaciones completan
    # correctamente el flujo técnico.
    return (
        0
        if (
            len(all_rows)
            == expected
            and technical_passes
            == expected
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
