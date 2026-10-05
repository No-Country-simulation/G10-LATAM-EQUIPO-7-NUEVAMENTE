from data_ai.validators.retrieval_validator import (
    validate_retrieval_contract,
)


def make_success_payload():
    return {
        "contract_version": "1.0",
        "case_id": "AI-ES-001-Q01",
        "query": "¿Qué es inteligencia artificial?",
        "top_k": 5,
        "score_type": "cosine_similarity",
        "status": "success",
        "results": [
            {
                "rank": 1,
                "chunk_id": "AI-ES-001_CH_001",
                "document_id": "AI-ES-001",
                "score": 0.91,
                "text": "Contenido relevante sobre inteligencia artificial.",
                "metadata": {},
            }
        ],
        "error": None,
    }


def test_success_payload_is_valid():
    payload = make_success_payload()

    errors = validate_retrieval_contract(payload)

    assert errors == []


def test_no_results_payload_is_valid():
    payload = {
        "contract_version": "1.0",
        "case_id": "AI-ES-001-Q02",
        "query": "Pregunta sin resultados",
        "top_k": 5,
        "score_type": "cosine_similarity",
        "status": "no_results",
        "results": [],
        "error": None,
    }

    errors = validate_retrieval_contract(payload)

    assert errors == []


def test_error_payload_is_valid():
    payload = {
        "contract_version": "1.0",
        "case_id": "AI-ES-001-Q03",
        "query": "Pregunta con error técnico",
        "top_k": 5,
        "score_type": "cosine_similarity",
        "status": "error",
        "results": [],
        "error": {
            "code": "RETRIEVAL_ERROR",
            "message": "No fue posible ejecutar retrieval.",
        },
    }

    errors = validate_retrieval_contract(payload)

    assert errors == []


def test_success_requires_results():
    payload = make_success_payload()
    payload["results"] = []

    errors = validate_retrieval_contract(payload)

    assert errors
    assert any(
        "requiere al menos un resultado" in error
        for error in errors
    )


def test_error_requires_error_object():
    payload = {
        "contract_version": "1.0",
        "case_id": "AI-ES-001-Q04",
        "query": "Pregunta con error",
        "top_k": 5,
        "score_type": "cosine_similarity",
        "status": "error",
        "results": [],
        "error": None,
    }

    errors = validate_retrieval_contract(payload)

    assert errors
    assert any(
        "requiere un objeto error" in error
        for error in errors
    )


def test_top_k_must_be_five():
    payload = make_success_payload()
    payload["top_k"] = 3

    errors = validate_retrieval_contract(payload)

    assert errors


def test_rank_must_follow_position():
    payload = make_success_payload()
    payload["results"][0]["rank"] = 2

    errors = validate_retrieval_contract(payload)

    assert errors


def test_required_contract_field_is_missing():
    payload = make_success_payload()
    payload.pop("error")

    errors = validate_retrieval_contract(payload)

    assert errors
