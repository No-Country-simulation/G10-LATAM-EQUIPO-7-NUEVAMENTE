"""Experimento de normalización lingüística para content_support_v2.

Este script NO modifica el evaluador productivo.

Objetivo:
- comparar el matching léxico actual contra una variante normalizada;
- aplicar normalización morfológica ligera;
- eliminar algunos conectores discursivos de poco valor factual;
- evitar que repeticiones de una misma forma inflen el análisis;
- mantener separados legacy_ratio y normalized_ratio;
- decidir si la normalización reduce falsos positivos
  sin ocultar unsupported claims reales.

NO:
- modifica quality_evaluator.py;
- modifica los umbrales productivos;
- llama a Gemini;
- calcula un nuevo verdict.

Casos iniciales:
- CAL-OCI-001
- CAL-V1-005
- CAL-V1-013
- CAL-V1-014
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from data_ai.evaluation.config import (
    RATIO_ALUCINACION_RECHAZO,
    RATIO_ALUCINACION_EXCELENTE,
    RATIO_ALUCINACION_BUENO,
)
from data_ai.evaluation.quality_evaluator import (
    _palabras_significativas,
)
from data_ai.schemas.format_evaluation import (
    EvaluationRequest,
)

from scripts.experiment_content_support_v2 import (
    CASE_IDS,
    CASES_DIR,
    RESULTS_DIR,
    extract_structural_units,
    expand_unit_into_claims,
)


OUTPUT_CSV = (
    RESULTS_DIR
    / "content_support_normalization_v1.csv"
)

SUMMARY_CSV = (
    RESULTS_DIR
    / "content_support_normalization_v1_summary.csv"
)


# ============================================================
# CONFIGURACIÓN EXPERIMENTAL
# ============================================================

# Términos discursivos que por sí solos no expresan
# una afirmación factual nueva.
#
# Esta lista se mantiene intencionalmente pequeña para
# evitar sobreajuste a los casos de calibración.
EXPERIMENTAL_NEUTRAL_TERMS = {
    "ademas",
    "mediante",
}


# ============================================================
# NORMALIZACIÓN
# ============================================================


def remove_accents(
    text: str,
) -> str:
    """Elimina marcas diacríticas."""

    return "".join(
        char
        for char in unicodedata.normalize(
            "NFD",
            text,
        )
        if unicodedata.category(char)
        != "Mn"
    )


def basic_tokenize(
    text: str,
) -> list[str]:
    """Tokenización simple para diagnóstico."""

    normalized = remove_accents(
        text.lower()
    )

    return re.findall(
        r"\b\w+\b",
        normalized,
        flags=re.UNICODE,
    )


def normalize_spanish_morphology(
    token: str,
) -> str:
    """Normalización morfológica ligera y conservadora.

    No pretende ser un lematizador completo.

    Solo intenta acercar formas flexionadas evidentes
    que actualmente producen diferencias superficiales.

    Ejemplos esperados:

    aparezca / aparezcan
        -> aparezc

    actue / actuen
        -> actu

    visita / visitamos
        -> visit

    importa / importada
        -> import
    """

    token = remove_accents(
        token.lower()
    )

    # ----------------------------
    # Formas participiales comunes
    # ----------------------------

    participle_suffixes = (
        "adas",
        "ados",
        "idos",
        "idas",
        "ada",
        "ado",
        "ida",
        "ido",
    )

    for suffix in participle_suffixes:
        if (
            token.endswith(suffix)
            and len(token) > len(suffix) + 3
        ):
            return token[
                : -len(suffix)
            ]

    # ----------------------------
    # Subjuntivo/plural:
    # aparezcan -> aparezc
    # actuen -> actu
    # ----------------------------

    for suffix in (
        "an",
        "en",
    ):
        if (
            token.endswith(suffix)
            and len(token) > 5
        ):
            candidate = token[
                : -len(suffix)
            ]

            if len(candidate) >= 4:
                return candidate

    # ----------------------------
    # Primera persona plural:
    # visitamos -> visit
    # ----------------------------

    if (
        token.endswith("amos")
        and len(token) > 7
    ):
        return token[:-4]

    if (
        token.endswith("emos")
        and len(token) > 7
    ):
        return token[:-4]

    if (
        token.endswith("imos")
        and len(token) > 7
    ):
        return token[:-4]

    # ----------------------------
    # Infinitivos
    # ----------------------------

    for suffix in (
        "ar",
        "er",
        "ir",
    ):
        if (
            token.endswith(suffix)
            and len(token) > 5
        ):
            return token[
                : -len(suffix)
            ]

    # ----------------------------
    # Plurales nominales simples
    # ----------------------------

    if (
        token.endswith("es")
        and len(token) > 6
    ):
        return token[:-2]

    if (
        token.endswith("s")
        and len(token) > 5
    ):
        return token[:-1]

    # ----------------------------
    # Vocal final verbal simple
    # importa -> import
    # visita -> visit
    # ----------------------------

    if (
        token.endswith(
            (
                "a",
                "e",
            )
        )
        and len(token) > 5
    ):
        return token[:-1]

    return token


def normalize_terms(
    terms: list[str],
) -> list[str]:
    """Normaliza y deduplica términos preservando orden."""

    normalized: list[str] = []

    seen: set[str] = set()

    for term in terms:
        clean = remove_accents(
            term.lower()
        )

        if clean in EXPERIMENTAL_NEUTRAL_TERMS:
            continue

        normalized_term = (
            normalize_spanish_morphology(
                clean
            )
        )

        if not normalized_term:
            continue

        if normalized_term in seen:
            continue

        seen.add(
            normalized_term
        )

        normalized.append(
            normalized_term
        )

    return normalized


# ============================================================
# CLASIFICACIÓN
# ============================================================


def classify_ratio(
    ratio: float,
) -> tuple[int, bool, str]:
    """Usa los mismos umbrales que el heurístico actual."""

    if ratio >= RATIO_ALUCINACION_RECHAZO:
        return (
            1,
            True,
            "critical_lexical",
        )

    if ratio <= RATIO_ALUCINACION_EXCELENTE:
        return (
            5,
            False,
            "supported",
        )

    if ratio <= RATIO_ALUCINACION_BUENO:
        return (
            4,
            False,
            "mostly_supported",
        )

    return (
        3,
        False,
        "lexically_suspicious",
    )


# ============================================================
# LEGACY
# ============================================================


def calculate_legacy(
    text: str,
    source_terms: set[str],
) -> dict[str, Any]:
    """Replica comparación léxica actual."""

    generated_terms = (
        _palabras_significativas(
            text
        )
    )

    unsupported = [
        term
        for term in generated_terms
        if term not in source_terms
    ]

    ratio = (
        len(unsupported)
        / len(generated_terms)
        if generated_terms
        else 0.0
    )

    (
        score,
        flag,
        status,
    ) = classify_ratio(
        ratio
    )

    return {
        "legacy_generated_terms": (
            generated_terms
        ),
        "legacy_unsupported_terms": (
            unsupported
        ),
        "legacy_ratio": ratio,
        "legacy_score": score,
        "legacy_flag": flag,
        "legacy_status": status,
    }


# ============================================================
# NORMALIZED
# ============================================================


def calculate_normalized(
    text: str,
    source_terms: list[str],
) -> dict[str, Any]:
    """Calcula ratio usando términos normalizados."""

    generated_raw = (
        _palabras_significativas(
            text
        )
    )

    generated_terms = (
        normalize_terms(
            generated_raw
        )
    )

    normalized_source = set(
        normalize_terms(
            source_terms
        )
    )

    supported = [
        term
        for term in generated_terms
        if term in normalized_source
    ]

    unsupported = [
        term
        for term in generated_terms
        if term not in normalized_source
    ]

    ratio = (
        len(unsupported)
        / len(generated_terms)
        if generated_terms
        else 0.0
    )

    (
        score,
        flag,
        status,
    ) = classify_ratio(
        ratio
    )

    return {
        "normalized_generated_terms": (
            generated_terms
        ),
        "normalized_supported_terms": (
            supported
        ),
        "normalized_unsupported_terms": (
            unsupported
        ),
        "normalized_ratio": ratio,
        "normalized_score": score,
        "normalized_flag": flag,
        "normalized_status": status,
    }


# ============================================================
# ROUTING
# ============================================================


def requires_review(
    factual_role: str,
    status: str,
) -> bool:
    """Decide si un claim debería escalar a semántica."""

    if (
        factual_role
        != "factual_content"
    ):
        return False

    return status in {
        "lexically_suspicious",
        "critical_lexical",
    }


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    adapter = TypeAdapter(
        EvaluationRequest
    )

    all_rows: list[
        dict[str, Any]
    ] = []

    summary_rows: list[
        dict[str, Any]
    ] = []

    for case_id in CASE_IDS:
        case_path = (
            CASES_DIR
            / f"{case_id}.json"
        )

        data = json.loads(
            case_path.read_text(
                encoding="utf-8"
            )
        )

        request = adapter.validate_python(
            data["evaluation_request"]
        )

        chunks_text = " ".join(
            chunk.text
            for chunk in request.chunks_used
        )

        source_terms_list = (
            _palabras_significativas(
                chunks_text
            )
        )

        source_terms_set = set(
            source_terms_list
        )

        units = extract_structural_units(
            request
        )

        case_rows: list[
            dict[str, Any]
        ] = []

        for unit in units:
            claims = expand_unit_into_claims(
                unit
            )

            for claim in claims:
                legacy = calculate_legacy(
                    claim["claim_text"],
                    source_terms_set,
                )

                normalized = (
                    calculate_normalized(
                        claim[
                            "claim_text"
                        ],
                        source_terms_list,
                    )
                )

                legacy_review = (
                    requires_review(
                        claim[
                            "factual_role"
                        ],
                        legacy[
                            "legacy_status"
                        ],
                    )
                )

                normalized_review = (
                    requires_review(
                        claim[
                            "factual_role"
                        ],
                        normalized[
                            "normalized_status"
                        ],
                    )
                )

                result = {
                    "calibration_id": (
                        case_id
                    ),
                    "format": (
                        request.format
                    ),
                    "unit_id": (
                        claim["unit_id"]
                    ),
                    "unit_type": (
                        claim["unit_type"]
                    ),
                    "factual_role": (
                        claim[
                            "factual_role"
                        ]
                    ),
                    "claim_id": (
                        claim["claim_id"]
                    ),
                    "claim_text": (
                        claim["claim_text"]
                    ),
                    **legacy,
                    **normalized,
                    "legacy_needs_review": (
                        legacy_review
                    ),
                    "normalized_needs_review": (
                        normalized_review
                    ),
                }

                case_rows.append(
                    result
                )

                all_rows.append(
                    result
                )

        factual_rows = [
            row
            for row in case_rows
            if row["factual_role"]
            == "factual_content"
        ]

        legacy_review_claims = [
            row
            for row in factual_rows
            if row[
                "legacy_needs_review"
            ]
        ]

        normalized_review_claims = [
            row
            for row in factual_rows
            if row[
                "normalized_needs_review"
            ]
        ]

        summary = {
            "calibration_id": (
                case_id
            ),
            "format": (
                request.format
            ),
            "factual_claims": len(
                factual_rows
            ),
            "legacy_review_claims": len(
                legacy_review_claims
            ),
            "normalized_review_claims": len(
                normalized_review_claims
            ),
            "legacy_case_review": bool(
                legacy_review_claims
            ),
            "normalized_case_review": bool(
                normalized_review_claims
            ),
        }

        summary_rows.append(
            summary
        )

        print()
        print("=" * 90)
        print(case_id)
        print("=" * 90)

        for row in case_rows:
            print()
            print("-" * 70)

            print(
                "CLAIM_ID:",
                row["claim_id"],
            )

            print(
                "FACTUAL_ROLE:",
                row["factual_role"],
            )

            print(
                "TEXT:"
            )

            print(
                row["claim_text"]
            )

            print()

            print(
                "LEGACY ratio=",
                round(
                    row[
                        "legacy_ratio"
                    ],
                    4,
                ),
            )

            print(
                "LEGACY status=",
                row[
                    "legacy_status"
                ],
            )

            print(
                "LEGACY needs_review=",
                row[
                    "legacy_needs_review"
                ],
            )

            print(
                "LEGACY unsupported=",
                row[
                    "legacy_unsupported_terms"
                ],
            )

            print()

            print(
                "NORMALIZED ratio=",
                round(
                    row[
                        "normalized_ratio"
                    ],
                    4,
                ),
            )

            print(
                "NORMALIZED status=",
                row[
                    "normalized_status"
                ],
            )

            print(
                "NORMALIZED needs_review=",
                row[
                    "normalized_needs_review"
                ],
            )

            print(
                "NORMALIZED unsupported=",
                row[
                    "normalized_unsupported_terms"
                ],
            )

        print()
        print("=" * 70)
        print("CASE SUMMARY")
        print("=" * 70)

        print(
            "factual_claims=",
            summary[
                "factual_claims"
            ],
        )

        print(
            "legacy_review_claims=",
            summary[
                "legacy_review_claims"
            ],
        )

        print(
            "normalized_review_claims=",
            summary[
                "normalized_review_claims"
            ],
        )

        print(
            "legacy_case_review=",
            summary[
                "legacy_case_review"
            ],
        )

        print(
            "normalized_case_review=",
            summary[
                "normalized_case_review"
            ],
        )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    claim_fieldnames = [
        "calibration_id",
        "format",
        "unit_id",
        "unit_type",
        "factual_role",
        "claim_id",
        "claim_text",
        "legacy_ratio",
        "legacy_score",
        "legacy_flag",
        "legacy_status",
        "legacy_needs_review",
        "legacy_generated_terms",
        "legacy_unsupported_terms",
        "normalized_ratio",
        "normalized_score",
        "normalized_flag",
        "normalized_status",
        "normalized_needs_review",
        "normalized_generated_terms",
        "normalized_supported_terms",
        "normalized_unsupported_terms",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=claim_fieldnames,
        )

        writer.writeheader()

        for row in all_rows:
            export = {
                **row,
            }

            list_fields = [
                "legacy_generated_terms",
                "legacy_unsupported_terms",
                "normalized_generated_terms",
                "normalized_supported_terms",
                "normalized_unsupported_terms",
            ]

            for field in list_fields:
                export[field] = "|".join(
                    export[field]
                )

            writer.writerow(
                {
                    key: export[key]
                    for key in claim_fieldnames
                }
            )

    summary_fieldnames = [
        "calibration_id",
        "format",
        "factual_claims",
        "legacy_review_claims",
        "normalized_review_claims",
        "legacy_case_review",
        "normalized_case_review",
    ]

    with SUMMARY_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=summary_fieldnames,
        )

        writer.writeheader()

        for row in summary_rows:
            writer.writerow(
                row
            )

    print()
    print("=" * 90)
    print("RESULT FILES")
    print("=" * 90)

    print(
        OUTPUT_CSV
    )

    print(
        SUMMARY_CSV
    )


if __name__ == "__main__":
    main()