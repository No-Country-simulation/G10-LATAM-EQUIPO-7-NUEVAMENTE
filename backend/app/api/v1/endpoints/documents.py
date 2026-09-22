"""Endpoints relacionados con documentos.

Los casos de uso se conectarán mediante DocumentService cuando se complete
la composición de dependencias de BackendAPI.
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)