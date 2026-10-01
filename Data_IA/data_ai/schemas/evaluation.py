from pydantic import BaseModel, Field
from typing import List, Literal

# 1. Reutilizamos el modelo canónico de Mafe (asumiendo que está en la misma carpeta)
from .format_evaluation import GenerationContext 

class RubricaEvaluacion(BaseModel):
    # 2. Restringimos los puntajes estrictamente al rango 1-5
    relevancia: int = Field(ge=1, le=5, description="Puntaje del 1 al 5")
    coherencia: int = Field(ge=1, le=5, description="Puntaje del 1 al 5")
    adaptacion_didactica: int = Field(ge=1, le=5, description="Puntaje del 1 al 5")
    informacion_respaldada: int = Field(ge=1, le=5, description="Puntaje del 1 al 5")

class EvaluacionReviewerContract(BaseModel):
    # 3. Restringimos el status solo a los 3 estados permitidos oficialmente
    status: Literal["aprobado", "requiere_revision", "rechazado"]
    scores: RubricaEvaluacion
    informacion_no_respaldada: bool
    observaciones: List[str]