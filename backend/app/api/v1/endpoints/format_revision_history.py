"""Consulta REST de versiones originales, correcciones y evaluaciones."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_format_revision_history_service
from app.application.format_revision_history_service import (
    FormatRevisionHistoryService,
    RevisionHistoryDocumentNotFoundError,
    RevisionHistoryInconsistentError,
)
from app.core.error_codes import ErrorCode
from app.core.http_exceptions import APIHTTPException
from app.domain.enums import GeneratedFormatType
from app.ports.document_repository_port import DocumentRepositoryError
from app.ports.format_evaluation_repository_port import FormatEvaluationRepositoryError
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryError
from app.schemas.revision_cycle import RevisionHistoryResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get(
    "/{document_id}/formats/{format_type}/history",
    response_model=RevisionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar historial de generaciones y correcciones",
)
async def get_revision_history(
    document_id: str,
    format_type: GeneratedFormatType,
    service: Annotated[
        FormatRevisionHistoryService, Depends(get_format_revision_history_service)
    ],
) -> RevisionHistoryResponse:
    """Agrupa por ciclo las evaluaciones V1/V2 sin mezclar regeneraciones."""
    try:
        return RevisionHistoryResponse.from_domain(
            service.get_history(document_id, format_type)
        )
    except RevisionHistoryDocumentNotFoundError as exc:
        raise APIHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.DOCUMENT_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        DocumentRepositoryError,
        GeneratedFormatRepositoryError,
        FormatEvaluationRepositoryError,
        RevisionHistoryInconsistentError,
    ) as exc:
        raise APIHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.PERSISTENCE_ERROR,
            detail="No fue posible consultar el historial de revisiones.",
        ) from exc
