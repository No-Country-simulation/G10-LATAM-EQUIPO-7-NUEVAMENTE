"""Manejadores de errores: toda respuesta usa el schema `ErrorResponse`."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import (
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.error_codes import ErrorCode
from app.core.http_exceptions import APIHTTPException
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _json(
    status_code: int,
    payload: ErrorResponse,
) -> JSONResponse:
    """Serializa el contrato público de error."""
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def _resolve_http_error_code(
    exc: StarletteHTTPException,
) -> ErrorCode:
    """Obtiene el código funcional de un HTTPException controlado.

    Los HTTPException creados por FastAPI/Starlette que no pertenezcan al
    contrato de BackendAPI reciben ``HTTP_ERROR`` para evitar inferir una
    causa funcional incorrecta.
    """
    if isinstance(
        exc,
        APIHTTPException,
    ):
        return exc.code

    return ErrorCode.HTTP_ERROR


def register_exception_handlers(app: FastAPI) -> None:
    """Registra el contrato transversal de errores de BackendAPI."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return _json(
            exc.status_code,
            ErrorResponse(
                code=_resolve_http_error_code(
                    exc
                ),
                detail=str(exc.detail),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            ErrorDetail(
                code=error["type"],
                message=error["msg"],
                field=".".join(
                    str(part)
                    for part in error["loc"][1:]
                )
                or None,
            )
            for error in exc.errors()
        ]

        return _json(
            HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorResponse(
                code=(
                    ErrorCode.REQUEST_VALIDATION_ERROR
                ),
                detail=(
                    "Error de validación en la petición."
                ),
                errors=errors,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        _: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Error no controlado en %s %s",
            request.method,
            request.url.path,
        )

        return _json(
            HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=(
                    ErrorCode.INTERNAL_SERVER_ERROR
                ),
                detail="Error interno del servidor.",
            ),
        )
