from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from data_ai.evaluation.claim_atomizer import (
    ClaimAtomizationOutput,
    GeneratedAtom,
)
from data_ai.evaluation.gemini_claim_atomizer_v0_2 import (
    GeminiClaimAtomizerV02,
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
        GeminiClaimAtomizerV02(
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
        GeminiClaimAtomizerV02(
            api_key="test-key",
            model="",
        )


def test_prompt_version_is_v0_2():
    provider = GeminiClaimAtomizerV02(
        api_key="test-key",
        model="test-model",
    )

    assert (
        provider.prompt_version
        == "claim-atomizer-v0.2"
    )

    assert (
        provider.prompt_version
        == PROMPT_VERSION
    )


def test_exposes_model():
    provider = GeminiClaimAtomizerV02(
        api_key="test-key",
        model="test-model",
    )

    assert provider.model == "test-model"


def test_accepts_atomic_structured_output():
    provider = GeminiClaimAtomizerV02(
        api_key="test-key",
        model="test-model",
    )

    expected = ClaimAtomizationOutput(
        atomization_class="atomic",
        atoms=[
            GeneratedAtom(
                text=(
                    "Kubernetes cifra automáticamente "
                    "todo el tráfico del clúster por defecto."
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
            "Kubernetes cifra automáticamente "
            "todo el tráfico del clúster por defecto."
        ),
        format="flashcards",
    )

    assert result == expected


def test_accepts_relational_structured_output():
    provider = GeminiClaimAtomizerV02(
        api_key="test-key",
        model="test-model",
    )

    expected = ClaimAtomizationOutput(
        atomization_class="relational",
        atoms=[
            GeneratedAtom(
                text=(
                    "La serie enseña conceptos básicos de la nube."
                ),
                atom_type="factual_proposition",
            ),
            GeneratedAtom(
                text=(
                    "La enseñanza de conceptos básicos de la nube "
                    "ocurre antes del evento o contexto referido."
                ),
                atom_type="temporal_relation",
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
        source_claim_id="claim-2",
        claim_text=(
            "Antes de eso, la serie enseña "
            "conceptos básicos de la nube."
        ),
        format="video_script",
    )

    assert result == expected
    assert len(result.atoms) == 2


def test_rejects_empty_response():
    provider = GeminiClaimAtomizerV02(
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