from pydantic import BaseModel, Field
from typing import List, Literal

class RubricaEvaluacion(BaseModel):
    """
    Puntajes de la rúbrica de evaluación pedagógica y técnica. 
    Todos los scores usan una escala del 1 al 5.
    """
    fidelidad: int = Field(..., ge=1, le=5, description="1=Inventa todo, 5=Estrictamente basado en contexto.")
    relevancia: int = Field(..., ge=1, le=5, description="1=No responde la pregunta, 5=Respuesta directa y útil.")
    coherencia: int = Field(..., ge=1, le=5, description="1=Incomprensible, 5=Redacción perfecta y lógica.")
    adaptacion_didactica: int = Field(..., ge=1, le=5, description="1=Tono incorrecto, 5=Adaptación perfecta al público.")
    informacion_no_respaldada: bool = Field(..., description="True si se detectan alucinaciones o datos inventados.")

class EvaluacionReviewerContract(BaseModel):
    """
    Contrato explícito de la salida estructurada del Agente Revisor.
    Reglas de status:
    - 'aprobado': Todos los scores >= 4 y informacion_no_respaldada = False.
    - 'requiere_revision': Algún score = 3.
    - 'rechazado': Algún score <= 2 o informacion_no_respaldada = True.
    """
    status: Literal["aprobado", "rechazado", "requiere_revision"] = Field(..., description="Estado final basado en los scores.")
    scores: RubricaEvaluacion = Field(..., description="Estructura anidada con las 5 métricas de la rúbrica.")
    observaciones: List[str] = Field(..., description="Lista de comentarios obligatorios si no es 'aprobado'.")