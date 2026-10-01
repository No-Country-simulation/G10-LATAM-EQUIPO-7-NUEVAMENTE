"""Endpoints relacionados con adaptación educativa."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.api.dependencies import (
    get_adaptation_orchestration_service,
)
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
from app.schemas.adaptation import (
    AdaptationRequest,
    AdaptationResponse,
    AdaptationResultResponse,
)

router = APIRouter(
    prefix="/adaptations",
    tags=["adaptations"],
)


@router.post(
    "",
    response_model=AdaptationResponse,
    status_code=status.HTTP_200_OK,
    summary="Adaptar documento",
    description=(
        "Ejecuta la adaptación educativa de un documento almacenado. "
        "Backend indexa el documento cuando sea necesario y solicita "
        "automáticamente Quiz y Flashcards. Los contenidos completos "
        "pueden consultarse posteriormente mediante "
        "GET /documents/{document_id}/formats."
    ),
    responses={
        404: {
            "description": "Documento no encontrado.",
        },
        409: {
            "description": (
                "El documento no se encuentra en un estado "
                "válido para iniciar la adaptación."
            ),
        },
        502: {
            "description": (
                "Fallo durante la comunicación con OCI, RAG "
                "o Agentes, o respuesta inválida de un servicio externo."
            ),
        },
    },
)
async def adapt_document(
    payload: AdaptationRequest,
    orchestration_service: Annotated[
        AdaptationOrchestrationService,
        Depends(
            get_adaptation_orchestration_service
        ),
    ],
) -> AdaptationResponse:
    """Ejecuta el flujo completo de adaptación de Sprint 2."""
    try:
        generated_formats = (
            await orchestration_service.adapt_document(
                document_id=payload.document_id,
                profile=payload.profile,
                niche=payload.niche,
                detail_level=payload.detail_level,
                learning_objective=(
                    payload.learning_objective
                ),
            )
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

    return AdaptationResponse(
        document_id=payload.document_id,
        results=[
            AdaptationResultResponse.from_domain(
                generated_format
            )
            for generated_format
            in generated_formats
        ],
    )