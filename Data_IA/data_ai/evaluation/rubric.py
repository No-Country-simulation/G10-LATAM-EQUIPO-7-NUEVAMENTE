"""Definición de la rúbrica matemática del reviewer.

Los umbrales y reglas de negocio determinan si un contenido generado
es aprobado, rechazado o requiere revisión humana.
"""
from typing import List, Tuple
from schemas.evaluation import RubricaEvaluacion

# Criterios oficiales actualizados para el Sprint 2
REVIEW_DIMENSIONS = (
    "relevancia",
    "coherencia",
    "adaptacion_didactica",
    "informacion_respaldada",
)

def calcular_veredicto_evaluacion(scores: RubricaEvaluacion, informacion_no_respaldada: bool) -> Tuple[str, List[str]]:
    """
    Calcula el estado final de un formato generado basado en su rúbrica.

    Args:
        scores (RubricaEvaluacion): Puntajes de 1 a 5 para los criterios definidos.
        informacion_no_respaldada (bool): Flag que indica posible alucinación.

    Returns:
        Tuple[str, List[str]]: Status ('aprobado', 'requiere_revision', 'rechazado') y observaciones.
    """
    observaciones = []
    
    lista_puntajes = [
        scores.relevancia, 
        scores.coherencia, 
        scores.adaptacion_didactica, 
        scores.informacion_respaldada
    ]

    # Regla 1: Rechazo si hay puntajes críticos (1 o 2)
    if any(p <= 2 for p in lista_puntajes):
        observaciones.append("Rechazado: Uno o más criterios no superan el puntaje mínimo aceptable (<=2).")
        return "rechazado", observaciones

    # Regla 2: Requiere revisión por posible alucinación
    if informacion_no_respaldada:
        observaciones.append("Requiere revisión: Se detectó información no respaldada en los chunks originales.")
    
    # Regla 3: Requiere revisión por puntajes regulares (3)
    if any(p == 3 for p in lista_puntajes):
        observaciones.append("Requiere revisión: Existen criterios con puntaje regular (3) que deben mejorarse.")

    if observaciones:
        return "requiere_revision", observaciones

    # Regla 4: Aprobado (Puntajes >= 4 y sin alucinaciones)
    observaciones.append("Aprobado: El contenido cumple con altos estándares de calidad.")
    return "aprobado", observaciones