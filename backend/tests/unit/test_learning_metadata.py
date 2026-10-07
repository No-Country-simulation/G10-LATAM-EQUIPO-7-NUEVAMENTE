"""Pruebas del value object LearningMetadata."""

import pytest

from app.domain.learning_metadata import LearningMetadata


def test_learning_metadata_serializes_to_json_compatible_dict() -> None:
    """Conserva tipos y nombres del contrato acordado con Agentes."""
    metadata = LearningMetadata(
        key_concepts=(
            "RAG",
            "Embeddings",
        ),
        prerequisites=(
            "Fundamentos de Python",
        ),
        estimated_time_minutes=20,
    )

    assert metadata.to_dict() == {
        "key_concepts": [
            "RAG",
            "Embeddings",
        ],
        "prerequisites": [
            "Fundamentos de Python",
        ],
        "estimated_time_minutes": 20,
    }


def test_learning_metadata_builds_official_empty_fallback() -> None:
    """Representa el fallback de Agentes sin usar nulls internos."""
    metadata = LearningMetadata.empty()

    assert metadata.key_concepts == ()
    assert metadata.prerequisites == ()
    assert (
        metadata.estimated_time_minutes
        == 0
    )


def test_learning_metadata_rejects_negative_estimated_time() -> None:
    """Evita persistir tiempos de estudio negativos."""
    with pytest.raises(
        ValueError,
        match="mayor o igual a cero",
    ):
        LearningMetadata(
            key_concepts=(),
            prerequisites=(),
            estimated_time_minutes=-1,
        )
