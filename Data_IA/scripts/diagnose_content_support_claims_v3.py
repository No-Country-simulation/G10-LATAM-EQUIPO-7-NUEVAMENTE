"""Diagnóstico jerárquico experimental de content_support.

Este script NO modifica el evaluador productivo.

Objetivo:
- preservar la estructura real de cada formato;
- separar unidades largas en oraciones/claims;
- analizar soporte léxico por claim;
- distinguir unidades pedagógicas de afirmaciones factuales;
- generar evidencia para un futuro content_support_v2.

Importante:
- no calcula un nuevo verdict;
- no reemplaza al evaluador heurístico;
- no reemplaza al evaluador semántico;
- usa exclusivamente chunks_used como fuente factual.

Casos iniciales:
- CAL-OCI-001
- CAL-V1-005
- CAL-V1-013
- CAL-V1-014
"""

from __future__ import annotations

import json
import re
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
    QuizContent,
    FlashcardsContent,
    TLDRContent,
    VideoScriptContent,
)


CASE_IDS = [
    "CAL-OCI-001",
    "CAL-V1-005",
    "CAL-V1-013",
    "CAL-V1-014",
]

CASES_DIR = Path(
    "data/evaluation/calibration_v1/cases"
)


# ============================================================
# CLASIFICACIÓN LÉXICA
# ============================================================


def classify_ratio(
    ratio: float,
) -> tuple[int, bool, str]:
    """Replica umbrales actuales y añade una etiqueta diagnóstica."""

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


def calculate_lexical_support(
    text: str,
    source_terms: set[str],
) -> dict[str, Any]:
    """Calcula soporte léxico para un claim individual."""

    generated_terms = (
        _palabras_significativas(
            text
        )
    )

    if not generated_terms:
        return {
            "generated_terms": [],
            "supported_terms": [],
            "unsupported_terms": [],
            "lexical_ratio": 0.0,
            "legacy_score": 5,
            "legacy_unsupported_flag": False,
            "diagnostic_status": "supported",
        }

    supported_terms = [
        term
        for term in generated_terms
        if term in source_terms
    ]

    unsupported_terms = [
        term
        for term in generated_terms
        if term not in source_terms
    ]

    lexical_ratio = (
        len(unsupported_terms)
        / len(generated_terms)
    )

    (
        legacy_score,
        legacy_flag,
        diagnostic_status,
    ) = classify_ratio(
        lexical_ratio
    )

    return {
        "generated_terms": generated_terms,
        "supported_terms": supported_terms,
        "unsupported_terms": unsupported_terms,
        "lexical_ratio": lexical_ratio,
        "legacy_score": legacy_score,
        "legacy_unsupported_flag": legacy_flag,
        "diagnostic_status": diagnostic_status,
    }


# ============================================================
# SEGMENTACIÓN
# ============================================================


def split_sentences(
    text: str,
) -> list[str]:
    """Divide una unidad larga en oraciones simples."""

    normalized = re.sub(
        r"\s+",
        " ",
        text.strip(),
    )

    if not normalized:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+",
        normalized,
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def should_split_unit(
    unit_type: str,
    text: str,
) -> bool:
    """Decide si una unidad debe dividirse en claims."""

    sentence_types = {
        "summary",
        "conclusion",
        "explanation",
        "narration",
        "back",
    }

    if unit_type not in sentence_types:
        return False

    return len(
        split_sentences(text)
    ) > 1


# ============================================================
# EXTRACCIÓN ESTRUCTURAL
# ============================================================


