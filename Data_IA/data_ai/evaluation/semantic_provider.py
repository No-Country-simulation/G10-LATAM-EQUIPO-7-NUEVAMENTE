"""Abstracción de proveedor para el evaluador semántico.

Este módulo define el contrato mínimo que debe cumplir cualquier proveedor
utilizado por ``semantic_evaluator.py``.

La intención es mantener la lógica de Data/IA desacoplada de SDKs concretos
como Gemini.

Arquitectura esperada:

    SemanticEvaluator
            |
            v
    SemanticProvider
            |
            +-- Fake provider (tests)
            |
            +-- Gemini provider (Sprint 4)
            |
            +-- otro proveedor futuro

Responsabilidades de este módulo:
- definir la interfaz del proveedor;
- normalizar errores técnicos del proveedor;
- exponer metadata mínima del proveedor.

Este módulo NO:
- construye prompts;
- valida scores semánticos;
- decide el status pedagógico del contenido;
- implementa fallback;
- conoce FastAPI;
- importa SDKs externos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SemanticProviderError(Exception):
    """Error base para fallos normalizados del proveedor semántico.

    Todos los errores técnicos que atraviesen la frontera entre un adapter
    concreto y ``SemanticEvaluator`` deberían convertirse en alguna de las
    excepciones definidas en este módulo.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(message)

        self.message = message
        self.provider = provider
        self.model = model

    def __str__(self) -> str:
        """Devuelve una representación legible del error."""

        context: list[str] = []

        if self.provider:
            context.append(f"provider={self.provider}")

        if self.model:
            context.append(f"model={self.model}")

        if not context:
            return self.message

        return f"{self.message} ({', '.join(context)})"


class SemanticProviderNotConfiguredError(
    SemanticProviderError
):
    """El proveedor semántico no está configurado.

    Ejemplos:
    - falta API key;
    - falta model name;
    - feature desactivada;
    - configuración mínima inexistente.

    Este error debe mapear posteriormente a:

        semantic_status = "unavailable"
        error_code = "not_configured"
    """


class SemanticProviderTimeoutError(
    SemanticProviderError
):
    """El proveedor excedió el timeout configurado.

    Este error debe mapear posteriormente a:

        semantic_status = "failed"
        error_code = "timeout"
    """


class SemanticProviderExecutionError(
    SemanticProviderError
):
    """Fallo técnico genérico durante la llamada al proveedor.

    Ejemplos:
    - proveedor temporalmente caído;
    - error HTTP inesperado;
    - error del SDK;
    - error de autenticación aún no normalizado específicamente;
    - respuesta imposible de recuperar.

    Este error debe mapear posteriormente a:

        semantic_status = "failed"
        error_code = "provider_error"
    """


class SemanticProvider(ABC):
    """Interfaz abstracta para proveedores de evaluación semántica.

    ``SemanticEvaluator`` depende únicamente de esta abstracción.

    Un adapter concreto deberá:

    1. recibir el prompt preparado por Data/IA;
    2. ejecutar el modelo;
    3. devolver el structured output como ``dict``;
    4. convertir errores propios del SDK a las excepciones normalizadas
       definidas en este módulo.

    La validación Pydantic del contenido devuelto NO corresponde a esta
    clase. Esa responsabilidad permanece en la capa de evaluación.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre estable del proveedor.

        Ejemplos:

            "fake"
            "gemini"
        """

        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str | None:
        """Nombre del modelo utilizado por el proveedor.

        Puede ser ``None`` cuando el provider todavía no está configurado.
        """

        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Genera una respuesta estructurada.

        Parameters
        ----------
        system_prompt:
            Instrucciones estables del evaluador semántico, incluyendo
            rúbrica, restricciones de grounding y formato esperado.

        user_prompt:
            Payload textual específico de la evaluación actual. Contendrá
            el contenido generado, contexto pedagógico y evidencia.

        Returns
        -------
        dict[str, Any]
            Structured output devuelto por el proveedor.

            Este diccionario todavía NO debe considerarse validado.

            ``SemanticEvaluator`` deberá convertirlo posteriormente a los
            schemas internos definidos en:

                data_ai.schemas.semantic_evaluation

        Raises
        ------
        SemanticProviderNotConfiguredError
            Cuando el proveedor no cuenta con la configuración necesaria.

        SemanticProviderTimeoutError
            Cuando la llamada supera el timeout permitido.

        SemanticProviderExecutionError
            Para otros fallos técnicos del proveedor.
        """

        raise NotImplementedError