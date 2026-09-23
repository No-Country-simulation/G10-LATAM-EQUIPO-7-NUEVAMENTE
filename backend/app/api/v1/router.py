"""Agrupa todos los routers de la versión 1 de la API."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    adaptations,
    documents,
    files,
    health,
    processes,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(adaptations.router)
api_router.include_router(processes.router)

# Endpoint legacy. Se eliminará cuando POST /documents sustituya /files/upload.
api_router.include_router(files.router)
