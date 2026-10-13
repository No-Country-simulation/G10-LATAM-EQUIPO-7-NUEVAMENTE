"""Caso de uso para regenerar formatos educativos persistidos."""

from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
    GenerationContext,
)
from app.ports.document_repository_port import (
    DocumentRepositoryPort,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryPort,
)


class FormatRegenerationDocumentNotFoundError(Exception):
    """El documento solicitado para regeneración no existe."""


class FormatRegenerationDocumentStateError(Exception):
    """El documento no está listo para regenerar formatos."""


class FormatRegenerationInProgressError(Exception):
    """Existe un intento activo para alguno de los formatos solicitados."""


class FormatRegenerationContextNotFoundError(Exception):
    """No existe contexto pedagógico previo para regenerar un formato."""


class FormatRegenerationContextConflictError(Exception):
    """Los formatos solicitados no comparten el mismo contexto previo."""


class FormatRegenerationService:
    """Prepara nuevos intentos reutilizando el contexto pedagógico previo.

    La responsabilidad de este servicio termina cuando los nuevos intentos
    quedan persistidos en ``processing``. La generación real continúa mediante
    el flujo de background ya existente.

    Reglas:
    - el documento debe existir y estar ``INDEXED``;
    - no se permite regenerar un formato con un intento ``PROCESSING`` activo;
    - el contexto pedagógico se recupera del intento previo más reciente de
      cada formato solicitado;
    - una regeneración crea nuevos ``format_id`` y conserva el historial.
    """

    def __init__(
        self,
        *,
        document_repository: DocumentRepositoryPort,
        generated_format_repository: GeneratedFormatRepositoryPort,
        format_generation_service: FormatGenerationService,
    ) -> None:
        self._document_repository = document_repository
        self._generated_format_repository = (
            generated_format_repository
        )
        self._format_generation_service = (
            format_generation_service
        )

    def prepare_regeneration(
        self,
        *,
        document_id: str,
        formats: tuple[
            GeneratedFormatType,
            ...,
        ],
    ) -> list[GeneratedFormat]:
        """Registra nuevos intentos ``processing`` para uno o varios formatos.

        Args:
            document_id: Identificador canónico del documento.
            formats: Formatos que Frontend desea regenerar.

        Returns:
            Nuevos intentos persistidos en estado ``PROCESSING``.

        Raises:
            ValueError:
                Si no se solicitan formatos o existen duplicados.
            FormatRegenerationDocumentNotFoundError:
                Si el documento no existe.
            FormatRegenerationDocumentStateError:
                Si el documento no está indexado.
            FormatRegenerationInProgressError:
                Si alguno de los formatos solicitados ya tiene un intento
                activo en ``PROCESSING``.
            FormatRegenerationContextNotFoundError:
                Si no existe una generación previa de alguno de los formatos.
            FormatRegenerationContextConflictError:
                Si los formatos solicitados no comparten el mismo contexto
                pedagógico previo.
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
                FormatRegenerationDocumentNotFoundError(
                    f"No existe el documento {document_id}."
                )
            )

        if (
            document.status
            != DocumentStatus.INDEXED
        ):
            raise FormatRegenerationDocumentStateError(
                f"El documento {document_id} debe estar "
                "indexed para regenerar formatos."
            )

        history = (
            self._generated_format_repository
            .find_by_document_id(
                document_id
            )
        )

        self._ensure_no_processing_attempts(
            history=history,
            formats=formats,
        )

        generation_context = (
            self._resolve_previous_context(
                history=history,
                formats=formats,
            )
        )

        return (
            self._format_generation_service
            .prepare_generation(
                document_id=document_id,
                formats=formats,
                profile=generation_context.profile,
                niche=generation_context.niche,
                detail_level=(
                    generation_context.detail_level
                ),
                learning_objective=(
                    generation_context.learning_objective
                ),
            )
        )

    @staticmethod
    def _validate_requested_formats(
        formats: tuple[
            GeneratedFormatType,
            ...,
        ],
    ) -> None:
        """Valida que la regeneración solicite formatos únicos."""
        if not formats:
            raise ValueError(
                "Debe solicitarse al menos un formato."
            )

        if len(formats) != len(set(formats)):
            raise ValueError(
                "La solicitud no puede contener formatos duplicados."
            )

    @staticmethod
    def _ensure_no_processing_attempts(
        *,
        history: list[GeneratedFormat],
        formats: tuple[
            GeneratedFormatType,
            ...,
        ],
    ) -> None:
        """Impide iniciar un nuevo intento si uno solicitado sigue activo."""
        requested_types = set(
            formats
        )

        active_types = sorted(
            {
                generated_format.format_type
                for generated_format in history
                if (
                    generated_format.format_type
                    in requested_types
                    and generated_format.status
                    == GeneratedFormatStatus.PROCESSING
                )
            },
            key=lambda format_type: (
                format_type.value
            ),
        )

        if not active_types:
            return

        active_names = ", ".join(
            format_type.value
            for format_type in active_types
        )

        raise FormatRegenerationInProgressError(
            "No es posible iniciar una nueva regeneración "
            "mientras existan intentos processing para: "
            f"{active_names}."
        )

    @classmethod
    def _resolve_previous_context(
        cls,
        *,
        history: list[GeneratedFormat],
        formats: tuple[
            GeneratedFormatType,
            ...,
        ],
    ) -> GenerationContext:
        """Obtiene el contexto del intento previo más reciente por formato."""
        previous_attempts: list[
            GeneratedFormat
        ] = []

        for format_type in formats:
            candidates = [
                generated_format
                for generated_format in history
                if (
                    generated_format.format_type
                    == format_type
                )
            ]

            if not candidates:
                raise (
                    FormatRegenerationContextNotFoundError(
                        "No existe una generación previa de "
                        f"{format_type.value} para reutilizar "
                        "su contexto pedagógico."
                    )
                )

            previous_attempts.append(
                max(
                    candidates,
                    key=cls._history_order_key,
                )
            )

        contexts = {
            attempt.generation_context
            for attempt in previous_attempts
        }

        if len(contexts) != 1:
            raise FormatRegenerationContextConflictError(
                "Los formatos solicitados no comparten "
                "el mismo contexto pedagógico previo."
            )

        return next(
            iter(contexts)
        )

    @staticmethod
    def _history_order_key(
        generated_format: GeneratedFormat,
    ) -> tuple[object, ...]:
        """Orden estable para seleccionar el intento previo más reciente."""
        return (
            generated_format.created_at,
            generated_format.updated_at,
            generated_format.format_id,
        )
