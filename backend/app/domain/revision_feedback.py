"""Value objects de feedback pedagógico compatible con Evaluation V2.

No conoce HTTP, LangGraph ni las rutas externas de Data/IA. La integración
Data/IA V2 podrá construir estos objetos sin importar sus schemas públicos.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

Dimension = Literal["relevance", "coherence", "didactic_adaptation", "content_support"]
Severity = Literal["low", "medium", "high"]
SemanticStatus = Literal["success", "failed", "unavailable"]
RevisionVerdict = Literal["requires_revision", "rejected"]

_DIMENSIONS = frozenset(("relevance", "coherence", "didactic_adaptation", "content_support"))
_SEVERITIES = frozenset(("low", "medium", "high"))
_ERROR_CODES = frozenset(("timeout", "provider_error", "invalid_output", "not_configured"))


@dataclass(frozen=True, slots=True)
class FeedbackScores:
    """Puntajes 1–5, heurísticos o semánticos; sin agregación artificial."""

    relevance: float
    coherence: float
    didactic_adaptation: float
    content_support: float

    def __post_init__(self) -> None:
        if any(
            not isfinite(value) or not 1 <= value <= 5
            for value in (
                self.relevance,
                self.coherence,
                self.didactic_adaptation,
                self.content_support,
            )
        ):
            raise ValueError("Los puntajes deben ser finitos y estar entre 1 y 5.")


@dataclass(frozen=True, slots=True)
class RevisionObservation:
    """Problema de calidad localizado, producido por Data/IA."""

    dimension: Dimension
    severity: Severity
    message: str
    item_id: str | None = None

    def __post_init__(self) -> None:
        if self.dimension not in _DIMENSIONS or self.severity not in _SEVERITIES:
            raise ValueError("Dimensión o severidad de observación inválida.")
        if not self.message.strip():
            raise ValueError("La observación debe incluir un mensaje.")


@dataclass(frozen=True, slots=True)
class RevisionRecommendation:
    """Acción de mejora sugerida para el redactor."""

    dimension: Dimension
    message: str
    item_id: str | None = None

    def __post_init__(self) -> None:
        if self.dimension not in _DIMENSIONS or not self.message.strip():
            raise ValueError("Recomendación inválida.")


@dataclass(frozen=True, slots=True)
class UnsupportedClaim:
    """Afirmación no respaldada y sus referencias documentales."""

    claim: str
    reason: str
    item_id: str | None = None
    related_chunk_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.claim.strip() or not self.reason.strip():
            raise ValueError("La afirmación requiere claim y reason.")
        if any(not chunk_id.strip() for chunk_id in self.related_chunk_ids):
            raise ValueError("related_chunk_ids no puede contener identificadores vacíos.")


@dataclass(frozen=True, slots=True)
class SemanticReview:
    """Resultado semántico íntegro, incluido estado técnico de degradación."""

    status: SemanticStatus
    scores: FeedbackScores | None = None
    observations: tuple[RevisionObservation, ...] = ()
    recommendations: tuple[RevisionRecommendation, ...] = ()
    unsupported_information: tuple[UnsupportedClaim, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None

    def __post_init__(self) -> None:
        if self.status == "success":
            if self.scores is None or self.error_code is not None:
                raise ValueError("Semántica success requiere scores y no admite error_code.")
        elif self.status == "failed":
            if self.scores is not None or self.error_code not in _ERROR_CODES - {
                "not_configured"
            }:
                raise ValueError("Semántica failed requiere un error_code de fallo válido.")
        elif self.status == "unavailable":
            if self.scores is not None or self.error_code != "not_configured":
                raise ValueError("Semántica unavailable requiere not_configured sin scores.")
        else:
            raise ValueError("Estado semántico desconocido.")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms debe ser no negativo.")


@dataclass(frozen=True, slots=True)
class RevisionFeedback:
    """Evaluación V2 normalizada; solo veredictos que admiten corrección."""

    verdict: RevisionVerdict
    heuristic_scores: FeedbackScores | None
    semantic_evaluation: SemanticReview

    def __post_init__(self) -> None:
        if self.verdict not in ("requires_revision", "rejected"):
            raise ValueError("Solo se puede revisar un formato con veredicto negativo.")
        semantic = self.semantic_evaluation
        if not (
            semantic.observations
            or semantic.recommendations
            or semantic.unsupported_information
        ):
            raise ValueError("La revisión requiere feedback accionable de Data/IA.")