def extract_structural_units(
    request: EvaluationRequest,
) -> list[dict[str, Any]]:
    """Extrae unidades reales preservando su función pedagógica."""

    content = request.generated_content

    units: list[dict[str, Any]] = []

    if isinstance(
        content,
        QuizContent,
    ):
        for index, question in enumerate(
            content.questions,
            start=1,
        ):
            units.extend(
                [
                    {
                        "unit_id": (
                            f"question_{index}_prompt"
                        ),
                        "unit_type": "question",
                        "text": question.question,
                        "factual_role": (
                            "pedagogical_prompt"
                        ),
                    },
                    {
                        "unit_id": (
                            f"question_{index}_answer"
                        ),
                        "unit_type": (
                            "correct_answer"
                        ),
                        "text": (
                            question.correct_answer
                        ),
                        "factual_role": (
                            "factual_content"
                        ),
                    },
                    {
                        "unit_id": (
                            f"question_{index}_explanation"
                        ),
                        "unit_type": "explanation",
                        "text": (
                            question.explanation
                        ),
                        "factual_role": (
                            "factual_content"
                        ),
                    },
                ]
            )

        return units

    if isinstance(
        content,
        FlashcardsContent,
    ):
        for index, card in enumerate(
            content.cards,
            start=1,
        ):
            units.extend(
                [
                    {
                        "unit_id": (
                            f"card_{index}_front"
                        ),
                        "unit_type": "front",
                        "text": card.front,
                        "factual_role": (
                            "pedagogical_prompt"
                        ),
                    },
                    {
                        "unit_id": (
                            f"card_{index}_back"
                        ),
                        "unit_type": "back",
                        "text": card.back,
                        "factual_role": (
                            "factual_content"
                        ),
                    },
                ]
            )

        return units

    if isinstance(
        content,
        TLDRContent,
    ):
        units.append(
            {
                "unit_id": "summary",
                "unit_type": "summary",
                "text": content.summary,
                "factual_role": (
                    "factual_content"
                ),
            }
        )

        for index, key_point in enumerate(
            content.key_points,
            start=1,
        ):
            units.append(
                {
                    "unit_id": (
                        f"key_point_{index}"
                    ),
                    "unit_type": "key_point",
                    "text": key_point,
                    "factual_role": (
                        "factual_content"
                    ),
                }
            )

        units.append(
            {
                "unit_id": "conclusion",
                "unit_type": "conclusion",
                "text": content.conclusion,
                "factual_role": (
                    "factual_content"
                ),
            }
        )

        return units

    if isinstance(
        content,
        VideoScriptContent,
    ):
        for index, scene in enumerate(
            content.scenes,
            start=1,
        ):
            units.append(
                {
                    "unit_id": (
                        f"scene_{index}_narration"
                    ),
                    "unit_type": "narration",
                    "text": scene.narration,
                    "factual_role": (
                        "factual_content"
                    ),
                }
            )

        return units

    raise TypeError(
        "Unsupported generated_content type: "
        f"{type(content).__name__}"
    )


# ============================================================
# CLAIMS JERÁRQUICOS
# ============================================================


