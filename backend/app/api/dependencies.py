"""Dependencias compartidas por los endpoints de BackendAPI."""

from pathlib import Path

from fastapi import Request

from app.application.document_service import DocumentService
from app.core.config import settings
from app.infrastructure.storage.local_storage import (
    LocalFileStorage,
)
from app.ports.object_storage import ObjectStoragePort
from app.ports.temporary_storage import TemporaryStoragePort


def get_document_service(
    request: Request,
) -> DocumentService:
    """Obtiene el servicio de documentos configurado en la aplicación."""
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


def get_temporary_storage() -> TemporaryStoragePort:
    """Construye el almacenamiento temporal configurado.

    La implementación concreta queda encapsulada en la composición
    de dependencias. Los endpoints consumen únicamente el contrato
    TemporaryStoragePort.
    """
    return LocalFileStorage(
        base_directory=Path(
            settings.UPLOAD_DIR
        ),
        max_size_bytes=(
            settings.max_upload_size_bytes
        ),
    )