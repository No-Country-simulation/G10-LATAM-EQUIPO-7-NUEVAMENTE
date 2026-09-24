import pandas as pd

from data_ai.metrics.retrieval_evaluator import (
    evaluate_retrieval_case,
    evaluate_retrieval_batch,
)


def make_ground_truth():
    return pd.DataFrame(
        [
            {
                "case_id": "AI-ES-001-Q01",
                "categoria": "IA",
                "pregunta": "¿Qué es inteligencia artificial?",
                "relevant_chunk_ids_list": [
                    "AI-ES-001_CH_001",
                ],
            },
            {
                "case_id": "AI-ES-001-Q02",
                "categoria": "IA",
                "pregunta": "¿Qué es aprendizaje automático?",
                "relevant_chunk_ids_list": [
                    "AI-ES-001_CH_002",
                ],
            },
        ]
    )


def make_success_payload(case_id="AI-ES-001-Q01"):
    return {
        "contract_version": "1.0",
        "case_id": case_id,
        "query": "¿Qué es inteligencia artificial?",
        "top_k": 5,
        "score_type": "cosine_similarity",
        "status": "success",
        "results": [
            {
                "rank": 1,
                "chunk_id": "AI-ES-001_CH_001",
                "document_id": "AI-ES-001",
                "score": 0.95,
                "text": "Contenido relevante.",
                "metadata": {},
            }
        ],
        "error": None,
    }


def make_no_results_payload(case_id="AI-ES-001-Q02"):
    return {
        "contract_version": "1.0",
        "case_id": case_id,
        "query": "Pregunta sin resultados",
        "top_k": 5,
        "score_type": "cosine_similarity",
        "status": "no_results",
        "results": [],
        "error": None,
    }


def make_error_payload(case_id="AI-ES-001-Q02"):
    return {
        "contract_version": "1.0",
        "case_id": case_id,
        "query": "Pregunta con error",
        "top_k": 5,
        "score_type": "cosine_similarity",
        "status": "error",
        "results": [],
        "error": {
            "code": "RETRIEVAL_ERROR",
            "message": "Falló el retrieval.",
        },
    }


def test_evaluate_success_case():
    ground_truth = make_ground_truth()
    payload = make_success_payload()

    result = evaluate_retrieval_case(
        payload,
        ground_truth,
    )

    assert result["status"] == "success"
    assert result["metric_eligible"] is True
    assert result["recall_at_5"] == 1.0
    assert result["precision_at_5"] == 0.2


def test_evaluate_no_results_case():
    ground_truth = make_ground_truth()
    payload = make_no_results_payload()

    result = evaluate_retrieval_case(
        payload,
        ground_truth,
    )

    assert result["status"] == "no_results"
    assert result["metric_eligible"] is True
    assert result["retrieved_chunk_ids"] == []
    assert result["recall_at_5"] == 0.0
    assert result["precision_at_5"] == 0.0


def test_evaluate_error_case():
    ground_truth = make_ground_truth()
    payload = make_error_payload()

    result = evaluate_retrieval_case(
        payload,
        ground_truth,
    )

    assert result["status"] == "error"
    assert result["metric_eligible"] is False
    assert result["recall_at_5"] is None
    assert result["precision_at_5"] is None
    assert result["error_code"] == "RETRIEVAL_ERROR"


def test_batch_detects_missing_case():
    ground_truth = make_ground_truth()

    payloads = [
        make_success_payload(
            "AI-ES-001-Q01"
        )
    ]

    _, report = evaluate_retrieval_batch(
        payloads,
        ground_truth,
    )

    assert report["missing_case_ids"] == [
        "AI-ES-001-Q02"
    ]


def test_batch_detects_duplicate_case():
    ground_truth = make_ground_truth()

    payloads = [
        make_success_payload(
            "AI-ES-001-Q01"
        ),
        make_success_payload(
            "AI-ES-001-Q01"
        ),
    ]

    _, report = evaluate_retrieval_batch(
        payloads,
        ground_truth,
    )

    assert report["duplicated_case_ids"] == [
        "AI-ES-001-Q01"
    ]


def test_batch_detects_extra_case():
    ground_truth = make_ground_truth()

    payloads = [
        make_success_payload(
            "AI-ES-999-Q99"
        )
    ]

    _, report = evaluate_retrieval_batch(
        payloads,
        ground_truth,
    )

    assert report["extra_case_ids"] == [
        "AI-ES-999-Q99"
    ]
    assert report["batch_errors"]