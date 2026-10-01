"""Servicio de evaluación del resultado generado.

Este módulo orquesta la revisión del contenido generado, asegurando que las
integraciones externas se mantengan desacopladas (sin llamadas directas a LLMs).
"""
from typing import Dict, Any, List
from data_ai.schemas.evaluation import EvaluacionReviewerContract
from data_ai.evaluation.rubric import calcular_veredicto_evaluacion
from data_ai.evaluation.quality_evaluator import evaluate

def evaluar_contenido(
    document_id: str, 
    formato: str, 
    generated_content: Dict[str, Any], 
    chunks_used: List[Dict[str, Any]],
    generation_context: Dict[str, Any]
) -> EvaluacionReviewerContract:
    """
    Controlador principal que procesa la evaluación del contenido generado y 
    retorna el JSON estructurado final.
    """
    # 1. Calcular scores reales y detectar alucinaciones usando el texto y los chunks
    scores_evaluacion, info_no_respaldada = evaluate(
        generated_content, 
        chunks_used, 
        generation_context
    )

    # 2. Delegar la evaluación matemática a la rúbrica para obtener el status
    status, observaciones = calcular_veredicto_evaluacion(scores_evaluacion, info_no_respaldada)
    
    # 3. Ensamblar y retornar el contrato canónico estructurado
    return EvaluacionReviewerContract(
        status=status,
        scores=scores_evaluacion,
        informacion_no_respaldada=info_no_respaldada,
        observaciones=observaciones
    )