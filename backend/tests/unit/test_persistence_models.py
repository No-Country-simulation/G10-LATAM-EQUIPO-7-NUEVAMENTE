"""Pruebas unitarias de conversión de modelos de persistencia."""

import json
from datetime import UTC, datetime

import pytest

from app.infrastructure.persistence.models import (
    GeneratedFormatRecord,
)


def test_generated_format_record_rejects_invalid_chunk_item() -> None:
    """La persistencia no debe descartar evidencias inválidas."""
    timestamp = datetime(
        2026,
        10,
        1,
        12,
        0,
        tzinfo=UTC,
    ).isoformat()

    content = {
        "title": "Quiz de prueba",
        "instructions": "Seleccione la respuesta correcta.",
        "questions": [
            {
                "question_id": "q_1",
                "question": "¿Qué componente coordina el producto?",
                "options": [
                    "BackendAPI",
                    "Frontend",
                ],
                "correct_answer": "BackendAPI",
                "explanation": (
                    "BackendAPI coordina las integraciones."
                ),
            }
        ],
    }

    chunks_used = [
        {
            "chunk_id": "chunk_1",
            "document_id": "doc_123",
            "rank": 1,
            "score": 0.93,
            "text": "Texto utilizado como evidencia.",
        },
        "chunk_invalido",
    ]

    record = GeneratedFormatRecord(
        format_id="fmt_123",
        document_id="doc_123",
        format_type="quiz",
        status="success",
        content_json=json.dumps(
            content
        ),
        chunks_used_json=json.dumps(
            chunks_used
        ),
        profile="beginner",
        niche="technology",
        detail_level="detailed",
        learning_objective=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
    )

    with pytest.raises(
        ValueError,
        match=(
            r"chunks_used_json\[1\] "
            r"debe representar un objeto"
        ),
    ):
        record.to_domain()