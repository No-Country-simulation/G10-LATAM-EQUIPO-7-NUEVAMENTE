from typing import List, Literal
from pydantic import BaseModel

from .format_evaluation import (
    EvaluationScores,
    GenerationContext,
)

class EvaluacionReviewerContract(BaseModel):
    status: Literal[
        "aprobado",
        "requiere_revision",
        "rechazado",
    ]
    scores: EvaluationScores
    informacion_no_respaldada: bool
    observaciones: List[str]