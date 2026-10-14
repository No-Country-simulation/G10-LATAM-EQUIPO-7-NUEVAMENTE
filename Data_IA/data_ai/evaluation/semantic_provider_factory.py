"""Factory para seleccionar el SemanticProvider de Data/IA.

La selección depende exclusivamente de configuración externa.

Reglas:

- Si DATA_IA_GEMINI_API_KEY y DATA_IA_GEMINI_MODEL están configurados,
  se utiliza GeminiSemanticProvider.

- Si falta cualquiera de las variables necesarias,
  se utiliza UnavailableSemanticProvider.

Este módulo NO:
- ejecuta evaluaciones;
- conoce FastAPI;
- combina scores;
- decide verdict;
- persiste estado.
"""

from __future__ import annotations

import os

from data_ai.evaluation.gemini_semantic_provider import (
    GeminiSemanticProvider,
)
from data_ai.evaluation.semantic_provider import (
    SemanticProvider,
)
from data_ai.evaluation.unavailable_semantic_provider import (
    UnavailableSemanticProvider,
)


DATA_IA_GEMINI_API_KEY_ENV = "DATA_IA_GEMINI_API_KEY"
DATA_IA_GEMINI_MODEL_ENV = "DATA_IA_GEMINI_MODEL"


def build_semantic_provider() -> SemanticProvider:
    """Construye el provider semántico según variables de entorno."""

    api_key = os.getenv(
        DATA_IA_GEMINI_API_KEY_ENV,
        "",
    ).strip()

    model = os.getenv(
        DATA_IA_GEMINI_MODEL_ENV,
        "",
    ).strip()

    if not api_key or not model:
        return UnavailableSemanticProvider()

    return GeminiSemanticProvider(
        api_key=api_key,
        model=model,
    )