"""Orquestación del flujo de adaptación educativa."""

import logging

from app.application.document_service import (
    DocumentService,
)
from app.application.format_evaluation_service import (
    EvaluationResponseMismatchError,
    FormatEvaluationIntegrationError,
    FormatEvaluationService,
    GeneratedFormatNotEvaluationReadyError,
    GeneratedFormatNotFoundError,
)
from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.application.generated_package_storage_service import (
    GeneratedPackageStorageService,
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
from app.ports.format_evaluation_repository_port import (
    FormatEvaluationRepositoryError,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
)

logger = logging.getLogger(__name__)


class AdaptationDocumentStateError(Exception):
    """El documento no está en un estado válido para adaptación."""


class AdaptationOrchestrationService:
    """Coordina indexación, generación, evaluación y snapshot educativo.

    BackendAPI separa explícitamente estas responsabilidades:

    1. garantizar que el documento quede indexado;
    2. registrar los intentos de generación en ``processing``;
    3. completar esos intentos posteriormente mediante Agentes;
    4. solicitar a Data/IA la evaluación de formatos exitosos;
    5. persistir en Object Storage el snapshot educativo terminal vigente;
    6. cerrar en ``failed`` cualquier intento que continúe activo cuando
       la ejecución en segundo plano termina con un error.

    Data/IA evalúa contenido ya generado. Un fallo de evaluación no cambia
    un ``GeneratedFormat`` exitoso a ``failed`` ni impide persistir el
    snapshot educativo. La evaluación es un resultado de calidad separado.

    El servicio no implementa acceso directo a OCI, RAG, Agentes, Data/IA
    ni persistencia. Estas responsabilidades permanecen delegadas a los
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
        generated_package_storage_service: (
            GeneratedPackageStorageService
        ),
        format_evaluation_service: (
            FormatEvaluationService | None
        ) = None,
    ) -> None:
        self._document_service = document_service
        self._rag_integration_service = (
            rag_integration_service
        )
        self._format_generation_service = (
            format_generation_service
        )
        self._generated_package_storage_service = (
            generated_package_storage_service
        )
        self._format_evaluation_service = (
            format_evaluation_service
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
            ...,
        ],
    ) -> list[GeneratedFormat]:
        """Completa generación, evalúa éxitos y actualiza el paquete OCI.

        La misma operación se utiliza tanto para la generación inicial como
        para regeneraciones. Data/IA recibe únicamente formatos que ya
        terminaron exitosamente y cuentan con contenido y evidencias.

        Los errores esperados de evaluación se aíslan por formato para que
        no alteren el estado terminal generado por Agentes.
        """
        completed_attempts = await (
            self._format_generation_service
            .complete_generation(
                attempts=attempts
            )
        )

        await self._evaluate_completed_formats(
            completed_attempts
        )

        if completed_attempts:
            self._generated_package_storage_service.persist_current_package(
                completed_attempts[0].document_id
            )

        return completed_attempts

    def fail_default_generation(
        self,
        *,
        attempts: tuple[
            GeneratedFormat,
            ...,
        ],
        error_message: str,
    ) -> list[GeneratedFormat]:
        """Cierra únicamente intentos que sigan en ``processing``.

        Este método se utiliza como compensación cuando la ejecución en
        segundo plano termina con un error que no alcanzó a producir un
        estado terminal para todo el lote.
        """
        return (
            self._format_generation_service
            .fail_processing_attempts(
                attempts=attempts,
                error_message=error_message,
            )
        )

    async def _evaluate_completed_formats(
        self,
        completed_attempts: list[
            GeneratedFormat
        ],
    ) -> None:
        """Evalúa en modo best-effort los formatos exitosos del lote."""
        if (
            self._format_evaluation_service
            is None
        ):
            return

        for generated_format in (
            completed_attempts
        ):
            if not (
                generated_format
                .is_evaluation_ready
            ):
                continue

            try:
                await (
                    self._format_evaluation_service
                    .evaluate_format(
                        generated_format.format_id
                    )
                )

            except (
                GeneratedFormatNotFoundError,
                GeneratedFormatNotEvaluationReadyError,
                EvaluationResponseMismatchError,
                FormatEvaluationIntegrationError,
                FormatEvaluationRepositoryError,
                GeneratedFormatRepositoryError,
            ):
                logger.exception(
                    "No fue posible evaluar el formato %s "
                    "mediante Data/IA. La generación %s "
                    "conserva su estado %s.",
                    generated_format.format_id,
                    generated_format.format_type.value,
                    generated_format.status.value,
                )
