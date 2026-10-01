from typing import List, Tuple
# Importación absoluta solicitada por Tara
from data_ai.schemas.format_evaluation import EvaluationScores

REVIEW_DIMENSIONS = (
    "relevancia",
    "coherencia",
    "adaptacion_didactica",
    "informacion_respaldada",
)

def calcular_veredicto_evaluacion(scores: EvaluationScores, informacion_no_respaldada: bool) -> Tuple[str, List[str]]:
    observaciones = []
    
    lista_puntajes = [
        scores.relevancia, 
        scores.coherencia, 
        scores.adaptacion_didactica, 
        scores.informacion_respaldada
    ]

    # Rechazo automático por alucinación
    if informacion_no_respaldada:
        observaciones.append("Rechazado: Se detectó información no respaldada en los chunks originales.")
        return "rechazado", observaciones

    # Rechazo por puntajes críticos (1 o 2)
    if any(p <= 2 for p in lista_puntajes):
        observaciones.append("Rechazado: Uno o más criterios no superan el puntaje mínimo aceptable (<=2).")
        return "rechazado", observaciones
    
    # Requiere revisión por puntajes regulares (3)
    if any(p == 3 for p in lista_puntajes):
        observaciones.append("Requiere revisión: Existen criterios con puntaje regular (3) que deben mejorarse.")
        return "requiere_revision", observaciones

    # Aprobado
    observaciones.append("Aprobado: El contenido cumple con altos estándares de calidad.")
    return "aprobado", observaciones