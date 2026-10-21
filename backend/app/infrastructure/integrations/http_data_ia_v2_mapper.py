"""Valida y normaliza el contrato HTTP /evaluate/v2 hacia el puerto Data/IA.

El adaptador HTTP es responsable solo de transporte. Este módulo valida la
estructura, traduce objetos semánticos al dominio y preserva ambas señales
(heurística y semántica) sin calcular métricas ni veredictos nuevos.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import GeneratedFormatType
from app.domain.format_evaluation import (
    EvaluationVerdict,
    HeuristicScoresV2,
    SemanticEvaluationResult,
    SemanticObservation,
    SemanticRecommendation,
    SemanticScores,
    UnsupportedClaim,
)
from app.ports.data_ia_port import DataIAV2EvaluationResult


class _Scores(BaseModel):
    """Cuatro dimensiones de calidad (escala numérica 1.0–5.0)."""

    model_config = ConfigDict(extra="forbid")

    relevance: float = Field(ge=1.0, le=5.0)
    coherence: float = Field(ge=1.0, le=5.0)
    didactic_adaptation: float = Field(ge=1.0, le=5.0)
    content_support: float = Field(ge=1.0, le=5.0)


class _Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: Literal[
        "relevance", "coherence", "didactic_adaptation", "content_support"
    ]
    severity: Literal["low", "medium", "high"]
    message: str = Field(min_length=1)
    item_id: str | None = None


class _Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: Literal[
        "relevance", "coherence", "didactic_adaptation", "content_support"
    ]
    message: str = Field(min_length=1)
    item_id: str | None = None


class _UnsupportedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    item_id: str | None = None
    related_chunk_ids: list[str] = Field(default_factory=list)


class _SemanticEvaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["success", "failed", "unavailable"]
    scores: _Scores | None = None
    observations: list[_Observation] = Field(default_factory=list)
    recommendations: list[_Recommendation] = Field(default_factory=list)
    unsupported_information: list[_UnsupportedClaim] = Field(default_factory=list)
    error_code: Literal[
        "timeout", "provider_error", "invalid_output", "not_configured"
    ] | None = None
    error_message: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_consistency(self) -> "_SemanticEvaluation":
        """Comprueba coherencia entre estado, scores y error técnico."""
        if self.status == "success":
            if self.scores is None or self.error_code is not None:
                raise ValueError("semantic success requiere scores sin error_code")
        elif self.status == "failed":
            if self.scores is not None or self.error_code not in (
                "timeout", "provider_error", "invalid_output"
            ):
                raise ValueError(
                    "semantic failed requiere error_code válido y sin scores"
                )
        elif self.scores is not None or self.error_code != "not_configured":
            raise ValueError("semantic unavailable requiere not_configured sin scores")
        return self


class _EvaluationResponseV2(BaseModel):
    """Contrato público de Data/IA; rechazo explícito de V1 en ruta V2."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(min_length=1)
    format: GeneratedFormatType
    verdict: EvaluationVerdict | None = None
    heuristic_scores: _Scores | None = None
    semantic_evaluation: _SemanticEvaluation
    evaluator_version: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_verdict(self) -> "_EvaluationResponseV2":
        """Sin señal heurística ni semántica válida no existe veredicto."""
        has_signal = (
            self.heuristic_scores is not None
            or self.semantic_evaluation.status == "success"
        )
        if not has_signal and self.verdict is not None:
            raise ValueError("verdict debe ser null cuando no existen señales")
        return self


def parse_evaluation_v2(payload: object) -> DataIAV2EvaluationResult:
    """Convierte JSON V2 a tipos de dominio. Propaga ValidationError.

    Args:
        payload: objeto JSON decodificado del response HTTP.
    Returns:
        Evaluación V2 independiente de HTTP y lista para persistir.
    """
    response = _EvaluationResponseV2.model_validate(payload)
    semantic = response.semantic_evaluation

    semantic_scores = (
        SemanticScores(**semantic.scores.model_dump())
        if semantic.scores is not None
        else None
    )
    semantic_domain = SemanticEvaluationResult(
        status=semantic.status,
        scores=semantic_scores,
        observations=tuple(
            SemanticObservation(**item.model_dump()) for item in semantic.observations
        ),
        recommendations=tuple(
            SemanticRecommendation(**item.model_dump())
            for item in semantic.recommendations
        ),
        unsupported_information=tuple(
            UnsupportedClaim(
                claim=item.claim,
                reason=item.reason,
                item_id=item.item_id,
                related_chunk_ids=tuple(item.related_chunk_ids),
            )
            for item in semantic.unsupported_information
        ),
        error_code=semantic.error_code,
        error_message=semantic.error_message,
        model=semantic.model,
        prompt_version=semantic.prompt_version,
        latency_ms=semantic.latency_ms,
    )
    heuristic_scores = (
        HeuristicScoresV2(**response.heuristic_scores.model_dump())
        if response.heuristic_scores is not None
        else None
    )
    return DataIAV2EvaluationResult(
        document_id=response.document_id,
        format_type=response.format,
        verdict=response.verdict,
        heuristic_scores=heuristic_scores,
        semantic_evaluation=semantic_domain,
        evaluator_version=response.evaluator_version,
        rubric_version=response.rubric_version,
    )
