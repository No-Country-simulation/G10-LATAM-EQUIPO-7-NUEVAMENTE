"""Servicio de evaluación del resultado generado.

Este módulo orquesta la revisión del contenido generado, asegurando que las
integraciones externas se mantengan desacopladas (sin llamadas directas a LLMs).
Se encarga exclusivamente de recibir los parámetros, delegar el cálculo del veredicto
y ensamblar el contrato de salida validado.
"""
from typing import Dict, Any, List
from data_ai.schemas.evaluation import EvaluacionReviewerContract
from data_ai.schemas.format_evaluation import EvaluationScores
from data_ai.evaluation.rubric import calcular_veredicto_evaluacion

def evaluar_contenido(
    document_id: str, 
    formato: str, 
    generated_content: Dict[str, Any], 
    chunks_used: List[Dict[str, Any]],
    scores_evaluacion: EvaluationScores,
    informacion_no_respaldada: bool
) -> EvaluacionReviewerContract:
    """
    Controlador principal que procesa la evaluación del contenido generado y 
    retorna el JSON estructurado final.

    Args:
        document_id (str): Identificador único del documento origen.
        formato (str): Tipo de formato evaluado (ej. 'quiz', 'flashcards').
        generated_content (Dict[str, Any]): El contenido educativo generado por el agente.
        chunks_used (List[Dict[str, Any]]): Fragmentos de texto utilizados como contexto.
        scores_evaluacion (EvaluationScores): Puntajes (1-5) asignados a las dimensiones de calidad.
        informacion_no_respaldada (bool): Flag que indica si el LLM generó información sin respaldo.

    Returns:
        EvaluacionReviewerContract: Un objeto validado que contiene el estado final 
        ('aprobado', 'requiere_revision', 'rechazado'), los puntajes y la lista de observaciones.
    """
    # 1. Delegar la evaluación matemática a la rúbrica
    status, observaciones = calcular_veredicto_evaluacion(scores_evaluacion, informacion_no_respaldada)
    
    # 2. Ensamblar y retornar el contrato canónico estructurado
    return EvaluacionReviewerContract(
        status=status,
        scores=scores_evaluacion,
        informacion_no_respaldada=informacion_no_respaldada,
        observaciones=observaciones
    )