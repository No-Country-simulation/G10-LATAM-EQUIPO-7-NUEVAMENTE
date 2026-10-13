"""Tests para la abstracción del proveedor semántico.

Estos tests validan:
- que SemanticProvider funciona como interfaz abstracta;
- que una implementación concreta mínima puede usarse correctamente;
- que los errores normalizados conservan contexto útil;
- que la representación textual de los errores es estable.
"""

from typing import Any

import pytest

from data_ai.evaluation.semantic_provider import (
    SemanticProvider,
    SemanticProviderError,
    SemanticProviderExecutionError,
    SemanticProviderNotConfiguredError,
    SemanticProviderTimeoutError,
)


class FakeSemanticProvider(SemanticProvider):
    """Proveedor fake mínimo para probar la interfaz."""

    def __init__(
        self,
        *,
        response: dict[str, Any] | None = None,
        provider_name: str = "fake",
        model_name: str | None = "fake-model",
    ) -> None:
        self._response = response or {
            "scores": {
                "relevance": 4.5,
                "coherence": 4.2,
                "didactic_adaptation": 3.8,
                "content_support": 4.1,
            }
        }
        self._provider_name = provider_name
        self._model_name = model_name

        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str | None:
        return self._model_name

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt

        return self._response


# ============================================================
# SemanticProvider
# ============================================================


def test_semantic_provider_is_abstract():
    with pytest.raises(TypeError):
        SemanticProvider()


def test_fake_provider_exposes_provider_name():
    provider = FakeSemanticProvider()

    assert provider.provider_name == "fake"


def test_fake_provider_exposes_model_name():
    provider = FakeSemanticProvider(
        model_name="fake-semantic-v1",
    )

    assert provider.model_name == "fake-semantic-v1"


def test_fake_provider_allows_model_name_none():
    provider = FakeSemanticProvider(
        model_name=None,
    )

    assert provider.model_name is None


def test_generate_structured_returns_configured_response():
    expected = {
        "scores": {
            "relevance": 5.0,
            "coherence": 4.5,
            "didactic_adaptation": 4.0,
            "content_support": 4.8,
        },
        "observations": [],
        "recommendations": [],
        "unsupported_information": [],
    }

    provider = FakeSemanticProvider(
        response=expected,
    )

    result = provider.generate_structured(
        system_prompt="System instructions",
        user_prompt="User evaluation payload",
    )

    assert result == expected


def test_generate_structured_receives_prompts():
    provider = FakeSemanticProvider()

    provider.generate_structured(
        system_prompt="SYSTEM PROMPT",
        user_prompt="USER PROMPT",
    )

    assert provider.last_system_prompt == "SYSTEM PROMPT"
    assert provider.last_user_prompt == "USER PROMPT"


# ============================================================
# SemanticProviderError
# ============================================================


def test_semantic_provider_error_preserves_message():
    error = SemanticProviderError(
        "Provider failed.",
    )

    assert error.message == "Provider failed."
    assert error.provider is None
    assert error.model is None


def test_semantic_provider_error_preserves_context():
    error = SemanticProviderError(
        "Provider failed.",
        provider="gemini",
        model="gemini-test-model",
    )

    assert error.message == "Provider failed."
    assert error.provider == "gemini"
    assert error.model == "gemini-test-model"


def test_semantic_provider_error_string_without_context():
    error = SemanticProviderError(
        "Provider failed.",
    )

    assert str(error) == "Provider failed."


def test_semantic_provider_error_string_with_provider_only():
    error = SemanticProviderError(
        "Provider failed.",
        provider="gemini",
    )

    assert str(error) == (
        "Provider failed. (provider=gemini)"
    )


def test_semantic_provider_error_string_with_model_only():
    error = SemanticProviderError(
        "Provider failed.",
        model="gemini-test-model",
    )

    assert str(error) == (
        "Provider failed. (model=gemini-test-model)"
    )


def test_semantic_provider_error_string_with_full_context():
    error = SemanticProviderError(
        "Provider failed.",
        provider="gemini",
        model="gemini-test-model",
    )

    assert str(error) == (
        "Provider failed. "
        "(provider=gemini, model=gemini-test-model)"
    )


# ============================================================
# Specific error classes
# ============================================================


@pytest.mark.parametrize(
    "error_class",
    [
        SemanticProviderNotConfiguredError,
        SemanticProviderTimeoutError,
        SemanticProviderExecutionError,
    ],
)
def test_specific_provider_errors_inherit_base_error(
    error_class,
):
    error = error_class(
        "Test error.",
        provider="fake",
        model="fake-model",
    )

    assert isinstance(
        error,
        SemanticProviderError,
    )

    assert error.message == "Test error."
    assert error.provider == "fake"
    assert error.model == "fake-model"


def test_not_configured_error_can_be_raised_and_caught():
    with pytest.raises(
        SemanticProviderNotConfiguredError,
    ) as exc_info:
        raise SemanticProviderNotConfiguredError(
            "Semantic provider is not configured.",
            provider="gemini",
        )

    assert (
        exc_info.value.message
        == "Semantic provider is not configured."
    )


def test_timeout_error_can_be_raised_and_caught():
    with pytest.raises(
        SemanticProviderTimeoutError,
    ) as exc_info:
        raise SemanticProviderTimeoutError(
            "Semantic provider timed out.",
            provider="gemini",
            model="gemini-test-model",
        )

    assert (
        exc_info.value.message
        == "Semantic provider timed out."
    )


def test_execution_error_can_be_raised_and_caught():
    with pytest.raises(
        SemanticProviderExecutionError,
    ) as exc_info:
        raise SemanticProviderExecutionError(
            "Unexpected provider error.",
            provider="gemini",
            model="gemini-test-model",
        )

    assert (
        exc_info.value.message
        == "Unexpected provider error."
    )