"""Casos de uso para generación y persistencia de formatos educativos."""

from uuid import uuid4

from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
    GenerationContext,
)
from app.ports.agents_port import (
    AgentGeneratedFormatResult,
    AgentGenerationInput,
    AgentGenerationResult,
    AgentsError,
    AgentsPort,
)
from app.ports.document_repository_port import (
    DocumentRepositoryPort,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryPort,
)


class FormatGenerationDocumentNotFoundError(Exception):
    """El documento solicitado para generación no existe."""


class DocumentNotReadyForGenerationError(Exception):
    """El documento todavía no está disponible para generar formatos."""


class FormatGenerationContractError(Exception):
    """La respuesta de Agentes no cumple el contrato acordado."""


class FormatGenerationIntegrationError(Exception):
    """No fue posible completar la generación mediante Agentes."""


class FormatGenerationService:
    """Orquesta la generación y persistencia de Quiz y Flashcards.

    BackendAPI mantiene el control del flujo de negocio. Este servicio:

    1. valida que el documento exista y esté indexado;
    2. construye el contexto pedagógico de generación;
    3. solicita a Agentes uno o más formatos;
    4. valida que la respuesta corresponda a la solicitud;
    5. convierte cada resultado en una entidad GeneratedFormat;
    6. persiste cada generación conservando su evidencia.

    El servicio no implementa prompts, retrieval, acceso al Vector Store,
    generación mediante LLM ni evaluación de calidad.
    """

    def __init__(
        self,
        *,
        document_repository: DocumentRepositoryPort,
        generated_format_repository: GeneratedFormatRepositoryPort,
        agents: AgentsPort,
    ) -> None:
        self._document_repository = document_repository
        self._generated_format_repository = (
            generated_format_repository
        )
        self._agents = agents

    async def generate_formats(
        self,
        *,
        document_id: str,
        formats: tuple[GeneratedFormatType, ...],
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[GeneratedFormat]:
        """Genera y persiste formatos educativos para un documento.

        Args:
            document_id: Identificador canónico generado por BackendAPI.
            formats: Formatos solicitados. Sprint 2 admite Quiz y Flashcards.
            profile: Perfil del destinatario.
            niche: Contexto o dominio de aplicación.
            detail_level: Nivel de detalle solicitado.
            learning_objective: Objetivo de aprendizaje opcional.

        Returns:
            Generaciones persistidas, una por cada resultado de Agentes.

        Raises:
            FormatGenerationDocumentNotFoundError:
                Si document_id no existe.
            DocumentNotReadyForGenerationError:
                Si el documento todavía no está indexado.
            FormatGenerationContractError:
                Si la respuesta de Agentes no coincide con la solicitud.
            FormatGenerationIntegrationError:
                Si falla la comunicación o procesamiento en Agentes.
        """
        self._validate_requested_formats(
            formats
        )

        document = self._document_repository.find_by_id(
            document_id
        )

        if document is None:
            raise FormatGenerationDocumentNotFoundError(
                f"No existe el documento {document_id}."
            )

        if (
            document.status
            != DocumentStatus.INDEXED
        ):
            raise DocumentNotReadyForGenerationError(
                f"El documento {document_id} todavía no está indexado."
            )

        generation_context = GenerationContext(
            profile=profile,
            niche=niche,
            detail_level=detail_level,
            learning_objective=learning_objective,
        )

        request = AgentGenerationInput(
            document_id=document_id,
            formats=formats,
            generation_context=generation_context,
        )

        try:
            result = await self._agents.generate_formats(
                request
            )
        except AgentsError as exc:
            raise FormatGenerationIntegrationError(
                "Agentes no pudo generar los formatos "
                f"del documento {document_id}."
            ) from exc

        self._validate_agent_result(
            request=request,
            result=result,
        )

        generated_formats = [
            self._build_generated_format(
                document_id=document_id,
                generation_context=generation_context,
                agent_result=agent_result,
            )
            for agent_result in result.results
        ]

        return [
            self._generated_format_repository.create(
                generated_format
            )
            for generated_format in generated_formats
        ]

    @staticmethod
    def _validate_requested_formats(
        formats: tuple[
            GeneratedFormatType,
            ...
        ],
    ) -> None:
        """Valida que la solicitud contenga formatos únicos."""
        if not formats:
            raise ValueError(
                "Debe solicitarse al menos un formato."
            )

        if len(formats) != len(set(formats)):
            raise ValueError(
                "La solicitud no puede contener formatos duplicados."
            )

    @staticmethod
    def _validate_agent_result(
        *,
        request: AgentGenerationInput,
        result: AgentGenerationResult,
    ) -> None:
        """Verifica identidad y completitud de la respuesta de Agentes."""
        if (
            result.document_id
            != request.document_id
        ):
            raise FormatGenerationContractError(
                "Agentes devolvió un document_id diferente "
                "al solicitado."
            )

        returned_formats = tuple(
            item.format_type
            for item in result.results
        )

        if (
            len(returned_formats)
            != len(set(returned_formats))
        ):
            raise FormatGenerationContractError(
                "Agentes devolvió formatos duplicados."
            )

        if (
            set(returned_formats)
            != set(request.formats)
        ):
            raise FormatGenerationContractError(
                "Los formatos devueltos por Agentes "
                "no coinciden con los solicitados."
            )

    @staticmethod
    def _build_generated_format(
        *,
        document_id: str,
        generation_context: GenerationContext,
        agent_result: AgentGeneratedFormatResult,
    ) -> GeneratedFormat:
        """Convierte un resultado atómico de Agentes al dominio."""
        return GeneratedFormat(
            format_id=f"fmt_{uuid4().hex}",
            document_id=document_id,
            format_type=agent_result.format_type,
            status=agent_result.status,
            generation_context=generation_context,
            content=agent_result.content,
            chunks_used=agent_result.chunks_used,
            error_message=agent_result.error_message,
        )