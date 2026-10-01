from typing import List, Tuple
from schemas.format_evaluation import EvaluationScores

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

    # Ajuste Tara: Rechazo automático por alucinación
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


# --- Tests directos de la rúbrica ---
if __name__ == "__main__":
    print("Ejecutando tests de validación de rúbrica...")
    
    # Test 1: Aprobación
    s1 = EvaluationScores(relevancia=5, coherencia=4, adaptacion_didactica=4, informacion_respaldada=5)
    assert calcular_veredicto_evaluacion(s1, False)[0] == "aprobado"
    
    # Test 2: Alucinación -> Rechazado
    s2 = EvaluationScores(relevancia=5, coherencia=5, adaptacion_didactica=5, informacion_respaldada=5)
    assert calcular_veredicto_evaluacion(s2, True)[0] == "rechazado"
    
    # Test 3: Score <= 2 -> Rechazado
    s3 = EvaluationScores(relevancia=5, coherencia=4, adaptacion_didactica=2, informacion_respaldada=5)
    assert calcular_veredicto_evaluacion(s3, False)[0] == "rechazado"
    
    # Test 4: Score 3 -> Requiere revisión
    s4 = EvaluationScores(relevancia=5, coherencia=3, adaptacion_didactica=4, informacion_respaldada=5)
    assert calcular_veredicto_evaluacion(s4, False)[0] == "requiere_revision"
    
    print("Todos los tests de sincronización con EvaluationResponse pasaron con éxito.")