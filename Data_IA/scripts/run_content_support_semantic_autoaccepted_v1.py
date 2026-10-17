"""Evalúa con Gemini los claims que legacy habría autoaceptado.

Este script NO modifica producción.

Objetivo:
- leer content_support_semantic_autoaccepted_manifest_v1.csv;
- recuperar chunks_used del caso original;
- evaluar cada claim contra chunks_used;
- guardar resultados de forma incremental;
- conservar successes previos y reintentar solo pendientes/failed.

Variables requeridas:
- DATA_IA_GEMINI_API_KEY
- DATA_IA_GEMINI_MODEL
"""

from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError


RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

CASES_DIR = Path(
    "data/evaluation/calibration_v1/cases"
)

INPUT_MANIFEST = (
    RESULTS_DIR
    / "content_support_semantic_autoaccepted_manifest_v1.csv"
)

OUTPUT_RESULTS = (
    RESULTS_DIR
    / "content_support_semantic_autoaccepted_results_v1.csv"
)


PROMPT_VERSION = (
    "content-support-claim-review-v0.1"
)


class ClaimSupportResult(BaseModel):
    support_status: Literal[
        "supported",
        "unsupported",
    ]

    reason: str = Field(
        min_length=1,
    )


SYSTEM_PROMPT = """
Eres un evaluador de respaldo factual.

Tu única tarea es determinar si UNA afirmación concreta está
respaldada por la evidencia proporcionada en chunks_used.

REGLAS OBLIGATORIAS

1. chunks_used es la ÚNICA evidencia factual válida.

2. NO utilices:
- conocimiento general;
- conocimiento externo;
- conocimiento interno del modelo;
- inferencias basadas en lo que normalmente es cierto.

3. Una afirmación puede considerarse supported aunque no copie
literalmente los chunks, siempre que exista equivalencia semántica clara.

4. Marca unsupported cuando la afirmación:
- introduce información nueva no presente en los chunks;
- extrapola más allá de la evidencia;
- contradice los chunks;
- afirma algo que requeriría conocimiento externo para validarse.

5. Si una parte importante de la afirmación no está respaldada,
clasifica el claim completo como unsupported.

6. No evalúes calidad pedagógica, relevancia ni estilo.

Devuelve exclusivamente:

{
  "support_status": "supported | unsupported",
  "reason": "explicación breve basada únicamente en chunks_used"
}
""".strip()


def load_csv(
    path: Path,
) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def load_case(
    calibration_id: str,
) -> dict:
    path = (
        CASES_DIR
        / f"{calibration_id}.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Case not found: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def get_chunks(
    case_data: dict,
) -> list[dict]:
    return (
        case_data[
            "evaluation_request"
        ][
            "chunks_used"
        ]
    )


