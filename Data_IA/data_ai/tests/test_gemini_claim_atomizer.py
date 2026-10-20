from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from data_ai.evaluation.claim_atomizer import (
    ClaimAtomizationOutput,
    GeneratedAtom,
)
from data_ai.evaluation.gemini_claim_atomizer import (
    GeminiClaimAtomizer,
    PROMPT_VERSION,
)


def test_requires_api_key():
    with pytest.raises(
        ValueError,
        match="DATA_IA_GEMINI_API_KEY",
    ):
        GeminiClaimAtomizer(
            api_key="",
            model="test-model",
        )


def test_requires_model():
    with pytest.raises(
        ValueError,
        match="DATA_IA_GEMINI_MODEL",
    ):
        GeminiClaimAtomizer(
            api_key="test-key",
            model="",
        )


def test_exposes_model():
    provider = GeminiClaimAtomizer(
        api_key="test-key",
        model="test-model",
    )

    assert provider.model == "test-model"


def test_exposes_prompt_version():
    provider = GeminiClaimAtomizer(
        api_key="test-key",
        model="test-model",
    )

    assert (
        provider.prompt_version
        == PROMPT_VERSION
    )


def test_atomize_uses_structured_parsed_output():
    provider = GeminiClaimAtomizer(
        api_key="test-key",
        model="test-model",
    )

    expected = ClaimAtomizationOutput(
        atomization_class="atomic",
        atoms=[
            GeneratedAtom(
                text=(
                    "Crear solicitudes eficaces para LLM."
                ),
                atom_type="factual_proposition",
            )
        ],
    )

    fake_response = MagicMock()
    fake_response.parsed = expected

    provider._client = MagicMock()

    provider._client.models.generate_content.return_value = (
        fake_response
    )

    result = provider.atomize(
        source_claim_id="claim-1",
        claim_text=(
            "Crear solicitudes eficaces para LLM."
        ),
        format="tldr",
    )

    assert result == expected


def test_atomize_parses_json_fallback():
    provider = GeminiClaimAtomizer(
        api_key="test-key",
        model="test-model",
    )

    fake_response = MagicMock()
    fake_response.parsed = None
    fake_response.text = """
    {
      "atomization_class": "relational",
      "atoms": [
        {
          "text": "La serie enseña conceptos básicos de la nube.",
          "atom_type": "factual_proposition"
        },
        {
          "text": "La enseñanza ocurre antes del contexto referido.",
          "atom_type": "temporal_relation"
        }
      ]
    }
    """

    provider._client = MagicMock()

    provider._client.models.generate_content.return_value = (
        fake_response
    )

    result = provider.atomize(
        source_claim_id="claim-2",
        claim_text=(
            "Antes de eso, la serie enseña "
            "conceptos básicos de la nube."
        ),
        format="video_script",
    )

    assert (
        result.atomization_class
        == "relational"
    )

    assert len(result.atoms) == 2

    assert (
        result.atoms[1].atom_type
        == "temporal_relation"
    )


def test_atomize_rejects_empty_response():
    provider = GeminiClaimAtomizer(
        api_key="test-key",
        model="test-model",
    )

    fake_response = MagicMock()
    fake_response.parsed = None
    fake_response.text = ""

    provider._client = MagicMock()

    provider._client.models.generate_content.return_value = (
        fake_response
    )

    with pytest.raises(
        RuntimeError,
        match="empty atomization response",
    ):
        provider.atomize(
            source_claim_id="claim-3",
            claim_text="Texto de prueba.",
            format="tldr",
        )