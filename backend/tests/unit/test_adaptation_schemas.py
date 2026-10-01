"""Pruebas del contrato HTTP de adaptación educativa."""

import pytest
from pydantic import ValidationError

from app.schemas.adaptation import (
    AdaptationRequest,
)


def test_adaptation_request_accepts_supported_contract() -> None:
    """Acepta el contexto pedagógico acordado para Sprint 2."""
    request = AdaptationRequest(
        document_id="doc_123",
        profile="intermediate",
        niche="general",
        detail_level="detailed",
        learning_objective=(
            "Comprender los conceptos principales."
        ),
    )

    assert request.document_id == "doc_123"
    assert request.profile == "intermediate"
    assert request.niche == "general"
    assert request.detail_level == "detailed"
    assert request.learning_objective == (
        "Comprender los conceptos principales."
    )


def test_adaptation_request_allows_missing_learning_objective() -> None:
    """El objetivo de aprendizaje es opcional."""
    request = AdaptationRequest(
        document_id="doc_123",
        profile="beginner",
        niche="backend",
        detail_level="basic",
    )

    assert request.learning_objective is None


def test_adaptation_request_strips_surrounding_whitespace() -> None:
    """Normaliza los campos textuales libres."""
    request = AdaptationRequest(
        document_id="  doc_123  ",
        profile="advanced",
        niche="business",
        detail_level="  detailed  ",
        learning_objective="  Analizar casos reales.  ",
    )

    assert request.document_id == "doc_123"
    assert request.detail_level == "detailed"
    assert request.learning_objective == (
        "Analizar casos reales."
    )


@pytest.mark.parametrize(
    "profile",
    [
        "Principiante",
        "expert",
        "",
    ],
)
def test_adaptation_request_rejects_unsupported_profile(
    profile: str,
) -> None:
    """El perfil debe usar los valores acordados con Frontend."""
    with pytest.raises(
        ValidationError
    ):
        AdaptationRequest(
            document_id="doc_123",
            profile=profile,
            niche="general",
            detail_level="detailed",
        )


@pytest.mark.parametrize(
    "niche",
    [
        "General",
        "education",
        "",
    ],
)
def test_adaptation_request_rejects_unsupported_niche(
    niche: str,
) -> None:
    """El nicho debe usar los valores acordados con Frontend."""
    with pytest.raises(
        ValidationError
    ):
        AdaptationRequest(
            document_id="doc_123",
            profile="intermediate",
            niche=niche,
            detail_level="detailed",
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "document_id",
        "detail_level",
        "learning_objective",
    ],
)
def test_adaptation_request_rejects_blank_text_fields(
    field_name: str,
) -> None:
    """Los campos textuales presentes no pueden contener solo espacios."""
    payload = {
        "document_id": "doc_123",
        "profile": "intermediate",
        "niche": "general",
        "detail_level": "detailed",
        "learning_objective": "Comprender el documento.",
    }

    payload[field_name] = "   "

    with pytest.raises(
        ValidationError
    ):
        AdaptationRequest(
            **payload
        )


def test_adaptation_request_rejects_output_format() -> None:
    """La selección de formatos no pertenece al contrato de adaptación."""
    with pytest.raises(
        ValidationError
    ):
        AdaptationRequest(
            document_id="doc_123",
            profile="intermediate",
            niche="general",
            detail_level="detailed",
            output_format="all",
        )


def test_adaptation_request_rejects_unknown_fields() -> None:
    """Campos fuera del contrato no deben ignorarse silenciosamente."""
    with pytest.raises(
        ValidationError
    ):
        AdaptationRequest(
            document_id="doc_123",
            profile="intermediate",
            niche="general",
            detail_level="detailed",
            unsupported_parameter="value",
        )