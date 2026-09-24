"""Casos de uso relacionados con adaptación educativa."""

from app.domain.enums import DocumentStatus
from app.ports.agents import (
    AgentAdaptationInput,
    AgentAdaptationResult,
    AgentsPort,
)
from app.ports.document_repository import DocumentRepository


class AdaptationDocumentNotFoundError(Exception):
    """El documento solicitado para adaptación no existe."""


class DocumentNotReadyError(Exception):
    """El documento todavía no está preparado para generar contenido."""


class AdaptationService:
    """Coordina solicitudes de adaptación educativa."""

    def __init__(
        self,
        repository: DocumentRepository,
        agents: AgentsPort,
    ) -> None:
        self._repository = repository
        self._agents = agents

    async def generate(
        self,
        *,
        document_id: str,
        profile: str,
        output_format: str,
        niche: str,
        detail_level: str,
    ) -> AgentAdaptationResult:
        """Solicita contenido adaptado para un documento indexado."""
        document = self._repository.find_by_id(document_id)

        if document is None:
            raise AdaptationDocumentNotFoundError(
                f"No existe el documento {document_id}."
            )

        if document.status != DocumentStatus.INDEXED:
            raise DocumentNotReadyError(
                f"El documento {document_id} todavía no está indexado."
            )

        request = AgentAdaptationInput(
            document_id=document_id,
            profile=profile,
            output_format=output_format,
            niche=niche,
            detail_level=detail_level,
        )

        return await self._agents.generate_adaptation(request)