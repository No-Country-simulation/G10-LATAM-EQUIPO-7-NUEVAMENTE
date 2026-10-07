"""Orquestación del flujo de adaptación educativa."""

from app.application.document_service import (
    DocumentService,
)
from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.application.rag_integration_service import (
    RAGIntegrationService,
)
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
)


class AdaptationDocumentStateError(Exception):
    """El documento no está en un estado válido para adaptación."""


class AdaptationOrchestrationService:
    """Coordina indexación y generación de formatos educativos.

    BackendAPI separa explícitamente tres responsabilidades:

    1. garantizar que el documento quede indexado;
    2. registrar los intentos de generación en ``processing``;
    3. completar esos intentos posteriormente mediante Agentes.

    De esta forma ``POST /documents`` puede responder cuando el
    documento ya está indexado y los formatos fueron registrados como
    trabajo activo, sin esperar a que termine la generación mediante LLM.

    El servicio no implementa acceso directo a OCI, RAG, Agentes ni
    persistencia. Estas responsabilidades permanecen delegadas a los
    servicios especializados.
    """

    _DEFAULT_FORMATS = (
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    )

    _INDEXABLE_STATUSES = frozenset(
        {
            DocumentStatus.STORED,
            DocumentStatus.INDEXING_FAILED,
        }
    )

    def __init__(
        self,
        *,
        document_service: DocumentService,
        rag_integration_service: RAGIntegrationService,
        format_generation_service: FormatGenerationService,
    ) -> None:
        self._document_service = document_service
        self._rag_integration_service = (
            rag_integration_service
        )
        self._format_generation_service = (
            format_generation_service
        )

    async def ensure_document_indexed(
        self,
        document_id: str,
    ) -> None:
        """Garantiza que un documento esté disponible en RAG."""
        document = self._document_service.get_document(
            document_id
        )

        if (
            document.status
            in self._INDEXABLE_STATUSES
        ):
            await (
                self._rag_integration_service
                .index_document(
                    document_id
                )
            )
            return

        if (
            document.status
            == DocumentStatus.INDEXED
        ):
            return

        raise AdaptationDocumentStateError(
            f"El documento {document_id} está en estado "
            f"{document.status.value} y no puede iniciar "
            "la indexación para adaptación."
        )

    def prepare_default_formats(
        self,
        *,
        document_id: str,
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[GeneratedFormat]:
        """Registra Quiz y Flashcards como intentos ``processing``.

        Esta etapa ocurre después de confirmar la indexación y antes
        de responder a Frontend.

        Returns:
            Intentos persistidos que deberán completarse posteriormente.
        """
        return (
            self._format_generation_service
            .prepare_generation(
                document_id=document_id,
                formats=self._DEFAULT_FORMATS,
                profile=profile,
                niche=niche,
                detail_level=detail_level,
                learning_objective=learning_objective,
            )
        )

    async def complete_default_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...
        ],
    ) -> list[GeneratedFormat]:
        """Completa un lote previamente registrado como ``processing``.

        Esta operación está diseñada para ejecutarse en segundo plano.
        Los mismos ``format_id`` pasan a un estado terminal.
        """
        return await (
            self._format_generation_service
            .complete_generation(
                attempts=attempts
            )
        )
