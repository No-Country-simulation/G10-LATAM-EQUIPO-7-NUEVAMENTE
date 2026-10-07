"""Ejecución de las etapas HTTP del flujo de adaptación educativa."""

import logging

from fastapi import HTTPException, status

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
)
from app.application.rag_integration_service import (
    RAGIntegrationError,
)
from app.domain.generated_format import (
    GeneratedFormat,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
)

logger = logging.getLogger(__name__)


async def execute_indexing(
    *,
    orchestration_service: AdaptationOrchestrationService,
    document_id: str,
) -> None:
    """Ejecuta la indexación síncrona y traduce errores a HTTP."""
    try:
        await (
            orchestration_service
            .ensure_document_indexed(
                document_id
            )
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        AdaptationDocumentStateError,
        DocumentNotStoredError,
        DocumentIndexingStateError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except (
        DocumentRetrievalError,
        RAGIntegrationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
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
    ...
]:
    """Registra intentos ``processing`` antes de responder al cliente.

    Raises:
        HTTPException:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DocumentNotReadyForGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except GeneratedFormatRepositoryError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
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
        ...
    ],
) -> None:
    """Completa intentos de generación después de responder al cliente.

    Los fallos de Agentes no pueden modificar una respuesta HTTP que ya
    fue enviada. ``FormatGenerationService`` convierte los intentos
    ``processing`` a ``failed`` cuando Agentes falla, supera su timeout
    o incumple el contrato.

    Cualquier error se registra explícitamente para observabilidad.
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
        GeneratedFormatRepositoryError,
    ):
        logger.exception(
            "La generación en segundo plano falló "
            "para el documento %s.",
            document_id,
        )

    except Exception:
        logger.exception(
            "Error inesperado durante la generación "
            "en segundo plano del documento %s.",
            document_id,
        )
