"""Contratos para evaluación del JSON final y salida del reviewer."""

from pydantic import BaseModel, Field


class ReviewScores(BaseModel):
    fidelity: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    coherence: float = Field(ge=0.0, le=1.0)
    pedagogical_fit: float | None = Field(default=None, ge=0.0, le=1.0)


class ReviewResult(BaseModel):
    status: str
    scores: ReviewScores
    unsupported_information: bool
    observations: list[str] = Field(default_factory=list)