def build_user_prompt(
    *,
    claim_text: str,
    chunks_used: list[dict],
) -> str:
    chunks_json = json.dumps(
        chunks_used,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
CLAIM A EVALUAR

{claim_text}

EVIDENCIA FACTUAL — CHUNKS_USED

{chunks_json}

INSTRUCCIÓN

Determina si el claim está respaldado por estos chunks.

No utilices información externa.

Recuerda:
- paráfrasis válida = supported;
- extrapolación no demostrada = unsupported;
- información nueva no presente = unsupported.
""".strip()


def create_client() -> tuple[
    genai.Client,
    str,
]:
    api_key = (
        os.getenv(
            "DATA_IA_GEMINI_API_KEY",
            "",
        )
        .strip()
    )

    model = (
        os.getenv(
            "DATA_IA_GEMINI_MODEL",
            "",
        )
        .strip()
    )

    if not api_key:
        raise RuntimeError(
            "DATA_IA_GEMINI_API_KEY "
            "is not configured."
        )

    if not model:
        raise RuntimeError(
            "DATA_IA_GEMINI_MODEL "
            "is not configured."
        )

    return (
        genai.Client(
            api_key=api_key
        ),
        model,
    )


def review_claim(
    *,
    client: genai.Client,
    model: str,
    claim_text: str,
    chunks_used: list[dict],
) -> dict[str, str | int]:
    started_at = time.perf_counter()

    try:
        response = (
            client.models.generate_content(
                model=model,
                contents=build_user_prompt(
                    claim_text=claim_text,
                    chunks_used=chunks_used,
                ),
                config=types.GenerateContentConfig(
                    system_instruction=(
                        SYSTEM_PROMPT
                    ),
                    response_mime_type=(
                        "application/json"
                    ),
                    response_schema=(
                        ClaimSupportResult
                    ),
                    temperature=0.0,
                ),
            )
        )

        parsed = getattr(
            response,
            "parsed",
            None,
        )

        if parsed is not None:
            if isinstance(
                parsed,
                BaseModel,
            ):
                result = (
                    ClaimSupportResult
                    .model_validate(
                        parsed.model_dump()
                    )
                )

            elif isinstance(
                parsed,
                dict,
            ):
                result = (
                    ClaimSupportResult
                    .model_validate(
                        parsed
                    )
                )

            else:
                result = (
                    ClaimSupportResult
                    .model_validate(
                        parsed
                    )
                )

        else:
            raw_text = (
                getattr(
                    response,
                    "text",
                    None,
                )
                or ""
            ).strip()

            if not raw_text:
                raise RuntimeError(
                    "Gemini returned "
                    "an empty response."
                )

            result = (
                ClaimSupportResult
                .model_validate_json(
                    raw_text
                )
            )

        latency_ms = int(
            (
                time.perf_counter()
                - started_at
            )
            * 1000
        )

        return {
            "semantic_status": "success",
            "semantic_supported": (
                result.support_status
            ),
            "semantic_reason": (
                result.reason
            ),
            "semantic_model": model,
            "semantic_prompt_version": (
                PROMPT_VERSION
            ),
            "semantic_latency_ms": (
                latency_ms
            ),
            "semantic_error_code": "",
            "semantic_error_message": "",
        }

    except ValidationError as exc:
        latency_ms = int(
            (
                time.perf_counter()
                - started_at
            )
            * 1000
        )

        return {
            "semantic_status": "failed",
            "semantic_supported": "",
            "semantic_reason": "",
            "semantic_model": model,
            "semantic_prompt_version": (
                PROMPT_VERSION
            ),
            "semantic_latency_ms": (
                latency_ms
            ),
            "semantic_error_code": (
                "invalid_output"
            ),
            "semantic_error_message": (
                str(exc)
            ),
        }

    except Exception as exc:
        latency_ms = int(
            (
                time.perf_counter()
                - started_at
            )
            * 1000
        )

        return {
            "semantic_status": "failed",
            "semantic_supported": "",
            "semantic_reason": "",
            "semantic_model": model,
            "semantic_prompt_version": (
                PROMPT_VERSION
            ),
            "semantic_latency_ms": (
                latency_ms
            ),
            "semantic_error_code": (
                "provider_error"
            ),
            "semantic_error_message": (
                str(exc)
            ),
        }


def make_key(
    row: dict[str, str],
) -> tuple[str, str]:
    return (
        row["calibration_id"],
        row["claim_id"],
    )


def write_results(
    rows: list[dict],
) -> None:
    fieldnames = [
        "calibration_id",
        "format",
        "claim_id",
        "claim_text",
        "legacy_ratio",
        "legacy_needs_review",
        "human_support_label",
        "human_notes",
        "semantic_status",
        "semantic_supported",
        "semantic_reason",
        "semantic_model",
        "semantic_prompt_version",
        "semantic_latency_ms",
        "semantic_error_code",
        "semantic_error_message",
    ]

    with OUTPUT_RESULTS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    manifest_rows = load_csv(
        INPUT_MANIFEST
    )

    previous_rows = load_csv(
        OUTPUT_RESULTS
    )

    previous_by_key = {
        make_key(row): row
        for row in previous_rows
    }

    successful_keys = {
        key
        for key, row
        in previous_by_key.items()
        if (
            row.get(
                "semantic_status",
                ""
            )
            == "success"
        )
    }

    pending_rows = [
        row
        for row in manifest_rows
        if make_key(row)
        not in successful_keys
    ]

    (
        client,
        model,
    ) = create_client()

    print()
    print("=" * 80)
    print(
        "CONTENT SUPPORT SEMANTIC "
        "AUTOACCEPTED REVIEW V1"
    )
    print("=" * 80)

    print(
        "Manifest claims:",
        len(manifest_rows),
    )

    print(
        "Already successful:",
        len(successful_keys),
    )

    print(
        "Pending/retry:",
        len(pending_rows),
    )

    print(
        "Model:",
        model,
    )

    updated_by_key = dict(
        previous_by_key
    )

    for index, row in enumerate(
        pending_rows,
        start=1,
    ):
        calibration_id = (
            row[
                "calibration_id"
            ]
        )

        claim_id = (
            row[
                "claim_id"
            ]
        )

        claim_text = (
            row[
                "claim_text"
            ]
        )

        case_data = load_case(
            calibration_id
        )

        chunks_used = get_chunks(
            case_data
        )

        print()
        print("-" * 70)

        print(
            f"[{index}/"
            f"{len(pending_rows)}]"
        )

        print(
            calibration_id,
            claim_id,
        )

        print(
            "HUMAN:",
            row[
                "human_support_label"
            ],
        )

        semantic_result = review_claim(
            client=client,
            model=model,
            claim_text=claim_text,
            chunks_used=chunks_used,
        )

        output_row = {
            **row,
            **semantic_result,
        }

        updated_by_key[
            make_key(row)
        ] = output_row

        print(
            "SEMANTIC STATUS:",
            semantic_result[
                "semantic_status"
            ],
        )

        print(
            "SEMANTIC SUPPORT:",
            semantic_result[
                "semantic_supported"
            ],
        )

        print(
            "LATENCY MS:",
            semantic_result[
                "semantic_latency_ms"
            ],
        )

        if semantic_result[
            "semantic_reason"
        ]:
            print(
                "REASON:",
                semantic_result[
                    "semantic_reason"
                ],
            )

        if semantic_result[
            "semantic_error_code"
        ]:
            print(
                "ERROR:",
                semantic_result[
                    "semantic_error_code"
                ],
                semantic_result[
                    "semantic_error_message"
                ],
            )

        ordered_partial = [
            updated_by_key[
                make_key(manifest_row)
            ]
            for manifest_row
            in manifest_rows
            if make_key(
                manifest_row
            )
            in updated_by_key
        ]

        write_results(
            ordered_partial
        )

    final_rows = [
        updated_by_key[
            make_key(row)
        ]
        for row in manifest_rows
        if make_key(row)
        in updated_by_key
    ]

    write_results(
        final_rows
    )

    success = sum(
        row.get(
            "semantic_status",
            ""
        )
        == "success"
        for row in final_rows
    )

    failed = sum(
        row.get(
            "semantic_status",
            ""
        )
        == "failed"
        for row in final_rows
    )

    print()
    print("=" * 80)
    print("AUTOACCEPTED REVIEW SUMMARY")
    print("=" * 80)

    print(
        "success=",
        success,
    )

    print(
        "failed=",
        failed,
    )

    print(
        "total=",
        len(final_rows),
    )

    print()
    print(
        "Output:",
        OUTPUT_RESULTS,
    )


if __name__ == "__main__":
    main()