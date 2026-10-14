"""Adapter Gemini para SemanticEvaluator.

Este módulo implementa SemanticProvider utilizando el SDK oficial
google-genai.

Responsabilidades:
- ejecutar Gemini con structured output;
- devolver un dict compatible con SemanticEvaluator;
- normalizar errores del SDK.

Este módulo NO:
- construye la rúbrica;
- decide verdict;
- combina scores;
- aplica retries;
- lee variables de entorno;
- conoce FastAPI.
"""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from data_ai.evaluation.semantic_provider import (
    SemanticProvider,
    SemanticProviderExecutionError,
    SemanticProviderNotConfiguredError,
    SemanticProviderTimeoutError,
)
from data_ai.schemas.semantic_evaluation import (
    SemanticObservation,
    SemanticRecommendation,
    SemanticScores,
    UnsupportedClaim,
)


class GeminiSemanticOutput(BaseModel):
    """Structured output esperado del LLM-as-a-Judge."""

    scores: SemanticScores
    observations: list[SemanticObservation] = Field(
        default_factory=list
    )
    recommendations: list[SemanticRecommendation] = Field(
        default_factory=list
    )
    unsupported_information: list[UnsupportedClaim] = Field(
        default_factory=list
    )


class GeminiSemanticProvider(SemanticProvider):
    """SemanticProvider respaldado por Gemini."""

    provider_name_value = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None,
        client: Any | None = None,
        temperature: float = 0.0,
    ) -> None:
        self._api_key = (
            api_key.strip()
            if api_key
            else ""
        )

        self._model = (
            model.strip()
            if model
            else ""
        )

        self._temperature = temperature

        if client is not None:
            self._client = client
        elif self._api_key:
            self._client = genai.Client(
                api_key=self._api_key
            )
        else:
            self._client = None

    @property
    def provider_name(self) -> str:
        return self.provider_name_value

    @property
    def model_name(self) -> str | None:
        return self._model or None

    def _validate_configuration(self) -> None:
        """Valida configuración mínima antes de invocar Gemini."""

        if not self._api_key:
            raise SemanticProviderNotConfiguredError(
                "DATA_IA_GEMINI_API_KEY is not configured.",
                provider=self.provider_name,
                model=self.model_name,
            )

        if not self._model:
            raise SemanticProviderNotConfiguredError(
                "DATA_IA_GEMINI_MODEL is not configured.",
                provider=self.provider_name,
                model=None,
            )

        if self._client is None:
            raise SemanticProviderNotConfiguredError(
                "Gemini client is not configured.",
                provider=self.provider_name,
                model=self.model_name,
            )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Ejecuta Gemini y devuelve structured output normalizado."""

        self._validate_configuration()

        try:
            response = (
                self._client.models.generate_content(
                    model=self._model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type=(
                            "application/json"
                        ),
                        response_schema=(
                            GeminiSemanticOutput
                        ),
                        temperature=self._temperature,
                    ),
                )
            )

            parsed = getattr(
                response,
                "parsed",
                None,
            )

            if parsed is not None:
                if isinstance(parsed, BaseModel):
                    return parsed.model_dump()

                if isinstance(parsed, dict):
                    return parsed

                return (
                    GeminiSemanticOutput.model_validate(
                        parsed
                    ).model_dump()
                )

            raw_text = (
                getattr(
                    response,
                    "text",
                    None,
                )
                or ""
            ).strip()

            if not raw_text:
                raise SemanticProviderExecutionError(
                    "Gemini returned an empty response.",
                    provider=self.provider_name,
                    model=self.model_name,
                )

            try:
                return (
                    GeminiSemanticOutput
                    .model_validate_json(
                        raw_text
                    )
                    .model_dump()
                )

            except ValidationError as exc:
                raise SemanticProviderExecutionError(
                    "Gemini returned invalid structured output.",
                    provider=self.provider_name,
                    model=self.model_name,
                ) from exc

        except SemanticProviderExecutionError:
            raise

        except TimeoutError as exc:
            raise SemanticProviderTimeoutError(
                "Gemini request timed out.",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc

        except genai_errors.APIError as exc:
            code = getattr(
                exc,
                "code",
                None,
            )

            if code in {
                408,
                504,
            }:
                raise SemanticProviderTimeoutError(
                    "Gemini request timed out.",
                    provider=self.provider_name,
                    model=self.model_name,
                ) from exc

            raise SemanticProviderExecutionError(
                "Gemini provider request failed.",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc

        except Exception as exc:
            raise SemanticProviderExecutionError(
                "Unexpected Gemini provider failure.",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc