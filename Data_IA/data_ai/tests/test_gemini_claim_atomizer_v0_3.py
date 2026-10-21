from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from data_ai.evaluation.claim_atomizer import (
    ClaimAtomizationOutput,
    GeneratedAtom,
)
from data_ai.evaluation.gemini_claim_atomizer_v0_3 import (
    GeminiClaimAtomizerV03,
    PROMPT_VERSION,
)


def test_requires_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        "DATA_IA_GEMINI_API_KEY",
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="DATA_IA_GEMINI_API_KEY",
    ):
        GeminiClaimAtomizerV03(
            api_key="",
            model="test-model",
        )


def test_requires_model(
    monkeypatch,
):
    monkeypatch.delenv(
        "DATA_IA_GEMINI_MODEL",
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="DATA_IA_GEMINI_MODEL",
    ):
        GeminiClaimAtomizerV03(
            api_key="test-key",
            model="",
        )


def test_prompt_version():
    provider = GeminiClaimAtomizerV03(
        api_key="test-key",
        model="test-model",
    )

    assert (
        provider.prompt_version
        == "claim-atomizer-v0.3"
    )

    assert (
        provider.prompt_version
        == PROMPT_VERSION
    )


def test_exposes_model():
    provider = GeminiClaimAtomizerV03(
        api_key="test-key",
        model="test-model",
    )

    assert provider.model == "test-model"


def test_accepts_compound_output():
    provider = GeminiClaimAtomizerV03(
        api_key="test-key",
        model="test-model",
    )

    expected = ClaimAtomizationOutput(
        atomization_class="compound",
        atoms=[
            GeneratedAtom(
                text=(
                    "La herramienta es de código abierto."
                ),
                atom_type="factual_proposition",
            ),
            GeneratedAtom(
                text=(
                    "La herramienta permite ejecutar "
                    "modelos localmente."
                ),
                atom_type="factual_proposition",
            ),
        ],
    )

    fake_response = MagicMock()
    fake_response.parsed = expected

    provider._client = MagicMock()

    provider._client.models.generate_content.return_value = (
        fake_response
    )

    result = provider.atomize(
        source_claim_id="synthetic-1",
        claim_text=(
            "La herramienta es de código abierto "
            "y permite ejecutar modelos localmente."
        ),
        format="tldr",
    )

    assert result == expected


def test_accepts_single_atom_relational_output():
    provider = GeminiClaimAtomizerV03(
        api_key="test-key",
        model="test-model",
    )

    expected = ClaimAtomizationOutput(
        atomization_class="relational",
        atoms=[
            GeneratedAtom(
                text=(
                    "El modelo A supera al modelo B en precisión."
                ),
                atom_type="comparative_relation",
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
        source_claim_id="synthetic-2",
        claim_text=(
            "El modelo A supera al modelo B en precisión."
        ),
        format="tldr",
    )

    assert (
        result.atomization_class
        == "relational"
    )

    assert len(result.atoms) == 1


def test_rejects_empty_response():
    provider = GeminiClaimAtomizerV03(
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
            source_claim_id="synthetic-3",
            claim_text="Texto sintético.",
            format="quiz",
        )