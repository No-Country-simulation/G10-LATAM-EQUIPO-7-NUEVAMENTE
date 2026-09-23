"""Dependencias compartidas por los endpoints de BackendAPI."""

from fastapi import Request

from app.application.document_service import DocumentService
from app.ports.object_storage import ObjectStoragePort


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
    """Obtiene el almacenamiento de objetos configurado."""
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