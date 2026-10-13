"""Schemas internos para la evaluación semántica de Data/IA.

Este módulo define las estructuras utilizadas por el Semantic Evaluator
durante Sprint 4.

Principios principales:
- Los scores semánticos se mantienen separados de los heurísticos.
- El estado técnico del evaluador semántico no equivale al veredicto
  pedagógico final del contenido.
- `success` requiere scores válidos.
- `failed` y `unavailable` no deben contener scores.
- Las observaciones y recomendaciones son estructuradas y accionables.
- La evidencia factual se rastrea mediante `UnsupportedClaim`.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SemanticDimension = Literal[
    "relevance",
    "coherence",
    "didactic_adaptation",
    "content_support",
]


SemanticSeverity = Literal[
    "low",
    "medium",
    "high",
]


SemanticStatus = Literal[
    "success",
    "failed",
    "unavailable",
]


SemanticErrorCode = Literal[
    "timeout",
    "provider_error",
    "invalid_output",
    "not_configured",
]


class SemanticScores(BaseModel):
    """Scores semánticos para las cuatro dimensiones de evaluación.

    Cada dimensión utiliza una escala de 1.0 a 5.0.

    Estos valores representan calidad semántica del contenido,
    no confianza estadística del modelo.
    """

    relevance: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Nivel de alineación del contenido con el objetivo de "
            "aprendizaje y el nicho solicitado."
        ),
    )

    coherence: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Nivel de coherencia interna, consistencia y progresión "
            "lógica del contenido."
        ),
    )

    didactic_adaptation: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Nivel de adecuación del contenido al perfil y nivel de "
            "detalle solicitados."
        ),
    )

    content_support: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description=(
            "Nivel de respaldo factual del contenido respecto de los "
            "chunks utilizados como evidencia."
        ),
    )


class SemanticObservation(BaseModel):
    """Hallazgo semántico detectado durante la evaluación."""

    dimension: SemanticDimension = Field(
        ...,
        description=(
            "Dimensión de evaluación afectada por el hallazgo."
        ),
    )

    severity: SemanticSeverity = Field(
        ...,
        description=(
            "Severidad del problema detectado."
        ),
    )

    message: str = Field(
        ...,
        min_length=1,
        description=(
            "Descripción concreta y comprensible del problema."
        ),
    )

    item_id: str | None = Field(
        default=None,
        description=(
            "Identificador opcional del elemento afectado, por ejemplo "
            "question_id, card_id o scene_id."
        ),
    )


class SemanticRecommendation(BaseModel):
    """Recomendación accionable derivada de un hallazgo semántico."""

    dimension: SemanticDimension = Field(
        ...,
        description=(
            "Dimensión a la que corresponde la recomendación."
        ),
    )

    message: str = Field(
        ...,
        min_length=1,
        description=(
            "Acción concreta sugerida para corregir o mejorar "
            "el contenido."
        ),
    )

    item_id: str | None = Field(
        default=None,
        description=(
            "Identificador opcional del elemento al que aplica la "
            "recomendación."
        ),
    )


class UnsupportedClaim(BaseModel):
    """Afirmación factual que no está suficientemente respaldada."""

    claim: str = Field(
        ...,
        min_length=1,
        description=(
            "Afirmación problemática detectada dentro del contenido "
            "generado."
        ),
    )

    reason: str = Field(
        ...,
        min_length=1,
        description=(
            "Explicación de por qué la afirmación no está respaldada "
            "por los chunks disponibles."
        ),
    )

    item_id: str | None = Field(
        default=None,
        description=(
            "Identificador opcional del elemento donde aparece la "
            "afirmación."
        ),
    )

    related_chunk_ids: list[str] = Field(
        default_factory=list,
        description=(
            "IDs opcionales de chunks relacionados con la afirmación."
        ),
    )


class SemanticEvaluationResult(BaseModel):
    """Resultado completo del evaluador semántico.

    `status` representa el estado técnico de ejecución del evaluador,
    no el veredicto final del contenido.

    Reglas:
    - success -> scores obligatorios
    - failed -> scores deben ser None
    - unavailable -> scores deben ser None
    """

    status: SemanticStatus = Field(
        ...,
        description=(
            "Estado técnico de la evaluación semántica."
        ),
    )

    scores: SemanticScores | None = Field(
        default=None,
        description=(
            "Scores semánticos. Deben existir únicamente cuando "
            "status='success'."
        ),
    )

    observations: list[SemanticObservation] = Field(
        default_factory=list,
        description=(
            "Hallazgos relevantes detectados durante la evaluación."
        ),
    )

    recommendations: list[SemanticRecommendation] = Field(
        default_factory=list,
        description=(
            "Recomendaciones accionables derivadas de los hallazgos."
        ),
    )

    unsupported_information: list[UnsupportedClaim] = Field(
        default_factory=list,
        description=(
            "Afirmaciones factuales detectadas como no respaldadas."
        ),
    )

    error_code: SemanticErrorCode | None = Field(
        default=None,
        description=(
            "Código técnico del error cuando la evaluación falla "
            "o no está disponible."
        ),
    )

    error_message: str | None = Field(
        default=None,
        description=(
            "Descripción técnica opcional del error."
        ),
    )

    model: str | None = Field(
        default=None,
        description=(
            "Modelo utilizado para la evaluación semántica."
        ),
    )

    prompt_version: str | None = Field(
        default=None,
        description=(
            "Versión del prompt utilizado por el evaluador semántico."
        ),
    )

    latency_ms: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Duración de la evaluación semántica en milisegundos."
        ),
    )

    @model_validator(mode="after")
    def validate_status_consistency(
        self,
    ) -> "SemanticEvaluationResult":
        """Valida coherencia entre status, scores y error_code."""

        if self.status == "success":
            if self.scores is None:
                raise ValueError(
                    "Semantic evaluation with status='success' "
                    "must include scores."
                )

            if self.error_code is not None:
                raise ValueError(
                    "Semantic evaluation with status='success' "
                    "must not include error_code."
                )

        elif self.status == "failed":
            if self.scores is not None:
                raise ValueError(
                    "Semantic evaluation with status='failed' "
                    "must not include scores."
                )

            if self.error_code is None:
                raise ValueError(
                    "Semantic evaluation with status='failed' "
                    "must include error_code."
                )

            if self.error_code == "not_configured":
                raise ValueError(
                    "error_code='not_configured' must use "
                    "status='unavailable'."
                )

        elif self.status == "unavailable":
            if self.scores is not None:
                raise ValueError(
                    "Semantic evaluation with status='unavailable' "
                    "must not include scores."
                )

            if self.error_code != "not_configured":
                raise ValueError(
                    "Semantic evaluation with status='unavailable' "
                    "must use error_code='not_configured'."
                )

        return self