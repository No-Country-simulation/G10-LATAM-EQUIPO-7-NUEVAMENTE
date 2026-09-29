"""Contrato provisional entre BackendAPI y el módulo de Agentes."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentAdaptationInput:
    """Parámetros necesarios para solicitar una adaptación educativa."""

    document_id: str
    profile: str
    output_format: str
    niche: str
    detail_level: str


@dataclass(frozen=True, slots=True)
class AgentAdaptationResult:
    """Resultado estructurado devuelto por el módulo de Agentes.

    Las estructuras internas permanecerán provisionales hasta cerrar
    el contrato definitivo con RAG/Agentes y Frontend.
    """

    metadata: Mapping[str, object]
    content: Mapping[str, object]
    quality: Mapping[str, object]


class AgentsPort(Protocol):
    """Operaciones del sistema de agentes requeridas por BackendAPI."""

    async def generate_adaptation(
        self,
        request: AgentAdaptationInput,
    ) -> AgentAdaptationResult:
        """Genera contenido educativo adaptado."""
        ...