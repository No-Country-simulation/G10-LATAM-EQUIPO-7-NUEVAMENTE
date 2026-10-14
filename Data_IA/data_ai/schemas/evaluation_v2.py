"""Schemas públicos propuestos para Evaluation Contract V2.

Este módulo representa el contrato acordado entre Data/IA y BackendAPI
durante Sprint 4.

Importante:
- todavía no sustituye el response actual de POST /evaluate;
- permite implementar y probar V2 sin romper compatibilidad;
- SemanticEvaluationResult permanece anidado;
- heuristic_scores y semantic scores permanecen separados;
- no existe final_score ni ponderación;
- verdict puede ser None cuando no fue posible evaluar de forma confiable.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
)


EvaluationVerdict = Literal[
    "approved",
    "requires_revision",
    "rejected",
]


class HeuristicScoresV2(BaseModel):
    """Scores heurísticos expuestos por Evaluation Contract V2.

    Los nombres externos utilizan el vocabulario técnico canónico
    acordado para Sprint 4.

    La traducción desde los nombres internos actuales del evaluator V1.1
    se realizará en la capa de integración.
    """

    relevance: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Score heurístico de relevancia respecto del objetivo "
            "de aprendizaje."
        ),
    )

    coherence: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Score heurístico de coherencia interna."
        ),
    )

    didactic_adaptation: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Score heurístico de adaptación pedagógica."
        ),
    )

    content_support: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Score heurístico de respaldo factual."
        ),
    )


class EvaluationResponseV2(BaseModel):
    """Respuesta pública propuesta de Data/IA hacia BackendAPI.

    `verdict` representa el resultado pedagógico global.

    `semantic_evaluation.status` representa únicamente el estado técnico
    del componente semántico.

    Los scores heurísticos y semánticos permanecen separados.
    """

    document_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Identificador del documento evaluado."
        ),
    )

    format: Literal[
        "quiz",
        "flashcards",
        "tldr",
        "video_script",
    ] = Field(
        ...,
        description=(
            "Formato pedagógico del contenido evaluado."
        ),
    )

    verdict: EvaluationVerdict | None = Field(
        default=None,
        description=(
            "Veredicto pedagógico global. Puede ser None cuando "
            "Data/IA no dispone de señales suficientes para evaluar "
            "el contenido de forma confiable."
        ),
    )

    heuristic_scores: HeuristicScoresV2 | None = Field(
        default=None,
        description=(
            "Scores producidos por el evaluador heurístico. "
            "Pueden ser None si dicho evaluador no logró producir "
            "una evaluación válida."
        ),
    )

    semantic_evaluation: SemanticEvaluationResult = Field(
        ...,
        description=(
            "Resultado técnico y pedagógico del Semantic Evaluator."
        ),
    )

    evaluator_version: str = Field(
        ...,
        min_length=1,
        description=(
            "Versión del evaluador Data/IA."
        ),
    )

    rubric_version: str = Field(
        ...,
        min_length=1,
        description=(
            "Versión de la rúbrica utilizada."
        ),
    )

    @model_validator(mode="after")
    def validate_evaluation_consistency(
        self,
    ) -> "EvaluationResponseV2":
        """Evita publicar un verdict cuando no existe evaluación válida.

        Reglas iniciales:
        - si existe heuristic_scores, puede existir verdict incluso cuando
          semantic_evaluation falló o no está disponible;
        - si el semántico tuvo success, también existe una señal válida;
        - si no existe heurístico y el semántico no tuvo success,
          verdict debe ser None.

        La lógica que CALCULA el verdict no pertenece a este schema.
        """

        has_heuristic_signal = (
            self.heuristic_scores is not None
        )

        has_semantic_signal = (
            self.semantic_evaluation.status == "success"
        )

        has_valid_signal = (
            has_heuristic_signal
            or has_semantic_signal
        )

        if (
            not has_valid_signal
            and self.verdict is not None
        ):
            raise ValueError(
                "verdict must be None when neither heuristic "
                "nor semantic evaluation produced a valid signal."
            )

        return self