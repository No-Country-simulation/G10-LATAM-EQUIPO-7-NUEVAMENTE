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
from app.domain.learning_metadata import LearningMetadata
from app.ports.agents_port import (
    AgentGeneratedFormatResult,
    AgentGenerationInput,
    AgentGenerationResult,
    AgentsError,
    AgentsPort,
)
from app.ports.document_repository_port import (
    DocumentRepositoryError,
    DocumentRepositoryPort,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
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


class FormatGenerationMetadataPersistenceError(Exception):
    """No fue posible persistir la metadata pedagógica recibida."""


class FormatGenerationAttemptStateError(Exception):
    """El intento persistido no puede continuar su generación."""


class FormatGenerationRecoveryError(Exception):
    """No fue posible cerrar todos los intentos processing pendientes."""


class FormatGenerationService:
    """Gestiona el ciclo de vida de intentos de generación.

    El caso de uso se divide explícitamente en cuatro responsabilidades:

    1. ``prepare_generation`` registra los formatos solicitados en
       ``PROCESSING`` antes de iniciar la llamada a Agentes.
    2. ``complete_generation`` ejecuta Agentes y valida la respuesta.
    3. Los metadatos pedagógicos de la adaptación se persisten una sola
       vez a nivel de documento antes de cerrar los formatos.
    4. ``fail_processing_attempts`` actúa como cierre de contingencia y
       convierte únicamente los intentos que sigan persistidos en
       ``PROCESSING`` a ``FAILED``.

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
            ...,
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
            ...,
        ],
    ) -> list[GeneratedFormat]:
        """Completa intentos previamente persistidos como ``PROCESSING``.

        Agentes se invoca una única vez con todos los formatos del lote.
        La metadata pedagógica retornada se persiste una sola vez a nivel
        del documento y los resultados actualizan los mismos ``format_id``.

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
            FormatGenerationDocumentNotFoundError:
                Si el documento desaparece antes de persistir metadata.
            FormatGenerationRecoveryError:
                Si no es posible persistir el cierre a ``FAILED`` después
                de un error conocido de Agentes o de contrato.
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

            self.fail_processing_attempts(
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
            self.fail_processing_attempts(
                attempts=attempts,
                error_message=str(exc),
            )

            raise

        try:
            self._persist_learning_metadata(
                document_id=document_id,
                learning_metadata=(
                    result.learning_metadata
                ),
            )
        except (
            DocumentRepositoryError,
            FormatGenerationDocumentNotFoundError,
        ) as exc:
            error_message = (
                "No fue posible persistir los metadatos "
                f"pedagógicos del documento {document_id}."
            )

            self.fail_processing_attempts(
                attempts=attempts,
                error_message=error_message,
            )

            raise (
                FormatGenerationMetadataPersistenceError(
                    error_message
                )
            ) from exc

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

    def fail_processing_attempts(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
        error_message: str,
    ) -> list[GeneratedFormat]:
        """Cierra en ``FAILED`` solo intentos aún activos.

        Antes de actualizar cada ``format_id`` se consulta nuevamente su
        estado persistido. De esta forma un cierre de contingencia no
        sobrescribe un ``SUCCESS``, ``FAILED`` o ``NO_RESULTS`` que ya haya
        sido persistido antes de producirse otro error en el lote.

        Args:
            attempts: Intentos originales del lote de generación.
            error_message: Mensaje seguro que se persistirá en los intentos
                que todavía estén en ``PROCESSING``.

        Returns:
            Intentos que fueron efectivamente actualizados a ``FAILED``.

        Raises:
            ValueError:
                Si ``error_message`` está vacío.
            FormatGenerationRecoveryError:
                Si algún intento no puede consultarse o actualizarse por
                un error del repositorio, o si un ``format_id`` esperado ya
                no existe.
        """
        if not error_message.strip():
            raise ValueError(
                "error_message no puede estar vacío."
            )

        failed_attempts: list[
            GeneratedFormat
        ] = []

        unresolved_ids: list[str] = []
        first_repository_error: (
            GeneratedFormatRepositoryError | None
        ) = None

        now = datetime.now(UTC)

        for attempt in attempts:
            try:
                current_attempt = (
                    self._generated_format_repository
                    .find_by_id(
                        attempt.format_id
                    )
                )

                if current_attempt is None:
                    unresolved_ids.append(
                        attempt.format_id
                    )
                    continue

                if (
                    current_attempt.status
                    != GeneratedFormatStatus.PROCESSING
                ):
                    continue

                failed_attempt = (
                    self._build_failed_attempt(
                        attempt=current_attempt,
                        error_message=error_message,
                        updated_at=now,
                    )
                )

                failed_attempts.append(
                    self._generated_format_repository
                    .update(
                        failed_attempt
                    )
                )

            except GeneratedFormatRepositoryError as exc:
                unresolved_ids.append(
                    attempt.format_id
                )

                if first_repository_error is None:
                    first_repository_error = exc

        if unresolved_ids:
            unique_ids = sorted(
                set(unresolved_ids)
            )

            recovery_error = (
                FormatGenerationRecoveryError(
                    "No fue posible cerrar todos los intentos "
                    "de generación que podían seguir en processing. "
                    "format_id pendientes: "
                    f"{', '.join(unique_ids)}."
                )
            )

            if first_repository_error is not None:
                raise recovery_error from first_repository_error

            raise recovery_error

        return failed_attempts

    def _persist_learning_metadata(
        self,
        *,
        document_id: str,
        learning_metadata: LearningMetadata,
    ) -> None:
        """Persiste metadata pedagógica una sola vez a nivel de documento."""
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

        document.assign_learning_metadata(
            learning_metadata
        )

        self._document_repository.update(
            document
        )

    @staticmethod
    def _build_failed_attempt(
        *,
        attempt: GeneratedFormat,
        error_message: str,
        updated_at: datetime,
    ) -> GeneratedFormat:
        """Construye la transición de un intento activo a ``FAILED``."""
        return GeneratedFormat(
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
            updated_at=updated_at,
        )

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
            ...,
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
            ...,
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

        if not isinstance(
            result.learning_metadata,
            LearningMetadata,
        ):
            raise FormatGenerationContractError(
                "Agentes devolvió learning_metadata "
                "con un contrato inválido."
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
