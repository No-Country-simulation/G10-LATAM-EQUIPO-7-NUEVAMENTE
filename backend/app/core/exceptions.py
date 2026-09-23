"""Manejadores de errores: toda respuesta de error usa el schema `ErrorResponse`."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import (
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _json(status_code: int, payload: ErrorResponse) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return _json(
            exc.status_code,
            ErrorResponse(detail=str(exc.detail)),
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
                    str(part) for part in error["loc"][1:]
                )
                or None,
            )
            for error in exc.errors()
        ]

        return _json(
            HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorResponse(
                detail="Error de validación en la petición.",
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
                detail="Error interno del servidor."
            ),
        )