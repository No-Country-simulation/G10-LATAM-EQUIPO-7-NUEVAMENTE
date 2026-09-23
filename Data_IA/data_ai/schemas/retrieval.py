"""Contratos para resultados de retrieval recibidos desde Agentes."""

from typing import Any
from pydantic import BaseModel, Field


class RetrievalItem(BaseModel):
    """Un chunk recuperado por el pipeline de Agentes."""

    chunk_id: str
    document_id: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    """Respuesta de retrieval consumida por Data/IA para evaluación."""

    case_id: str | None = None
    query: str
    top_k: int = Field(gt=0)
    results: list[RetrievalItem]
