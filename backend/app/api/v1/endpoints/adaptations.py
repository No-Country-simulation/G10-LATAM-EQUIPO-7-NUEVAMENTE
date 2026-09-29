"""Endpoints relacionados con adaptación educativa.

La implementación se habilitará cuando se complete la integración con
RAG y Agentes.
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/adaptations",
    tags=["adaptations"],
)