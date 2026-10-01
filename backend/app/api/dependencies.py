"""Dependencias compartidas por los endpoints de BackendAPI."""

from pathlib import Path

from fastapi import Request

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
from app.infrastructure.storage.local_temporary_storage_adapter import (
    LocalTemporaryStorageAdapter,
)
from app.ports.object_storage_port import (
    ObjectStoragePort,
)
from app.ports.temporary_storage_port import (
    TemporaryStoragePort,
)


def get_document_service(
    request: Request,
) -> DocumentService:
    """Obtiene el servicio de documentos configurado."""
    service = getattr(
        request.app.state,
        "document_service",
        None,
    )

    if service is None:
        raise RuntimeError(
            "DocumentService no fue inicializado."
        )

    return service


def get_format_generation_service(
    request: Request,
) -> FormatGenerationService:
    """Obtiene el servicio de generación de formatos configurado."""
    service = getattr(
        request.app.state,
        "format_generation_service",
        None,
    )

    if service is None:
        raise RuntimeError(
            "FormatGenerationService no fue inicializado."
        )

    return service


def get_generated_format_query_service(
    request: Request,
) -> GeneratedFormatQueryService:
    """Obtiene el servicio de consulta de formatos generado."""
    service = getattr(
        request.app.state,
        "generated_format_query_service",
        None,
    )

    if service is None:
        raise RuntimeError(
            "GeneratedFormatQueryService no fue inicializado."
        )

    return service


def get_object_storage(
    request: Request,
) -> ObjectStoragePort:
    """Obtiene el almacenamiento persistente configurado."""
    storage = getattr(
        request.app.state,
        "object_storage",
        None,
    )

    if storage is None:
        raise RuntimeError(
            "ObjectStoragePort no fue inicializado."
        )

    return storage


def get_rag_integration_service(
    request: Request,
) -> RAGIntegrationService:
    """Obtiene la integración BackendAPI-RAG configurada."""
    service = getattr(
        request.app.state,
        "rag_integration_service",
        None,
    )

    if service is None:
        raise RuntimeError(
            "RAGIntegrationService no fue inicializado."
        )

    return service


def get_adaptation_orchestration_service(
    request: Request,
) -> AdaptationOrchestrationService:
    """Obtiene el orquestador de adaptación configurado."""
    service = getattr(
        request.app.state,
        "adaptation_orchestration_service",
        None,
    )

    if service is None:
        raise RuntimeError(
            "AdaptationOrchestrationService no fue inicializado."
        )

    return service


def get_temporary_storage() -> TemporaryStoragePort:
    """Construye el adaptador de almacenamiento temporal configurado."""
    return LocalTemporaryStorageAdapter(
        base_directory=Path(
            settings.UPLOAD_DIR
        ),
        max_size_bytes=(
            settings.max_upload_size_bytes
        ),
    )