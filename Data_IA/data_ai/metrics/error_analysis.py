"""Utilidades para clasificar y documentar errores de retrieval.

La primera versión se mantiene intencionalmente simple.
"""


def classify_retrieval_failure(recall_at_5: float) -> str:
    """Clasifica un caso según su Recall@5."""
    if recall_at_5 == 0:
        return "sin_evidencia_relevante_en_top5"
    if recall_at_5 < 1:
        return "evidencia_parcial"
    return "recuperacion_completa"
