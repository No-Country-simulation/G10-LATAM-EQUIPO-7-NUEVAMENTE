"""Diagnóstico experimental de content_support por oración.

Este script NO modifica el evaluador productivo.

Objetivo:
- comparar el comportamiento léxico global actual;
- evaluar cada oración factual de forma independiente;
- identificar posibles falsos positivos y falsos negativos;
- generar evidencia para una futura versión de content_support.

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

from pydantic import TypeAdapter

from data_ai.evaluation.config import (
    RATIO_ALUCINACION_RECHAZO,
    RATIO_ALUCINACION_EXCELENTE,
    RATIO_ALUCINACION_BUENO,
)
from data_ai.evaluation.quality_evaluator import (
    _extraer_texto_factual,
    _palabras_significativas,
)
from data_ai.schemas.format_evaluation import (
    EvaluationRequest,
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


def split_claims(text: str) -> list[str]:
    """Separa texto factual en oraciones/unidades simples."""

    parts = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def calculate_ratio(
    text: str,
    source_terms: set[str],
) -> tuple[
    list[str],
    list[str],
    float,
]:
    """Calcula términos respaldados y no respaldados."""

    generated_terms = _palabras_significativas(
        text
    )

    if not generated_terms:
        return [], [], 0.0

    unsupported = [
        term
        for term in generated_terms
        if term not in source_terms
    ]

    supported = [
        term
        for term in generated_terms
        if term in source_terms
    ]

    ratio = (
        len(unsupported)
        / len(generated_terms)
    )

    return (
        supported,
        unsupported,
        ratio,
    )


def classify_ratio(
    ratio: float,
) -> tuple[int, bool]:
    """Replica los umbrales heurísticos actuales."""

    if (
        ratio
        >= RATIO_ALUCINACION_RECHAZO
    ):
        return 1, True

    if (
        ratio
        <= RATIO_ALUCINACION_EXCELENTE
    ):
        return 5, False

    if (
        ratio
        <= RATIO_ALUCINACION_BUENO
    ):
        return 4, False

    return 3, False


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

        factual_text = (
            _extraer_texto_factual(
                request.generated_content
            )
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

        (
            global_supported,
            global_unsupported,
            global_ratio,
        ) = calculate_ratio(
            factual_text,
            source_terms,
        )

        (
            global_score,
            global_flag,
        ) = classify_ratio(
            global_ratio
        )

        print()
        print("=" * 70)
        print(case_id)
        print("=" * 70)

        print()
        print("GLOBAL")
        print(
            "ratio=",
            round(global_ratio, 4),
        )
        print(
            "content_support=",
            global_score,
        )
        print(
            "unsupported_flag=",
            global_flag,
        )

        print(
            "unsupported_terms=",
            global_unsupported,
        )

        claims = split_claims(
            factual_text
        )

        print()
        print(
            "CLAIMS:",
            len(claims),
        )

        for index, claim in enumerate(
            claims,
            start=1,
        ):
            (
                supported,
                unsupported,
                ratio,
            ) = calculate_ratio(
                claim,
                source_terms,
            )

            (
                score,
                unsupported_flag,
            ) = classify_ratio(
                ratio
            )

            print()
            print(
                f"[Claim {index}]"
            )
            print(claim)

            print(
                "ratio=",
                round(ratio, 4),
            )

            print(
                "content_support=",
                score,
            )

            print(
                "unsupported_flag=",
                unsupported_flag,
            )

            print(
                "supported_terms=",
                supported,
            )

            print(
                "unsupported_terms=",
                unsupported,
            )


if __name__ == "__main__":
    main()