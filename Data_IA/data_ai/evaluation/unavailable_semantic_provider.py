"""Provider semántico utilizado cuando no existe configuración LLM.

Permite ejecutar Evaluation V2 de forma controlada antes de conectar
un proveedor real como Gemini.

El provider no devuelve resultados sintéticos ni inventa scores.
Expresa explícitamente que la evaluación semántica no está disponible.
"""

from __future__ import annotations

from typing import Any

from data_ai.evaluation.semantic_provider import (
    SemanticProvider,
    SemanticProviderNotConfiguredError,
)


class UnavailableSemanticProvider(
    SemanticProvider
):
    """Provider que representa una configuración semántica ausente."""

    @property
    def provider_name(self) -> str:
        return "unavailable"

    @property
    def model_name(self) -> str | None:
        return None

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Indica explícitamente que el provider no está configurado."""

        raise SemanticProviderNotConfiguredError(
            "Semantic provider is not configured.",
            provider=self.provider_name,
            model=None,
        )