def expand_unit_into_claims(
    unit: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convierte una unidad estructural en uno o varios claims."""

    text = unit["text"]
    unit_type = unit["unit_type"]

    if not should_split_unit(
        unit_type,
        text,
    ):
        return [
            {
                **unit,
                "claim_id": (
                    f"{unit['unit_id']}_claim_1"
                ),
                "claim_index": 1,
                "claim_text": text,
            }
        ]

    sentences = split_sentences(
        text
    )

    return [
        {
            **unit,
            "claim_id": (
                f"{unit['unit_id']}_claim_{index}"
            ),
            "claim_index": index,
            "claim_text": sentence,
        }
        for index, sentence in enumerate(
            sentences,
            start=1,
        )
    ]


# ============================================================
# RESÚMENES
# ============================================================


def summarize_claims(
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resume resultados sin producir verdict."""

    factual_claims = [
        claim
        for claim in claims
        if claim["factual_role"]
        == "factual_content"
    ]

    pedagogical_claims = [
        claim
        for claim in claims
        if claim["factual_role"]
        == "pedagogical_prompt"
    ]

    critical_factual = [
        claim
        for claim in factual_claims
        if claim["diagnostic_status"]
        == "critical_lexical"
    ]

    suspicious_factual = [
        claim
        for claim in factual_claims
        if claim["diagnostic_status"]
        in {
            "critical_lexical",
            "lexically_suspicious",
        }
    ]

    ratios = [
        claim["lexical_ratio"]
        for claim in factual_claims
    ]

    return {
        "total_claims": len(
            claims
        ),
        "factual_claims": len(
            factual_claims
        ),
        "pedagogical_claims": len(
            pedagogical_claims
        ),
        "critical_factual_claims": len(
            critical_factual
        ),
        "suspicious_factual_claims": len(
            suspicious_factual
        ),
        "average_factual_ratio": (
            sum(ratios) / len(ratios)
            if ratios
            else 0.0
        ),
        "max_factual_ratio": (
            max(ratios)
            if ratios
            else 0.0
        ),
    }


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    adapter = TypeAdapter(
        EvaluationRequest
    )

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

        source_terms = set(
            _palabras_significativas(
                chunks_text
            )
        )

        structural_units = (
            extract_structural_units(
                request
            )
        )

        claims: list[
            dict[str, Any]
        ] = []

        for unit in structural_units:
            expanded = (
                expand_unit_into_claims(
                    unit
                )
            )

            for claim in expanded:
                lexical_result = (
                    calculate_lexical_support(
                        claim["claim_text"],
                        source_terms,
                    )
                )

                claims.append(
                    {
                        **claim,
                        **lexical_result,
                    }
                )

        print()
        print("=" * 90)
        print(case_id)
        print("=" * 90)

        print(
            "FORMAT:",
            request.format,
        )

        print(
            "STRUCTURAL_UNITS:",
            len(structural_units),
        )

        print(
            "CLAIMS:",
            len(claims),
        )

        for claim in claims:
            print()
            print("-" * 70)

            print(
                "UNIT:",
                claim["unit_id"],
            )

            print(
                "UNIT_TYPE:",
                claim["unit_type"],
            )

            print(
                "FACTUAL_ROLE:",
                claim["factual_role"],
            )

            print(
                "CLAIM_ID:",
                claim["claim_id"],
            )

            print(
                "TEXT:"
            )
            print(
                claim["claim_text"]
            )

            print(
                "generated_terms=",
                claim[
                    "generated_terms"
                ],
            )

            print(
                "supported_terms=",
                claim[
                    "supported_terms"
                ],
            )

            print(
                "unsupported_terms=",
                claim[
                    "unsupported_terms"
                ],
            )

            print(
                "lexical_ratio=",
                round(
                    claim[
                        "lexical_ratio"
                    ],
                    4,
                ),
            )

            print(
                "legacy_score=",
                claim[
                    "legacy_score"
                ],
            )

            print(
                "legacy_unsupported_flag=",
                claim[
                    "legacy_unsupported_flag"
                ],
            )

            print(
                "diagnostic_status=",
                claim[
                    "diagnostic_status"
                ],
            )

        summary = summarize_claims(
            claims
        )

        print()
        print("=" * 70)
        print("CASE DIAGNOSTIC SUMMARY")
        print("=" * 70)

        print(
            "total_claims=",
            summary[
                "total_claims"
            ],
        )

        print(
            "factual_claims=",
            summary[
                "factual_claims"
            ],
        )

        print(
            "pedagogical_claims=",
            summary[
                "pedagogical_claims"
            ],
        )

        print(
            "critical_factual_claims=",
            summary[
                "critical_factual_claims"
            ],
        )

        print(
            "suspicious_factual_claims=",
            summary[
                "suspicious_factual_claims"
            ],
        )

        print(
            "average_factual_ratio=",
            round(
                summary[
                    "average_factual_ratio"
                ],
                4,
            ),
        )

        print(
            "max_factual_ratio=",
            round(
                summary[
                    "max_factual_ratio"
                ],
                4,
            ),
        )


if __name__ == "__main__":
    main()