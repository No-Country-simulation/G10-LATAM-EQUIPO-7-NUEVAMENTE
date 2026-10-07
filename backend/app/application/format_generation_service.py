"""Casos de uso para generación y persistencia de formatos educativos."""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
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


class FormatGenerationAttemptStateError(Exception):
    """El intento persistido no puede continuar su generación."""


class FormatGenerationService:
    """Gestiona el ciclo de vida de intentos de generación.

    El caso de uso se divide explícitamente en dos etapas:

    1. ``prepare_generation`` registra los formatos solicitados en
       ``PROCESSING`` antes de iniciar la llamada a Agentes.
    2. ``complete_generation`` ejecuta Agentes y actualiza esos mismos
       intentos a ``SUCCESS``, ``FAILED`` o ``NO_RESULTS``.

    De esta forma Frontend puede observar ``processing`` mientras la
    generación ocurre en segundo plano y cada intento conserva un único
    ``format_id`` durante todo su ciclo de vida.

    El servicio no implementa prompts, retrieval, Vector Store ni LLM.
    """

    _TERMINAL_STATUSES = frozenset(
        {
            GeneratedFormatStatus.SUCCESS,
            GeneratedFormatStatus.FAILED,
            GeneratedFormatStatus.NO_RESULTS,
        }
    )

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

    def prepare_generation(
        self,
        *,
        document_id: str,
        formats: tuple[
            GeneratedFormatType,
            ...
        ],
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[GeneratedFormat]:
        """Registra intentos ``PROCESSING`` antes de llamar a Agentes.

        Args:
            document_id: Identificador canónico del documento.
            formats: Formatos que deben generarse.
            profile: Perfil educativo del destinatario.
            niche: Dominio o contexto temático.
            detail_level: Nivel de detalle esperado.
            learning_objective: Objetivo de aprendizaje opcional.

        Returns:
            Intentos persistidos en estado ``PROCESSING``.

        Raises:
            FormatGenerationDocumentNotFoundError:
                Si el documento no existe.
            DocumentNotReadyForGenerationError:
                Si el documento todavía no está indexado.
            ValueError:
                Si no se solicitan formatos o existen duplicados.
        """
        self._validate_requested_formats(
            formats
        )

        document = (
            self._document_repository.find_by_id(
                document_id
            )
        )

        if document is None:
            raise (
                FormatGenerationDocumentNotFoundError(
                    f"No existe el documento {document_id}."
                )
            )

        if (
            document.status
            != DocumentStatus.INDEXED
        ):
            raise DocumentNotReadyForGenerationError(
                f"El documento {document_id} "
                "todavía no está indexado."
            )

        generation_context = GenerationContext(
            profile=profile,
            niche=niche,
            detail_level=detail_level,
            learning_objective=learning_objective,
        )

        attempts = [
            GeneratedFormat(
                format_id=f"fmt_{uuid4().hex}",
                document_id=document_id,
                format_type=format_type,
                status=(
                    GeneratedFormatStatus.PROCESSING
                ),
                generation_context=(
                    generation_context
                ),
                content=None,
                chunks_used=(),
                error_message=None,
            )
            for format_type in formats
        ]

        return [
            self._generated_format_repository.create(
                attempt
            )
            for attempt in attempts
        ]

    async def complete_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...
        ],
    ) -> list[GeneratedFormat]:
        """Completa intentos previamente persistidos como ``PROCESSING``.

        Agentes se invoca una única vez con todos los formatos del lote.
        Los resultados actualizan los mismos ``format_id`` registrados
        antes de responder a Frontend.

        Args:
            attempts: Intentos previamente creados en ``PROCESSING``.

        Returns:
            Intentos actualizados a estados terminales.

        Raises:
            FormatGenerationAttemptStateError:
                Si los intentos no forman un lote válido en processing.
            FormatGenerationIntegrationError:
                Si falla la comunicación con Agentes.
            FormatGenerationContractError:
                Si Agentes devuelve una respuesta incompatible.
        """
        self._validate_processing_attempts(
            attempts
        )

        document_id = (
            attempts[0].document_id
        )

        generation_context = (
            attempts[0].generation_context
        )

        requested_formats = tuple(
            attempt.format_type
            for attempt in attempts
        )

        request = AgentGenerationInput(
            document_id=document_id,
            formats=requested_formats,
            generation_context=(
                generation_context
            ),
        )

        try:
            result = (
                await self._agents.generate_formats(
                    request
                )
            )

        except AgentsError as exc:
            error_message = (
                "Agentes no pudo generar los formatos "
                f"del documento {document_id}."
            )

            self._mark_attempts_failed(
                attempts=attempts,
                error_message=error_message,
            )

            raise (
                FormatGenerationIntegrationError(
                    error_message
                )
            ) from exc

        try:
            self._validate_agent_result(
                request=request,
                result=result,
            )

        except FormatGenerationContractError as exc:
            self._mark_attempts_failed(
                attempts=attempts,
                error_message=str(exc),
            )

            raise

        results_by_type = {
            agent_result.format_type: agent_result
            for agent_result
            in result.results
        }

        completed_attempts = [
            self._build_completed_attempt(
                attempt=attempt,
                agent_result=(
                    results_by_type[
                        attempt.format_type
                    ]
                ),
            )
            for attempt in attempts
        ]

        return [
            self._generated_format_repository.update(
                completed_attempt
            )
            for completed_attempt
            in completed_attempts
        ]

    def _mark_attempts_failed(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...
        ],
        error_message: str,
    ) -> list[GeneratedFormat]:
        """Actualiza a ``FAILED`` los intentos del lote actual."""
        now = datetime.now(UTC)

        failed_attempts = [
            GeneratedFormat(
                format_id=attempt.format_id,
                document_id=attempt.document_id,
                format_type=attempt.format_type,
                status=GeneratedFormatStatus.FAILED,
                generation_context=(
                    attempt.generation_context
                ),
                content=None,
                chunks_used=(),
                error_message=error_message,
                created_at=attempt.created_at,
                updated_at=now,
            )
            for attempt in attempts
        ]

        return [
            self._generated_format_repository.update(
                failed_attempt
            )
            for failed_attempt
            in failed_attempts
        ]

    @staticmethod
    def _build_completed_attempt(
        *,
        attempt: GeneratedFormat,
        agent_result: AgentGeneratedFormatResult,
    ) -> GeneratedFormat:
        """Aplica el resultado de Agentes sobre un intento existente."""
        return GeneratedFormat(
            format_id=attempt.format_id,
            document_id=attempt.document_id,
            format_type=attempt.format_type,
            status=agent_result.status,
            generation_context=(
                attempt.generation_context
            ),
            content=agent_result.content,
            chunks_used=agent_result.chunks_used,
            error_message=(
                agent_result.error_message
            ),
            created_at=attempt.created_at,
            updated_at=datetime.now(UTC),
        )

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
    def _validate_processing_attempts(
        attempts: tuple[
            GeneratedFormat,
            ...
        ],
    ) -> None:
        """Valida el lote persistido que será enviado a Agentes."""
        if not attempts:
            raise FormatGenerationAttemptStateError(
                "Debe existir al menos un intento processing."
            )

        document_ids = {
            attempt.document_id
            for attempt in attempts
        }

        if len(document_ids) != 1:
            raise FormatGenerationAttemptStateError(
                "Todos los intentos deben pertenecer "
                "al mismo documento."
            )

        format_types = [
            attempt.format_type
            for attempt in attempts
        ]

        if (
            len(format_types)
            != len(set(format_types))
        ):
            raise FormatGenerationAttemptStateError(
                "El lote contiene formatos duplicados."
            )

        contexts = {
            attempt.generation_context
            for attempt in attempts
        }

        if len(contexts) != 1:
            raise FormatGenerationAttemptStateError(
                "Todos los intentos deben compartir "
                "el mismo contexto pedagógico."
            )

        invalid_attempts = [
            attempt.format_id
            for attempt in attempts
            if (
                attempt.status
                != GeneratedFormatStatus.PROCESSING
            )
        ]

        if invalid_attempts:
            raise FormatGenerationAttemptStateError(
                "Solo pueden completarse intentos "
                "en estado processing."
            )

    @classmethod
    def _validate_agent_result(
        cls,
        *,
        request: AgentGenerationInput,
        result: AgentGenerationResult,
    ) -> None:
        """Verifica identidad, completitud y estados de Agentes."""
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

        invalid_statuses = [
            item.format_type.value
            for item in result.results
            if (
                item.status
                not in cls._TERMINAL_STATUSES
            )
        ]

        if invalid_statuses:
            raise FormatGenerationContractError(
                "Agentes devolvió estados no terminales "
                "para los formatos solicitados."
            )
