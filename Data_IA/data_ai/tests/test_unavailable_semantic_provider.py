"""Tests para UnavailableSemanticProvider."""

import pytest

from data_ai.evaluation.semantic_provider import (
    SemanticProviderNotConfiguredError,
)
from data_ai.evaluation.unavailable_semantic_provider import (
    UnavailableSemanticProvider,
)


def test_provider_identifies_itself_as_unavailable():
    provider = UnavailableSemanticProvider()

    assert provider.provider_name == "unavailable"
    assert provider.model_name is None


def test_provider_never_returns_fake_semantic_output():
    provider = UnavailableSemanticProvider()

    with pytest.raises(
        SemanticProviderNotConfiguredError
    ):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )


def test_provider_error_contains_provider_context():
    provider = UnavailableSemanticProvider()

    with pytest.raises(
        SemanticProviderNotConfiguredError
    ) as exc_info:
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )

    assert (
        "unavailable"
        in str(exc_info.value)
    )