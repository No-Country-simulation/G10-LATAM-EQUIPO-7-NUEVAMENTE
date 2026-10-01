from pydantic import BaseModel
from typing import List, Optional

class GenerationContext(BaseModel):
    profile: str
    niche: str
    detail_level: str
    learning_objective: Optional[str] = None

class RubricaEvaluacion(BaseModel):
    relevancia: int
    coherencia: int
    adaptacion_didactica: int
    informacion_respaldada: int

class EvaluacionReviewerContract(BaseModel):
    status: str
    scores: RubricaEvaluacion
    informacion_no_respaldada: bool
    observaciones: List[str]