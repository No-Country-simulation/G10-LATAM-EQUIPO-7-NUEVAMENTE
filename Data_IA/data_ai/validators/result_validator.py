"""Validación estructural de resultados recibidos por Data/IA."""

from data_ai.schemas.retrieval import RetrievalResponse


def validate_retrieval_payload(payload: dict) -> RetrievalResponse:
    """Valida y normaliza la respuesta de retrieval de Agentes."""
    return RetrievalResponse.model_validate(payload)
