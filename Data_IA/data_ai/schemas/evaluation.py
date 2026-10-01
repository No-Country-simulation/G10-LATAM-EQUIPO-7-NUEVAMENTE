from typing import List, Literal

from pydantic import BaseModel

from data_ai.schemas.format_evaluation import EvaluationScores


class EvaluacionReviewerContract(BaseModel):
    """
    Contrato interno de salida del reviewer.
    """

    status: Literal[
        "aprobado",
        "requiere_revision",
        "rechazado",
    ]

    scores: EvaluationScores

    informacion_no_respaldada: bool

    observaciones: List[str]
