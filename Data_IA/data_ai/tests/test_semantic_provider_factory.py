"""Tests para semantic_provider_factory."""

from data_ai.evaluation.gemini_semantic_provider import (
    GeminiSemanticProvider,
)
from data_ai.evaluation.semantic_provider_factory import (
    DATA_IA_GEMINI_API_KEY_ENV,
    DATA_IA_GEMINI_MODEL_ENV,
    build_semantic_provider,
)
from data_ai.evaluation.unavailable_semantic_provider import (
    UnavailableSemanticProvider,
)


def test_factory_returns_unavailable_when_api_key_missing(
    monkeypatch,
):
    monkeypatch.delenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        raising=False,
    )

    monkeypatch.setenv(
        DATA_IA_GEMINI_MODEL_ENV,
        "gemini-test",
    )

    provider = build_semantic_provider()

    assert isinstance(
        provider,
        UnavailableSemanticProvider,
    )


def test_factory_returns_unavailable_when_model_missing(
    monkeypatch,
):
    monkeypatch.setenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        "test-key",
    )

    monkeypatch.delenv(
        DATA_IA_GEMINI_MODEL_ENV,
        raising=False,
    )

    provider = build_semantic_provider()

    assert isinstance(
        provider,
        UnavailableSemanticProvider,
    )


def test_factory_returns_unavailable_when_both_missing(
    monkeypatch,
):
    monkeypatch.delenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        raising=False,
    )

    monkeypatch.delenv(
        DATA_IA_GEMINI_MODEL_ENV,
        raising=False,
    )

    provider = build_semantic_provider()

    assert isinstance(
        provider,
        UnavailableSemanticProvider,
    )


def test_factory_returns_gemini_when_configured(
    monkeypatch,
):
    monkeypatch.setenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        "test-key",
    )

    monkeypatch.setenv(
        DATA_IA_GEMINI_MODEL_ENV,
        "gemini-test",
    )

    provider = build_semantic_provider()

    assert isinstance(
        provider,
        GeminiSemanticProvider,
    )

    assert provider.provider_name == "gemini"
    assert provider.model_name == "gemini-test"


def test_factory_strips_environment_values(
    monkeypatch,
):
    monkeypatch.setenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        "  test-key  ",
    )

    monkeypatch.setenv(
        DATA_IA_GEMINI_MODEL_ENV,
        "  gemini-test  ",
    )

    provider = build_semantic_provider()

    assert isinstance(
        provider,
        GeminiSemanticProvider,
    )

    assert provider.model_name == "gemini-test"


def test_factory_treats_blank_api_key_as_missing(
    monkeypatch,
):
    monkeypatch.setenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        "   ",
    )

    monkeypatch.setenv(
        DATA_IA_GEMINI_MODEL_ENV,
        "gemini-test",
    )

    provider = build_semantic_provider()

    assert isinstance(
        provider,
        UnavailableSemanticProvider,
    )


def test_factory_treats_blank_model_as_missing(
    monkeypatch,
):
    monkeypatch.setenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        "test-key",
    )

    monkeypatch.setenv(
        DATA_IA_GEMINI_MODEL_ENV,
        "   ",
    )

    provider = build_semantic_provider()

    assert isinstance(
        provider,
        UnavailableSemanticProvider,
    )