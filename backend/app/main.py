"""Punto de entrada de la aplicación FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.application.document_service import DocumentService
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.infrastructure.persistence.repository_factory import (
    create_document_repository,
)
from app.infrastructure.storage.oci_object_storage import (
    OCIObjectStorage,
)
from app.schemas.common import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicializa y libera recursos utilizados por BackendAPI."""
    setup_logging()

    document_repository = create_document_repository(
        settings.DATABASE_URL
    )

    app.state.document_service = DocumentService(
        document_repository
    )
    
    app.state.object_storage = OCIObjectStorage(
        namespace=settings.OCI_NAMESPACE,
        bucket_name=settings.OCI_BUCKET_NAME,
        region=settings.OCI_REGION,
        config_file=settings.OCI_CONFIG_FILE,
        config_profile=settings.OCI_CONFIG_PROFILE,
    )

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        docs_url=settings.docs_url,
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
        responses={
            422: {"model": ErrorResponse, "description": "Error de validación"},
            500: {"model": ErrorResponse, "description": "Error interno"},
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["root"], summary="Información del servicio")
    async def root() -> dict[str, str]:
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": settings.docs_url or "deshabilitado en producción",
        }

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
