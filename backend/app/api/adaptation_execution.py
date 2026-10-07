"""Ejecución de las etapas HTTP del flujo de adaptación educativa."""

import logging

from fastapi import status

from app.application.adaptation_orchestration_service import (
    AdaptationDocumentStateError,
    AdaptationOrchestrationService,
)
from app.application.document_service import (
    DocumentIndexingStateError,
    DocumentNotFoundError,
    DocumentNotStoredError,
    DocumentRetrievalError,
)
from app.application.format_generation_service import (
    DocumentNotReadyForGenerationError,
    FormatGenerationAttemptStateError,
    FormatGenerationContractError,
    FormatGenerationDocumentNotFoundError,
    FormatGenerationIntegrationError,
    FormatGenerationRecoveryError,
)
from app.application.rag_integration_service import (
    RAGIntegrationError,
)
from app.core.error_codes import ErrorCode
from app.core.http_exceptions import APIHTTPException
from app.domain.generated_format import (
    GeneratedFormat,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
)

logger = logging.getLogger(__name__)

_BACKGROUND_FAILURE_MESSAGE = (
    "La generación terminó con un error interno antes de completar "
    "todos los formatos."
)


async def execute_indexing(
    *,
    orchestration_service: AdaptationOrchestrationService,
    document_id: str,
) -> None:
    """Ejecuta la indexación síncrona y traduce errores al contrato HTTP."""
    try:
        await (
            orchestration_service
            .ensure_document_indexed(
                document_id
            )
        )

    except DocumentNotFoundError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.DOCUMENT_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        AdaptationDocumentStateError,
        DocumentNotStoredError,
        DocumentIndexingStateError,
    ) as exc:
        raise APIHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.DOCUMENT_STATE_CONFLICT,
            detail=str(exc),
        ) from exc

    except DocumentRetrievalError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.DOCUMENT_RETRIEVAL_FAILED,
            detail=str(exc),
        ) from exc

    except RAGIntegrationError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.RAG_INDEXING_FAILED,
            detail=str(exc),
        ) from exc


def prepare_background_generation(
    *,
    orchestration_service: AdaptationOrchestrationService,
    document_id: str,
    profile: str,
    niche: str,
    detail_level: str,
    learning_objective: str | None = None,
) -> tuple[
    GeneratedFormat,
    ...,
]:
    """Registra intentos ``processing`` antes de responder al cliente.

    Raises:
        APIHTTPException:
            Si el documento no puede iniciar generación o falla la
            persistencia de los intentos.
    """
    try:
        attempts = (
            orchestration_service
            .prepare_default_formats(
                document_id=document_id,
                profile=profile,
                niche=niche,
                detail_level=detail_level,
                learning_objective=learning_objective,
            )
        )

    except FormatGenerationDocumentNotFoundError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.DOCUMENT_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DocumentNotReadyForGenerationError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.DOCUMENT_NOT_INDEXED,
            detail=str(exc),
        ) from exc

    except GeneratedFormatRepositoryError as exc:
        raise APIHTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            code=ErrorCode.FORMAT_REGISTRATION_FAILED,
            detail=(
                "El documento fue indexado, pero no fue posible "
                "registrar la generación de formatos."
            ),
        ) from exc

    return tuple(
        attempts
    )


async def execute_background_generation(
    *,
    orchestration_service: AdaptationOrchestrationService,
    attempts: tuple[
        GeneratedFormat,
        ...,
    ],
) -> None:
    """Completa intentos de generación después de responder al cliente.

    Los errores conocidos de Agentes y contrato se resuelven dentro de la
    capa de aplicación. Si aparece cualquier otro error, se ejecuta una
    compensación adicional que consulta el estado persistido y convierte
    únicamente los intentos que sigan en ``processing`` a ``failed``.

    Como la respuesta HTTP ya fue enviada, los errores se registran para
    observabilidad y no se propagan al cliente.
    """
    document_id = (
        attempts[0].document_id
        if attempts
        else "desconocido"
    )

    try:
        await (
            orchestration_service
            .complete_default_generation(
                attempts=attempts
            )
        )

    except (
        FormatGenerationAttemptStateError,
        FormatGenerationIntegrationError,
        FormatGenerationContractError,
        FormatGenerationRecoveryError,
        GeneratedFormatRepositoryError,
    ):
        _fail_remaining_processing_attempts(
            orchestration_service=orchestration_service,
            attempts=attempts,
            document_id=document_id,
        )

        logger.exception(
            "La generación en segundo plano falló "
            "para el documento %s.",
            document_id,
        )

    except Exception:
        _fail_remaining_processing_attempts(
            orchestration_service=orchestration_service,
            attempts=attempts,
            document_id=document_id,
        )

        logger.exception(
            "Error inesperado durante la generación "
            "en segundo plano del documento %s.",
            document_id,
        )


def _fail_remaining_processing_attempts(
    *,
    orchestration_service: AdaptationOrchestrationService,
    attempts: tuple[
        GeneratedFormat,
        ...,
    ],
    document_id: str,
) -> None:
    """Ejecuta el cierre de contingencia sin ocultar un segundo fallo."""
    try:
        orchestration_service.fail_default_generation(
            attempts=attempts,
            error_message=(
                _BACKGROUND_FAILURE_MESSAGE
            ),
        )

    except Exception:
        logger.exception(
            "No fue posible cerrar todos los intentos "
            "processing del documento %s después de "
            "un error de background.",
            document_id,
        )
