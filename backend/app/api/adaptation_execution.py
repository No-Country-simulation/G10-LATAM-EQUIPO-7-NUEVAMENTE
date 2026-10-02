"""Ejecución HTTP compartida del caso de uso de adaptación educativa."""

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
from app.domain.generated_format import GeneratedFormat


async def execute_adaptation(
    *,
    orchestration_service: AdaptationOrchestrationService,
    document_id: str,
    profile: str,
    niche: str,
    detail_level: str,
    learning_objective: str | None = None,
) -> list[GeneratedFormat]:
    """Ejecuta la adaptación y traduce errores de aplicación a HTTP.

    Este helper pertenece a la capa API. Permite que distintos endpoints
    disparen el mismo caso de uso sin duplicar la traducción de errores.

    Args:
        orchestration_service: Orquestador del flujo de adaptación.
        document_id: Documento que será procesado.
        profile: Perfil educativo del destinatario.
        niche: Contexto o dominio de aplicación.
        detail_level: Nivel de detalle requerido.
        learning_objective: Objetivo de aprendizaje opcional.

    Returns:
        Formatos generados y persistidos por el orquestador.

    Raises:
        HTTPException: Traducción HTTP de errores de aplicación e
            integración.
    """
    try:
        return await orchestration_service.adapt_document(
            document_id=document_id,
            profile=profile,
            niche=niche,
            detail_level=detail_level,
            learning_objective=learning_objective,
        )

    except (
        DocumentNotFoundError,
        FormatGenerationDocumentNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        AdaptationDocumentStateError,
        DocumentNotStoredError,
        DocumentIndexingStateError,
        DocumentNotReadyForGenerationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except (
        DocumentRetrievalError,
        RAGIntegrationError,
        FormatGenerationIntegrationError,
        FormatGenerationContractError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc