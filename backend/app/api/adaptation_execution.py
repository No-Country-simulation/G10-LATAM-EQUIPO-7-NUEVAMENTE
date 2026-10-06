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
    FormatGenerationContractError,
    FormatGenerationDocumentNotFoundError,
    FormatGenerationIntegrationError,
)
from app.application.rag_integration_service import (
    RAGIntegrationError,
)

logger = logging.getLogger(__name__)


async def execute_indexing(
    *,
    orchestration_service: AdaptationOrchestrationService,
    document_id: str,
) -> None:
    """Ejecuta la indexación síncrona y traduce errores a HTTP.

    La indexación forma parte del contrato de ``POST /documents``:
    el endpoint solo responde correctamente cuando el documento queda
    disponible en RAG.

    Args:
        orchestration_service: Orquestador de adaptación configurado.
        document_id: Documento que debe quedar indexado.

    Raises:
        HTTPException: Traducción HTTP de errores de aplicación,
            almacenamiento o integración RAG.
    """
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


async def execute_background_generation(
    *,
    orchestration_service: AdaptationOrchestrationService,
    document_id: str,
    profile: str,
    niche: str,
    detail_level: str,
    learning_objective: str | None = None,
) -> None:
    """Ejecuta generación pedagógica después de responder al cliente.

    Los fallos de Agentes no pueden modificar una respuesta HTTP que ya
    fue enviada. FormatGenerationService conserva los intentos fallidos
    cuando Agentes falla, supera su timeout o incumple el contrato.

    Cualquier error se registra explícitamente para observabilidad y no
    se propaga hacia la respuesta de ``POST /documents``.
    """
    try:
        await (
            orchestration_service
            .generate_default_formats(
                document_id=document_id,
                profile=profile,
                niche=niche,
                detail_level=detail_level,
                learning_objective=learning_objective,
            )
        )

    except (
        DocumentNotFoundError,
        FormatGenerationDocumentNotFoundError,
        DocumentNotReadyForGenerationError,
        FormatGenerationIntegrationError,
        FormatGenerationContractError,
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