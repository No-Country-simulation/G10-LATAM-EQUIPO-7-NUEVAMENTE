"""Punto de entrada de la aplicación FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.v1.router import api_router
from app.application.adaptation_orchestration_service import (
    AdaptationOrchestrationService,
)
from app.application.document_service import (
    DocumentService,
)
from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.application.generated_format_query_service import (
    GeneratedFormatQueryService,
)
from app.application.rag_integration_service import (
    RAGIntegrationService,
)
from app.core.config import settings
from app.core.exceptions import (
    register_exception_handlers,
)
from app.core.logging import setup_logging
from app.infrastructure.integrations.http_agents_adapter import (
    HTTPAgentsAdapter,
)
from app.infrastructure.integrations.http_rag_adapter import (
    HTTPRAGAdapter,
)
from app.infrastructure.persistence.repository_factory import (
    create_document_repository,
    create_generated_format_repository,
)
from app.infrastructure.storage.oci_object_storage_adapter import (
    OCIObjectStorageAdapter,
)
from app.schemas.common import ErrorResponse


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """Inicializa y libera recursos utilizados por BackendAPI."""
    setup_logging()

    document_repository = (
        create_document_repository(
            settings.DATABASE_URL
        )
    )

    generated_format_repository = (
        create_generated_format_repository(
            settings.DATABASE_URL
        )
    )

    document_service = DocumentService(
        document_repository
    )

    generated_format_query_service = (
        GeneratedFormatQueryService(
            document_repository=(
                document_repository
            ),
            generated_format_repository=(
                generated_format_repository
            ),
        )
    )

    object_storage = (
        OCIObjectStorageAdapter(
            namespace=settings.OCI_NAMESPACE,
            bucket_name=settings.OCI_BUCKET_NAME,
            region=settings.OCI_REGION,
            config_file=settings.OCI_CONFIG_FILE,
            config_profile=settings.OCI_CONFIG_PROFILE,
        )
    )

    async with (
        httpx.AsyncClient(
            base_url=settings.RAG_BASE_URL,
            timeout=settings.RAG_TIMEOUT_SECONDS,
        ) as rag_http_client,
        httpx.AsyncClient(
            base_url=settings.AGENTS_BASE_URL,
            timeout=settings.AGENTS_TIMEOUT_SECONDS,
        ) as agents_http_client,
    ):
        rag_adapter = HTTPRAGAdapter(
            client=rag_http_client,
            index_path=settings.RAG_INDEX_PATH,
        )

        agents_adapter = HTTPAgentsAdapter(
            client=agents_http_client,
            generate_path=(
                settings.AGENTS_GENERATE_PATH
            ),
        )

        rag_integration_service = (
            RAGIntegrationService(
                document_service=(
                    document_service
                ),
                object_storage=(
                    object_storage
                ),
                rag=rag_adapter,
            )
        )

        format_generation_service = (
            FormatGenerationService(
                document_repository=(
                    document_repository
                ),
                generated_format_repository=(
                    generated_format_repository
                ),
                agents=agents_adapter,
            )
        )

        adaptation_orchestration_service = (
            AdaptationOrchestrationService(
                document_service=(
                    document_service
                ),
                rag_integration_service=(
                    rag_integration_service
                ),
                format_generation_service=(
                    format_generation_service
                ),
            )
        )

        app.state.document_service = (
            document_service
        )

        app.state.generated_format_query_service = (
            generated_format_query_service
        )

        app.state.format_generation_service = (
            format_generation_service
        )

        app.state.object_storage = (
            object_storage
        )

        app.state.rag_integration_service = (
            rag_integration_service
        )

        app.state.adaptation_orchestration_service = (
            adaptation_orchestration_service
        )

        yield


def create_app() -> FastAPI:
    """Construye la aplicación FastAPI."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        docs_url=settings.docs_url,
        redoc_url=None,
        openapi_url=(
            None
            if settings.is_production
            else "/openapi.json"
        ),
        lifespan=lifespan,
        responses={
            422: {
                "model": ErrorResponse,
                "description": (
                    "Error de validación"
                ),
            },
            500: {
                "model": ErrorResponse,
                "description": (
                    "Error interno"
                ),
            },
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            settings.BACKEND_CORS_ORIGINS
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(
        app
    )

    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
    )

    @app.get(
        "/",
        tags=["root"],
        summary="Información del servicio",
    )
    async def root() -> dict[
        str,
        str,
    ]:
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": (
                settings.docs_url
                or "deshabilitado en producción"
            ),
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