"""Dependencias compartidas por los endpoints de BackendAPI."""

from fastapi import Request

from app.application.document_service import DocumentService


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