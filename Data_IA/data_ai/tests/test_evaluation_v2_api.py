"""Tests del endpoint público Evaluation V2."""

from fastapi.testclient import TestClient

from data_ai.api.app import app

client = TestClient(app)


def _payload() -> dict:
    return {
        "document_id": "doc_123",
        "format": "tldr",
        "generated_content": {
            "title": "Arquitectura backend",
            "summary": (
                "Una arquitectura backend organiza "
                "servicios y lógica de negocio."
            ),
            "key_points": [
                "Organiza servicios.",
                "Separa responsabilidades.",
            ],
            "conclusion": (
                "La separación de responsabilidades "
                "facilita el mantenimiento."
            ),
        },
        "generation_context": {
            "profile": "intermediate",
            "niche": "backend",
            "detail_level": "medium",
            "learning_objective": (
                "Comprender arquitectura backend."
            ),
        },
        "chunks_used": [
            {
                "chunk_id": "chunk_1",
                "document_id": "doc_123",
                "rank": 1,
                "score": 1.0,
                "text": (
                    "Una arquitectura backend organiza "
                    "servicios, lógica de negocio y "
                    "responsabilidades."
                ),
            }
        ],
    }


def test_evaluate_v2_returns_successful_http_response():
    response = client.post(
        "/evaluate/v2",
        json=_payload(),
    )

    assert response.status_code == 200


def test_evaluate_v2_returns_v2_contract():
    response = client.post(
        "/evaluate/v2",
        json=_payload(),
    )

    body = response.json()

    assert body["document_id"] == "doc_123"
    assert body["format"] == "tldr"

    assert body["verdict"] in {
        "approved",
        "requires_revision",
        "rejected",
    }

    assert body["heuristic_scores"] is not None

    assert "semantic_evaluation" in body
    assert "evaluator_version" in body
    assert "rubric_version" in body


def test_evaluate_v2_semantic_is_unavailable_without_provider():
    response = client.post(
        "/evaluate/v2",
        json=_payload(),
    )

    body = response.json()

    semantic = body["semantic_evaluation"]

    assert semantic["status"] == "unavailable"
    assert semantic["scores"] is None
    assert semantic["error_code"] == "not_configured"


def test_evaluate_v2_keeps_heuristic_scores_when_semantic_unavailable():
    response = client.post(
        "/evaluate/v2",
        json=_payload(),
    )

    body = response.json()

    scores = body["heuristic_scores"]

    assert scores is not None

    assert 1.0 <= scores["relevance"] <= 5.0
    assert 1.0 <= scores["coherence"] <= 5.0

    assert (
        1.0
        <= scores["didactic_adaptation"]
        <= 5.0
    )

    assert (
        1.0
        <= scores["content_support"]
        <= 5.0
    )


def test_evaluate_v2_does_not_expose_combined_score():
    response = client.post(
        "/evaluate/v2",
        json=_payload(),
    )

    body = response.json()

    assert "final_score" not in body
    assert "combined_score" not in body
    assert "weighted_score" not in body


def test_evaluate_v1_remains_available():
    response = client.post(
        "/evaluate",
        json=_payload(),
    )

    assert response.status_code == 200

    body = response.json()

    assert "status" in body
    assert "scores" in body

    assert "heuristic_scores" not in body
    assert "semantic_evaluation" not in body
    
def test_evaluate_v2_uses_unavailable_fallback_without_env(
    monkeypatch,
):
    monkeypatch.delenv(
        "DATA_IA_GEMINI_API_KEY",
        raising=False,
    )
    monkeypatch.delenv(
        "DATA_IA_GEMINI_MODEL",
        raising=False,
    )

    response = client.post(
        "/evaluate/v2",
        json=_payload(),
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["semantic_evaluation"]["status"]
        == "unavailable"
    )

    assert (
        body["semantic_evaluation"]["error_code"]
        == "not_configured"
    )


def test_evaluate_v2_uses_provider_factory(
    monkeypatch,
):
    from data_ai.api import app as app_module

    class FakeProvider:
        provider_name = "fake"
        model_name = "fake-model"

        def generate_structured(
            self,
            *,
            system_prompt,
            user_prompt,
        ):
            return {
                "scores": {
                    "relevance": 4.5,
                    "coherence": 4.5,
                    "didactic_adaptation": 4.0,
                    "content_support": 4.5,
                },
                "observations": [],
                "recommendations": [],
                "unsupported_information": [],
            }

    monkeypatch.setattr(
        app_module,
        "build_semantic_provider",
        lambda: FakeProvider(),
    )

    response = client.post(
        "/evaluate/v2",
        json=_payload(),
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["semantic_evaluation"]["status"]
        == "success"
    )

    assert (
        body["semantic_evaluation"]["model"]
        == "fake-model"
    )

    assert (
        body["semantic_evaluation"]["scores"]
        is not None
    )