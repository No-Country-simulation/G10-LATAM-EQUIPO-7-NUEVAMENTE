import json

import pytest

from data_ai.loaders.retrieval_loader import (
    load_retrieval_batch,
)


def test_load_valid_batch(tmp_path):
    file_path = tmp_path / "retrieval.json"

    payloads = [
        {
            "contract_version": "1.0",
            "case_id": "AI-ES-001-Q01",
            "query": "Pregunta",
            "top_k": 5,
            "score_type": "cosine_similarity",
            "status": "no_results",
            "results": [],
            "error": None,
        }
    ]

    file_path.write_text(
        json.dumps(payloads),
        encoding="utf-8",
    )

    result = load_retrieval_batch(file_path)

    assert result == payloads


def test_loader_rejects_non_list_json(tmp_path):
    file_path = tmp_path / "retrieval.json"

    file_path.write_text(
        json.dumps(
            {
                "case_id": "AI-ES-001-Q01"
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="debe contener una lista de payloads",
    ):
        load_retrieval_batch(file_path)


def test_loader_missing_file(tmp_path):
    file_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_retrieval_batch(file_path)