"""Caso de uso para consultar formatos educativos persistidos."""

from dataclasses import dataclass

from app.domain.enums import (
    DocumentFormatsStatus,
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
)
from app.ports.document_repository_port import (
    DocumentRepositoryPort,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryPort,
)

_FAILED_DOCUMENT_STATUSES = frozenset(
    {
        DocumentStatus.VALIDATION_FAILED,
        DocumentStatus.STORAGE_FAILED,
        DocumentStatus.INDEXING_FAILED,
    }
)

_PROCESSING_DOCUMENT_STATUSES = frozenset(
    {
        DocumentStatus.INDEXING,
    }
)


class GeneratedFormatQueryDocumentNotFoundError(
    Exception
):
    """El documento solicitado no existe."""


@dataclass(frozen=True, slots=True)
class DocumentFormatsResult:
    """Resultado de consultar los formatos de un documento."""

    document_id: str
    status: DocumentFormatsStatus
    formats: tuple[
        GeneratedFormat,
        ...
    ]


class GeneratedFormatQueryService:
    """Consulta formatos educativos generados y persistidos.

    La persistencia conserva historial completo de generaciones.

    Para la respuesta pública se selecciona un único resultado por
    tipo de formato:

    - la generación exitosa más reciente, cuando existe;
    - en ausencia de generaciones exitosas, el intento más reciente.

    De esta forma, un reintento fallido no oculta contenido válido
    generado previamente.
    """

    def __init__(
        self,
        *,
        document_repository: DocumentRepositoryPort,
        generated_format_repository: (
            GeneratedFormatRepositoryPort
        ),
    ) -> None:
        self._document_repository = (
            document_repository
        )
        self._generated_format_repository = (
            generated_format_repository
        )

    def get_document_formats(
        self,
        document_id: str,
    ) -> DocumentFormatsResult:
        """Consulta los formatos disponibles de un documento.

        Args:
            document_id: Identificador canónico del documento.

        Returns:
            Estado agregado y formatos actualmente disponibles.

        Raises:
            GeneratedFormatQueryDocumentNotFoundError:
                Si el documento no existe.
        """
        document = (
            self._document_repository.find_by_id(
                document_id
            )
        )

        if document is None:
            raise (
                GeneratedFormatQueryDocumentNotFoundError(
                    "No existe el documento "
                    f"{document_id}."
                )
            )

        history = (
            self._generated_format_repository
            .find_by_document_id(
                document_id
            )
        )

        if not history:
            return DocumentFormatsResult(
                document_id=document_id,
                status=(
                    self._resolve_empty_history_status(
                        document.status
                    )
                ),
                formats=(),
            )

        selected_formats = (
            self._select_current_formats(
                history
            )
        )

        return DocumentFormatsResult(
            document_id=document_id,
            status=(
                self._resolve_aggregate_status(
                    selected_formats
                )
            ),
            formats=selected_formats,
        )

    @staticmethod
    def _resolve_empty_history_status(
        document_status: DocumentStatus,
    ) -> DocumentFormatsStatus:
        """Resuelve el estado cuando todavía no hay generaciones.

        ``INDEXING`` representa procesamiento activo del documento.

        ``INDEXED`` solo confirma que la indexación terminó correctamente.
        No implica que la generación se encuentre ejecutándose. Si un
        documento está indexado y aún no existe historial de formatos,
        la generación permanece pendiente.

        Los fallos de generación se representan mediante registros
        ``GeneratedFormat`` con estado ``FAILED`` y se resuelven a
        ``DocumentFormatsStatus.ERROR`` mediante el historial.
        """
        if (
            document_status
            in _FAILED_DOCUMENT_STATUSES
        ):
            return (
                DocumentFormatsStatus.ERROR
            )

        if (
            document_status
            in _PROCESSING_DOCUMENT_STATUSES
        ):
            return (
                DocumentFormatsStatus.PROCESSING
            )

        return DocumentFormatsStatus.PENDING

    @staticmethod
    def _select_current_formats(
        history: list[
            GeneratedFormat
        ],
    ) -> tuple[
        GeneratedFormat,
        ...
    ]:
        """Selecciona un resultado vigente por tipo de formato."""
        selected_formats: list[
            GeneratedFormat
        ] = []

        for format_type in GeneratedFormatType:
            candidates = [
                generated_format
                for generated_format
                in history
                if (
                    generated_format.format_type
                    == format_type
                )
            ]

            if not candidates:
                continue

            successful_candidates = [
                generated_format
                for generated_format
                in candidates
                if (
                    generated_format.status
                    == GeneratedFormatStatus.SUCCESS
                )
            ]

            available_candidates = (
                successful_candidates
                if successful_candidates
                else candidates
            )

            current_format = max(
                available_candidates,
                key=lambda generated_format: (
                    generated_format.created_at,
                    generated_format.updated_at,
                    generated_format.format_id,
                ),
            )

            selected_formats.append(
                current_format
            )

        return tuple(
            selected_formats
        )

    @staticmethod
    def _resolve_aggregate_status(
        formats: tuple[
            GeneratedFormat,
            ...
        ],
    ) -> DocumentFormatsStatus:
        """Calcula el estado agregado consumido por Frontend."""
        successful_types = {
            generated_format.format_type
            for generated_format
            in formats
            if (
                generated_format.status
                == GeneratedFormatStatus.SUCCESS
            )
        }

        supported_types = set(
            GeneratedFormatType
        )

        if (
            successful_types
            == supported_types
        ):
            return (
                DocumentFormatsStatus.READY
            )

        if successful_types:
            return (
                DocumentFormatsStatus.PARTIAL
            )

        return DocumentFormatsStatus.ERROR