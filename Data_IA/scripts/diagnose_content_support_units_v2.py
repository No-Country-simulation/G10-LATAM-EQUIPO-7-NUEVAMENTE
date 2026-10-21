"""Diagnóstico experimental de content_support por unidades estructurales.

Este script NO modifica el evaluador productivo.

Objetivo:
- evaluar contenido factual por unidad estructural real;
- evitar segmentación posterior sobre texto aplanado;
- comparar el comportamiento léxico del heurístico;
- detectar falsos positivos y falsos negativos;
- generar evidencia para una futura mejora de content_support.

Unidades por formato:
- quiz:
  - question
  - correct_answer
  - explanation
- flashcards:
  - front
  - back
- tldr:
  - summary
  - cada key_point
  - conclusion
- video_script:
  - narration de cada escena

Casos iniciales:
- CAL-OCI-001
- CAL-V1-005
- CAL-V1-013
- CAL-V1-014
"""

from __future__ import annotations

import json
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


def classify_ratio(
    ratio: float,
) -> tuple[int, bool]:
    """Replica los umbrales heurísticos actuales."""

    if ratio >= RATIO_ALUCINACION_RECHAZO:
        return 1, True

    if ratio <= RATIO_ALUCINACION_EXCELENTE:
        return 5, False

    if ratio <= RATIO_ALUCINACION_BUENO:
        return 4, False

    return 3, False


def calculate_ratio(
    text: str,
    source_terms: set[str],
) -> dict[str, Any]:
    """Calcula soporte léxico para una unidad."""

    generated_terms = (
        _palabras_significativas(text)
    )

    if not generated_terms:
        return {
            "text": text,
            "generated_terms": [],
            "supported_terms": [],
            "unsupported_terms": [],
            "ratio": 0.0,
            "content_support": 5,
            "unsupported_flag": False,
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

    ratio = (
        len(unsupported_terms)
        / len(generated_terms)
    )

    (
        content_support,
        unsupported_flag,
    ) = classify_ratio(
        ratio
    )

    return {
        "text": text,
        "generated_terms": generated_terms,
        "supported_terms": supported_terms,
        "unsupported_terms": unsupported_terms,
        "ratio": ratio,
        "content_support": content_support,
        "unsupported_flag": unsupported_flag,
    }


def extract_units(
    request: EvaluationRequest,
) -> list[dict[str, str]]:
    """Extrae unidades estructurales reales según el formato."""

    content = request.generated_content

    units: list[dict[str, str]] = []

    if isinstance(content, QuizContent):
        for index, question in enumerate(
            content.questions,
            start=1,
        ):
            units.append(
                {
                    "unit_id": (
                        f"question_{index}_prompt"
                    ),
                    "unit_type": "question",
                    "text": question.question,
                }
            )

            units.append(
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
                }
            )

            units.append(
                {
                    "unit_id": (
                        f"question_{index}_explanation"
                    ),
                    "unit_type": "explanation",
                    "text": (
                        question.explanation
                    ),
                }
            )

        return units

    if isinstance(content, FlashcardsContent):
        for index, card in enumerate(
            content.cards,
            start=1,
        ):
            units.append(
                {
                    "unit_id": (
                        f"card_{index}_front"
                    ),
                    "unit_type": "front",
                    "text": card.front,
                }
            )

            units.append(
                {
                    "unit_id": (
                        f"card_{index}_back"
                    ),
                    "unit_type": "back",
                    "text": card.back,
                }
            )

        return units

    if isinstance(content, TLDRContent):
        units.append(
            {
                "unit_id": "summary",
                "unit_type": "summary",
                "text": content.summary,
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
                }
            )

        units.append(
            {
                "unit_id": "conclusion",
                "unit_type": "conclusion",
                "text": content.conclusion,
            }
        )

        return units

    if isinstance(content, VideoScriptContent):
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
                }
            )

        return units

    raise TypeError(
        f"Unsupported content type: "
        f"{type(content).__name__}"
    )


def summarize_case(
    unit_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resume comportamiento por caso."""

    unsupported_units = [
        item
        for item in unit_results
        if item["unsupported_flag"]
    ]

    critical_units = [
        item
        for item in unit_results
        if item["content_support"] == 1
    ]

    ratios = [
        item["ratio"]
        for item in unit_results
    ]

    average_ratio = (
        sum(ratios) / len(ratios)
        if ratios
        else 0.0
    )

    max_ratio = (
        max(ratios)
        if ratios
        else 0.0
    )

    return {
        "total_units": len(
            unit_results
        ),
        "unsupported_units": len(
            unsupported_units
        ),
        "critical_units": len(
            critical_units
        ),
        "average_ratio": average_ratio,
        "max_ratio": max_ratio,
    }


def main() -> None:
    adapter = TypeAdapter(
        EvaluationRequest
    )

    for case_id in CASE_IDS:
        path = (
            CASES_DIR
            / f"{case_id}.json"
        )

        data = json.loads(
            path.read_text(
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

        units = extract_units(
            request
        )

        unit_results: list[
            dict[str, Any]
        ] = []

        print()
        print("=" * 80)
        print(case_id)
        print("=" * 80)

        print()
        print(
            "FORMAT:",
            request.format,
        )

        print()
        print(
            "SOURCE TERMS:",
            sorted(source_terms),
        )

        for unit in units:
            result = calculate_ratio(
                unit["text"],
                source_terms,
            )

            combined = {
                **unit,
                **result,
            }

            unit_results.append(
                combined
            )

            print()
            print("-" * 60)

            print(
                "UNIT:",
                unit["unit_id"],
            )

            print(
                "TYPE:",
                unit["unit_type"],
            )

            print(
                "TEXT:"
            )
            print(
                unit["text"]
            )

            print(
                "generated_terms=",
                result["generated_terms"],
            )

            print(
                "supported_terms=",
                result["supported_terms"],
            )

            print(
                "unsupported_terms=",
                result[
                    "unsupported_terms"
                ],
            )

            print(
                "ratio=",
                round(
                    result["ratio"],
                    4,
                ),
            )

            print(
                "content_support=",
                result[
                    "content_support"
                ],
            )

            print(
                "unsupported_flag=",
                result[
                    "unsupported_flag"
                ],
            )

        summary = summarize_case(
            unit_results
        )

        print()
        print("=" * 60)
        print("CASE SUMMARY")
        print("=" * 60)

        print(
            "total_units=",
            summary["total_units"],
        )

        print(
            "unsupported_units=",
            summary[
                "unsupported_units"
            ],
        )

        print(
            "critical_units=",
            summary[
                "critical_units"
            ],
        )

        print(
            "average_ratio=",
            round(
                summary[
                    "average_ratio"
                ],
                4,
            ),
        )

        print(
            "max_ratio=",
            round(
                summary[
                    "max_ratio"
                ],
                4,
            ),
        )


if __name__ == "__main__":
    main()