"""Agrupa todos los routers de la versión 1 de la API."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    documents,
    format_regeneration,
    format_revision_history,
    health,
    public_generation,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(
    format_regeneration.router
)
api_router.include_router(format_revision_history.router)
api_router.include_router(public_generation.router)