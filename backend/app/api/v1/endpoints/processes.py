"""Endpoints relacionados con procesos de BackendAPI.

Las operaciones de consulta se incorporarán cuando exista persistencia
durable para los procesos.
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/processes",
    tags=["processes"],
)