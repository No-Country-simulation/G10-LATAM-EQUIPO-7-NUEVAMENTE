from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.adaptation_execution import execute_background_generation
from app.api.dependencies import (
    get_adaptation_orchestration_service,
    get_format_generation_service,
)
from app.application.adaptation_orchestration_service import (
    AdaptationOrchestrationService,
)
from app.application.format_generation_service import (
    DocumentNotReadyForGenerationError,
    FormatGenerationDocumentNotFoundError,
    FormatGenerationService,
)
from app.core.error_codes import ErrorCode
from app.core.http_exceptions import APIHTTPException
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
)
from app.schemas.format_generation import (
    FormatGenerationResponse,
    PublicFormatGenerationRequest,
)

router = APIRouter(
    prefix="/documents/{document_id}/formats", 
    tags=["formats"]
)

@router.post(
    "/generate",
    response_model=FormatGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generar formatos públicos específicos",
    description="Inicia la generación de uno o más formatos en background (202 Accepted)."
)
async def generate_formats_public(
    document_id: str,
    request: PublicFormatGenerationRequest,
    background_tasks: BackgroundTasks,
    orchestration_service: Annotated[
        AdaptationOrchestrationService,
        Depends(get_adaptation_orchestration_service),
    ],
    generation_service: Annotated[
        FormatGenerationService,
        Depends(get_format_generation_service),
    ],
):
    try:
        attempts = generation_service.prepare_generation(
            document_id=document_id,
            formats=tuple(request.formats),
            profile=request.profile,
            niche=request.niche,
            detail_level=request.detail_level,
            learning_objective=request.learning_objective,
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.FORMAT_REGISTRATION_FAILED,
            detail="El documento fue indexado, pero no fue posible registrar la generación.",
        ) from exc

    background_tasks.add_task(
        execute_background_generation,
        orchestration_service=orchestration_service,
        attempts=tuple(attempts),
    )

    return FormatGenerationResponse.from_attempts(tuple(attempts))