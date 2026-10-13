"""Endpoint HTTP para regeneración de formatos educativos."""

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    status,
)

from app.api.adaptation_execution import (
    execute_background_generation,
)
from app.api.dependencies import (
    get_adaptation_orchestration_service,
    get_format_regeneration_service,
)
from app.application.adaptation_orchestration_service import (
    AdaptationOrchestrationService,
)
from app.application.format_generation_service import (
    DocumentNotReadyForGenerationError,
    FormatGenerationDocumentNotFoundError,
)
from app.application.format_regeneration_service import (
    FormatRegenerationContextConflictError,
    FormatRegenerationContextNotFoundError,
    FormatRegenerationDocumentNotFoundError,
    FormatRegenerationDocumentStateError,
    FormatRegenerationInProgressError,
    FormatRegenerationService,
)
from app.core.error_codes import ErrorCode
from app.core.http_exceptions import APIHTTPException
from app.ports.document_repository_port import (
    DocumentRepositoryError,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
)
from app.schemas.format_regeneration import (
    FormatRegenerationRequest,
    FormatRegenerationResponse,
)

router = APIRouter(
    prefix="/documents/{document_id}/formats",
    tags=["formats"],
)


@router.post(
    "/regenerate",
    response_model=FormatRegenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerar formatos educativos",
    description=(
        "Inicia un nuevo intento de generación para uno o varios "
        "formatos. Backend reutiliza automáticamente el contexto "
        "pedagógico persistido y responde cuando los nuevos intentos "
        "ya están registrados en processing."
    ),
    responses={
        404: {
            "description": (
                "Documento no encontrado."
            ),
        },
        409: {
            "description": (
                "El documento no está indexed, no existe contexto "
                "previo reutilizable o alguno de los formatos "
                "solicitados continúa en processing."
            ),
        },
        422: {
            "description": (
                "Formatos vacíos, duplicados o no soportados."
            ),
        },
        500: {
            "description": (
                "No fue posible registrar los nuevos intentos "
                "de regeneración."
            ),
        },
    },
)
async def regenerate_formats(
    document_id: str,
    request: FormatRegenerationRequest,
    background_tasks: BackgroundTasks,
    regeneration_service: Annotated[
        FormatRegenerationService,
        Depends(
            get_format_regeneration_service
        ),
    ],
    orchestration_service: Annotated[
        AdaptationOrchestrationService,
        Depends(
            get_adaptation_orchestration_service
        ),
    ],
) -> FormatRegenerationResponse:
    """Registra la regeneración y continúa el trabajo en background."""
    try:
        attempts = (
            regeneration_service
            .prepare_regeneration(
                document_id=document_id,
                formats=tuple(
                    request.formats
                ),
            )
        )

    except (
        FormatRegenerationDocumentNotFoundError,
        FormatGenerationDocumentNotFoundError,
    ) as exc:
        raise APIHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.DOCUMENT_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        FormatRegenerationDocumentStateError,
        DocumentNotReadyForGenerationError,
    ) as exc:
        raise APIHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.DOCUMENT_NOT_INDEXED,
            detail=str(exc),
        ) from exc

    except FormatRegenerationInProgressError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            code=(
                ErrorCode.FORMAT_REGENERATION_IN_PROGRESS
            ),
            detail=str(exc),
        ) from exc

    except FormatRegenerationContextNotFoundError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.FORMAT_CONTEXT_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except FormatRegenerationContextConflictError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.FORMAT_CONTEXT_CONFLICT,
            detail=str(exc),
        ) from exc

    except DocumentRepositoryError as exc:
        raise APIHTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            code=ErrorCode.PERSISTENCE_ERROR,
            detail=(
                "No fue posible consultar la persistencia "
                "del documento durante la regeneración."
            ),
        ) from exc

    except GeneratedFormatRepositoryError as exc:
        raise APIHTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            code=(
                ErrorCode
                .FORMAT_REGENERATION_REGISTRATION_FAILED
            ),
            detail=(
                "No fue posible registrar los nuevos "
                "intentos de regeneración."
            ),
        ) from exc

    generation_attempts = tuple(
        attempts
    )

    background_tasks.add_task(
        execute_background_generation,
        orchestration_service=(
            orchestration_service
        ),
        attempts=generation_attempts,
    )

    return (
        FormatRegenerationResponse
        .from_attempts(
            generation_attempts
        )
    )
