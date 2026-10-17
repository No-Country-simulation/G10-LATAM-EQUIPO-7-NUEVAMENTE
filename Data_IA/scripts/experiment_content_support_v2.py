"""Prototipo experimental de content_support_v2.

Este script NO modifica el evaluador productivo.

Objetivo:
- preservar estructura por formato;
- separar contenido factual en claims;
- excluir prompts pedagógicos del soporte factual;
- aplicar filtro léxico por claim;
- decidir qué claims necesitan revisión semántica;
- generar un resumen por caso;
- NO llamar todavía a Gemini;
- NO calcular verdict de producción.

Flujo experimental:

pedagogical_prompt
    -> excluded_from_factual_support

factual_content
    -> lexical analysis

supported / mostly_supported
    -> provisionally_supported

lexically_suspicious / critical_lexical
    -> needs_semantic_review = True

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

RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

OUTPUT_CSV = (
    RESULTS_DIR
    / "content_support_v2_experiment_batch1.csv"
)

SUMMARY_CSV = (
    RESULTS_DIR
    / "content_support_v2_experiment_summary_batch1.csv"
)


# ============================================================
# LÉXICO
# ============================================================


def classify_ratio(
    ratio: float,
) -> tuple[int, bool, str]:
    """Replica umbrales actuales con etiqueta diagnóstica."""

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
    """Calcula soporte léxico para un claim."""

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
            "lexical_status": "supported",
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
        lexical_status,
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
        "lexical_status": lexical_status,
    }


# ============================================================
# SEGMENTACIÓN
# ============================================================


def split_sentences(
    text: str,
) -> list[str]:
    """Divide texto largo en oraciones."""

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
    """Determina qué tipos pueden contener múltiples claims."""

    splittable_types = {
        "summary",
        "conclusion",
        "explanation",
        "narration",
        "back",
    }

    if unit_type not in splittable_types:
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
    """Extrae unidades preservando su función."""

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
# CLAIMS
# ============================================================


def expand_unit_into_claims(
    unit: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convierte una unidad en uno o varios claims."""

    if not should_split_unit(
        unit["unit_type"],
        unit["text"],
    ):
        return [
            {
                **unit,
                "claim_id": (
                    f"{unit['unit_id']}_claim_1"
                ),
                "claim_index": 1,
                "claim_text": unit["text"],
            }
        ]

    sentences = split_sentences(
        unit["text"]
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
# DECISIÓN EXPERIMENTAL
# ============================================================


def determine_experimental_action(
    factual_role: str,
    lexical_status: str,
) -> dict[str, Any]:
    """Define el siguiente paso del pipeline experimental.

    Esta función NO decide soporte factual definitivo.
    """

    if factual_role == "pedagogical_prompt":
        return {
            "needs_semantic_review": False,
            "experimental_status": (
                "excluded_pedagogical_prompt"
            ),
        }

    if lexical_status in {
        "supported",
        "mostly_supported",
    }:
        return {
            "needs_semantic_review": False,
            "experimental_status": (
                "provisionally_supported"
            ),
        }

    if lexical_status in {
        "lexically_suspicious",
        "critical_lexical",
    }:
        return {
            "needs_semantic_review": True,
            "experimental_status": (
                "pending_semantic_review"
            ),
        }

    raise ValueError(
        f"Unexpected lexical status: "
        f"{lexical_status}"
    )


# ============================================================
# RESUMEN
# ============================================================


def summarize_case(
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resume el resultado experimental por caso."""

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

    provisional_supported = [
        claim
        for claim in factual_claims
        if claim["experimental_status"]
        == "provisionally_supported"
    ]

    pending_semantic = [
        claim
        for claim in factual_claims
        if claim["needs_semantic_review"]
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
        "provisionally_supported_claims": len(
            provisional_supported
        ),
        "semantic_review_claims": len(
            pending_semantic
        ),
        "semantic_review_rate": (
            len(pending_semantic)
            / len(factual_claims)
            if factual_claims
            else 0.0
        ),
    }


# ============================================================
# CSV
# ============================================================


def write_claim_results(
    rows: list[dict[str, Any]],
) -> None:
    """Guarda resultados por claim."""

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "calibration_id",
        "format",
        "unit_id",
        "unit_type",
        "factual_role",
        "claim_id",
        "claim_text",
        "generated_terms",
        "supported_terms",
        "unsupported_terms",
        "lexical_ratio",
        "legacy_score",
        "legacy_unsupported_flag",
        "lexical_status",
        "needs_semantic_review",
        "experimental_status",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            export_row = {
                **row,
                "generated_terms": "|".join(
                    row["generated_terms"]
                ),
                "supported_terms": "|".join(
                    row["supported_terms"]
                ),
                "unsupported_terms": "|".join(
                    row["unsupported_terms"]
                ),
            }

            writer.writerow(
                {
                    key: export_row[key]
                    for key in fieldnames
                }
            )


def write_summary_results(
    rows: list[dict[str, Any]],
) -> None:
    """Guarda resumen por caso."""

    fieldnames = [
        "calibration_id",
        "format",
        "total_claims",
        "factual_claims",
        "pedagogical_claims",
        "provisionally_supported_claims",
        "semantic_review_claims",
        "semantic_review_rate",
    ]

    with SUMMARY_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    key: row[key]
                    for key in fieldnames
                }
            )


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    adapter = TypeAdapter(
        EvaluationRequest
    )

    all_claim_rows: list[
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

        source_terms = set(
            _palabras_significativas(
                chunks_text
            )
        )

        units = extract_structural_units(
            request
        )

        case_claims: list[
            dict[str, Any]
        ] = []

        for unit in units:
            claims = expand_unit_into_claims(
                unit
            )

            for claim in claims:
                lexical_result = (
                    calculate_lexical_support(
                        claim["claim_text"],
                        source_terms,
                    )
                )

                action = (
                    determine_experimental_action(
                        claim["factual_role"],
                        lexical_result[
                            "lexical_status"
                        ],
                    )
                )

                result = {
                    "calibration_id": case_id,
                    "format": request.format,
                    **claim,
                    **lexical_result,
                    **action,
                }

                case_claims.append(
                    result
                )

                all_claim_rows.append(
                    result
                )

        summary = summarize_case(
            case_claims
        )

        summary_row = {
            "calibration_id": case_id,
            "format": request.format,
            **summary,
        }

        summary_rows.append(
            summary_row
        )

        print()
        print("=" * 90)
        print(case_id)
        print("=" * 90)

        for claim in case_claims:
            print()
            print("-" * 70)

            print(
                "CLAIM_ID:",
                claim["claim_id"],
            )

            print(
                "FACTUAL_ROLE:",
                claim["factual_role"],
            )

            print(
                "TEXT:"
            )

            print(
                claim["claim_text"]
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
                "lexical_status=",
                claim[
                    "lexical_status"
                ],
            )

            print(
                "needs_semantic_review=",
                claim[
                    "needs_semantic_review"
                ],
            )

            print(
                "experimental_status=",
                claim[
                    "experimental_status"
                ],
            )

        print()
        print("=" * 70)
        print("EXPERIMENT SUMMARY")
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
            "provisionally_supported_claims=",
            summary[
                "provisionally_supported_claims"
            ],
        )

        print(
            "semantic_review_claims=",
            summary[
                "semantic_review_claims"
            ],
        )

        print(
            "semantic_review_rate=",
            round(
                summary[
                    "semantic_review_rate"
                ],
                4,
            ),
        )

    write_claim_results(
        all_claim_rows
    )

    write_summary_results(
        summary_rows
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