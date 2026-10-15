import csv
import json
import time
from pathlib import Path

from pydantic import TypeAdapter

from data_ai.schemas.format_evaluation import EvaluationRequest
from data_ai.evaluation.semantic_evaluator import SemanticEvaluator
from data_ai.evaluation.semantic_provider_factory import build_semantic_provider


CASE_IDS = [
    "CAL-V1-002",
    "CAL-V1-003",
    "CAL-V1-004",
    "CAL-V1-006",
    "CAL-V1-007",
    "CAL-V1-008",
    "CAL-V1-010",
    "CAL-V1-011",
    "CAL-V1-012",
    "CAL-V1-014",
    "CAL-V1-015",
    "CAL-V1-016",
    "CAL-V1-018",
    "CAL-V1-019",
    "CAL-V1-020",
]

MAX_ATTEMPTS = 3
RETRY_SECONDS = 2

CASES_DIR = Path(
    "data/evaluation/calibration_v1/cases"
)

RESULTS_DIR = Path(
    "data/evaluation/calibration_v1/results"
)

OUTPUT_PATH = (
    RESULTS_DIR /
    "semantic_perturbations_batch1.csv"
)


def main():
    adapter = TypeAdapter(EvaluationRequest)

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    evaluator = SemanticEvaluator(
        build_semantic_provider()
    )

    rows = []

    for case_id in CASE_IDS:
        path = CASES_DIR / f"{case_id}.json"

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        request = adapter.validate_python(
            data["evaluation_request"]
        )

        result = None
        attempts = 0

        for attempt in range(
            1,
            MAX_ATTEMPTS + 1
        ):
            attempts = attempt

            result = evaluator.evaluate(
                content_format=request.format,
                generated_content=(
                    request.generated_content
                ),
                chunks_used=request.chunks_used,
                generation_context=(
                    request.generation_context
                ),
            )

            if result.status == "success":
                break

            if result.error_code not in {
                "provider_error",
                "timeout",
            }:
                break

            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_SECONDS)

        scores = result.scores

        row = {
            "calibration_id":
                data["calibration_id"],

            "source_case_id":
                data["source_case_id"],

            "document_id":
                data["document_id"],

            "category":
                data["category"],

            "format":
                request.format,

            "variant":
                data["variant"],

            "target_dimension":
                data["target_dimension"],

            "semantic_status":
                result.status,

            "semantic_relevance":
                scores.relevance
                if scores else None,

            "semantic_coherence":
                scores.coherence
                if scores else None,

            "semantic_didactic_adaptation":
                scores.didactic_adaptation
                if scores else None,

            "semantic_content_support":
                scores.content_support
                if scores else None,

            "unsupported_information_count":
                len(
                    result.unsupported_information
                ),

            "observations_count":
                len(result.observations),

            "recommendations_count":
                len(result.recommendations),

            "error_code":
                result.error_code,

            "error_message":
                result.error_message,

            "attempts":
                attempts,

            "model":
                result.model,

            "prompt_version":
                result.prompt_version,

            "latency_ms_last_attempt":
                result.latency_ms,
        }

        rows.append(row)

        print(
            row["calibration_id"],
            "|",
            row["variant"],
            "| status=",
            row["semantic_status"],
            "| scores=",
            row["semantic_relevance"],
            row["semantic_coherence"],
            row["semantic_didactic_adaptation"],
            row["semantic_content_support"],
            "| unsupported=",
            row[
                "unsupported_information_count"
            ],
            "| attempts=",
            row["attempts"],
            "| error=",
            row["error_code"],
        )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys(),
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print(
        "Guardado en:",
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()