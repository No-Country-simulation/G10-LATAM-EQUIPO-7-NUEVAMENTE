"""Endpoints relacionados con adaptación educativa."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    status,
)

from app.api.adaptation_execution import (
    execute_adaptation,
)
from app.api.dependencies import (
    get_adaptation_orchestration_service,
)
from app.application.adaptation_orchestration_service import (
    AdaptationOrchestrationService,
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
        "automáticamente Quiz y Flashcards. Este endpoint se conserva "
        "como contrato independiente, aunque el flujo principal de "
        "Frontend se ejecuta actualmente desde POST /documents."
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
    """Ejecuta explícitamente el flujo de adaptación."""
    generated_formats = await execute_adaptation(
        orchestration_service=orchestration_service,
        document_id=payload.document_id,
        profile=payload.profile,
        niche=payload.niche,
        detail_level=payload.detail_level,
        learning_objective=(
            payload.learning_objective
        ),
    )

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