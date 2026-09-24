"""Servicio de evaluación del resultado generado.

Este módulo NO llama directamente a proveedores de IA.
La integración externa debe mantenerse desacoplada.
"""

from data_ai.schemas.evaluation import ReviewResult


def validate_review_result(payload: dict) -> ReviewResult:
    """Valida la salida estructurada producida por un reviewer externo."""
    return ReviewResult.model_validate(payload)
