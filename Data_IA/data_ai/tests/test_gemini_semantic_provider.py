"""Tests para GeminiSemanticProvider sin llamadas de red."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from data_ai.evaluation.gemini_semantic_provider import (
    GeminiSemanticOutput,
    GeminiSemanticProvider,
)
from data_ai.evaluation.semantic_provider import (
    SemanticProviderExecutionError,
    SemanticProviderNotConfiguredError,
    SemanticProviderTimeoutError,
)
from data_ai.schemas.semantic_evaluation import (
    SemanticScores,
)


def _valid_parsed_output() -> GeminiSemanticOutput:
    return GeminiSemanticOutput(
        scores=SemanticScores(
            relevance=4.5,
            coherence=4.0,
            didactic_adaptation=4.2,
            content_support=4.8,
        ),
        observations=[],
        recommendations=[],
        unsupported_information=[],
    )


def _client_with_response(
    response,
):
    client = Mock()

    client.models.generate_content.return_value = (
        response
    )

    return client


def test_provider_metadata():
    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=Mock(),
    )

    assert provider.provider_name == "gemini"
    assert provider.model_name == "gemini-test"


def test_missing_api_key_is_not_configured():
    provider = GeminiSemanticProvider(
        api_key=None,
        model="gemini-test",
    )

    with pytest.raises(
        SemanticProviderNotConfiguredError
    ):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )


def test_missing_model_is_not_configured():
    provider = GeminiSemanticProvider(
        api_key="test-key",
        model=None,
        client=Mock(),
    )

    with pytest.raises(
        SemanticProviderNotConfiguredError
    ):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )


def test_generate_structured_returns_parsed_payload():
    client = _client_with_response(
        SimpleNamespace(
            parsed=_valid_parsed_output(),
            text=None,
        )
    )

    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    result = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
    )

    assert result["scores"]["relevance"] == 4.5
    assert result["scores"]["content_support"] == 4.8

    assert result["observations"] == []
    assert result["recommendations"] == []
    assert result["unsupported_information"] == []


def test_provider_calls_requested_model_once():
    client = _client_with_response(
        SimpleNamespace(
            parsed=_valid_parsed_output(),
            text=None,
        )
    )

    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
    )

    client.models.generate_content.assert_called_once()

    call = (
        client.models.generate_content.call_args
    )

    assert (
        call.kwargs["model"]
        == "gemini-test"
    )

    assert (
        call.kwargs["contents"]
        == "user"
    )


def test_provider_can_parse_json_text_fallback():
    client = _client_with_response(
        SimpleNamespace(
            parsed=None,
            text="""
            {
              "scores": {
                "relevance": 5.0,
                "coherence": 4.0,
                "didactic_adaptation": 4.0,
                "content_support": 5.0
              },
              "observations": [],
              "recommendations": [],
              "unsupported_information": []
            }
            """,
        )
    )

    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    result = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
    )

    assert result["scores"]["relevance"] == 5.0
    assert result["scores"]["content_support"] == 5.0


def test_empty_response_becomes_execution_error():
    client = _client_with_response(
        SimpleNamespace(
            parsed=None,
            text="",
        )
    )

    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    with pytest.raises(
        SemanticProviderExecutionError
    ):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )


def test_invalid_json_becomes_execution_error():
    client = _client_with_response(
        SimpleNamespace(
            parsed=None,
            text="not-json",
        )
    )

    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    with pytest.raises(
        SemanticProviderExecutionError
    ):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )


def test_timeout_is_normalized():
    client = Mock()

    client.models.generate_content.side_effect = (
        TimeoutError("timeout")
    )

    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    with pytest.raises(
        SemanticProviderTimeoutError
    ):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )


def test_unexpected_exception_is_normalized():
    client = Mock()

    client.models.generate_content.side_effect = (
        RuntimeError("boom")
    )

    provider = GeminiSemanticProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    with pytest.raises(
        SemanticProviderExecutionError
    ):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
        )