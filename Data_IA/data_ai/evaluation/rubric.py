"""Reglas de decisión para la evaluación de calidad."""

from typing import List, Tuple

from data_ai.schemas.format_evaluation import EvaluationScores


REVIEW_DIMENSIONS = (
    "relevancia",
    "coherencia",
    "adaptacion_didactica",
    "informacion_respaldada",
)


def calcular_veredicto_evaluacion(
    scores: EvaluationScores,
    informacion_no_respaldada: bool,
) -> Tuple[str, List[str]]:
    """
    Calcula el veredicto final a partir de los scores de evaluación.

    Reglas:
    - informacion_no_respaldada=True -> rechazado
    - cualquier score <= 2 -> rechazado
    - cualquier score == 3 -> requiere_revision
    - todos los scores >= 4 -> aprobado
    """

    observaciones: List[str] = []

    lista_puntajes = [
        scores.relevancia,
        scores.coherencia,
        scores.adaptacion_didactica,
        scores.informacion_respaldada,
    ]

    if informacion_no_respaldada:
        observaciones.append(
            "Rechazado: Se detectó información no respaldada "
            "en los chunks originales."
        )
        return "rechazado", observaciones

    if any(puntaje <= 2 for puntaje in lista_puntajes):
        observaciones.append(
            "Rechazado: Uno o más criterios no superan "
            "el puntaje mínimo aceptable (<=2)."
        )
        return "rechazado", observaciones

    if any(puntaje == 3 for puntaje in lista_puntajes):
        observaciones.append(
            "Requiere revisión: Existen criterios con "
            "puntaje regular (3) que deben mejorarse."
        )
        return "requiere_revision", observaciones

    observaciones.append(
        "Aprobado: El contenido cumple con altos estándares de calidad."
    )

    return "aprobado", observaciones
