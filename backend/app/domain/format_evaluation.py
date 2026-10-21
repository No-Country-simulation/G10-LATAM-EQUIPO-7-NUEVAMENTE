"""Entidades asociadas a evaluaciones realizadas por Data/IA.

Este módulo conserva el contrato V1 (heurístico, Evaluator 1.1) y agrega
el contrato V2 acordado para Sprint 4 (``verdict`` + ``heuristic_scores``
+ ``semantic_evaluation``), reutilizando la misma entidad ``FormatEvaluation``
y el mismo repositorio para ambas versiones.

``FormatEvaluation`` no exige que estén presentes los campos de ambas
versiones a la vez: una evaluación persistida antes de Sprint 4 solo trae
los campos V1; una evaluación V2 puede dejar los campos V1 vacíos. Lo único
obligatorio es que exista al menos una señal real de evaluación (V1 o V2).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from app.domain.enums import (
    FormatEvaluationStatus,
)

# ---------------------------------------------------------------------------
# V1 (Evaluator heurístico 1.1) — sin modificar
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvaluationScores:
    """Puntajes heurísticos V1 emitidos por Data/IA (enteros 1-5)."""

    relevance: int
    coherence: int
    didactic_adaptation: int
    content_support: int

    def __post_init__(self) -> None:
        values = (
            self.relevance,
            self.coherence,
            self.didactic_adaptation,
            self.content_support,
        )

        if any(
            value < 1 or value > 5
            for value in values
        ):
            raise ValueError(
                "Todos los scores deben estar entre 1 y 5."
            )


# ---------------------------------------------------------------------------
# V2 (Evaluation Contract V2, Sprint 4) — nuevo
#
# Reproduce 1:1 el contrato ya implementado por Data/IA en
# Data_IA/data_ai/schemas/evaluation_v2.py y semantic_evaluation.py.
# ---------------------------------------------------------------------------

EvaluationVerdict = Literal[
    "approved",
    "requires_revision",
    "rejected",
]

SemanticStatus = Literal[
    "success",
    "failed",
    "unavailable",
]

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

SemanticErrorCode = Literal[
    "timeout",
    "provider_error",
    "invalid_output",
    "not_configured",
]


def _validate_score_range(value: float, field_name: str) -> None:
    if value < 1.0 or value > 5.0:
        raise ValueError(
            f"{field_name} debe estar entre 1.0 y 5.0."
        )


@dataclass(frozen=True, slots=True)
class HeuristicScoresV2:
    """Scores heurísticos expuestos por Evaluation Contract V2 (float 1.0-5.0).

    Mismas cuatro dimensiones que ``EvaluationScores`` (V1), pero en punto
    flotante: el evaluador heurístico V2 ya no redondea a enteros.
    """

    relevance: float
    coherence: float
    didactic_adaptation: float
    content_support: float

    def __post_init__(self) -> None:
        _validate_score_range(self.relevance, "relevance")
        _validate_score_range(self.coherence, "coherence")
        _validate_score_range(
            self.didactic_adaptation, "didactic_adaptation"
        )
        _validate_score_range(self.content_support, "content_support")


@dataclass(frozen=True, slots=True)
class SemanticScores:
    """Scores del evaluador semántico (float 1.0-5.0, mismas 4 dimensiones)."""

    relevance: float
    coherence: float
    didactic_adaptation: float
    content_support: float

    def __post_init__(self) -> None:
        _validate_score_range(self.relevance, "relevance")
        _validate_score_range(self.coherence, "coherence")
        _validate_score_range(
            self.didactic_adaptation, "didactic_adaptation"
        )
        _validate_score_range(self.content_support, "content_support")


@dataclass(frozen=True, slots=True)
class SemanticObservation:
    """Hallazgo semántico detectado durante la evaluación."""

    dimension: SemanticDimension
    severity: SemanticSeverity
    message: str
    item_id: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError(
                "message no puede estar vacío."
            )


@dataclass(frozen=True, slots=True)
class SemanticRecommendation:
    """Recomendación accionable derivada de un hallazgo semántico."""

    dimension: SemanticDimension
    message: str
    item_id: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError(
                "message no puede estar vacío."
            )


@dataclass(frozen=True, slots=True)
class UnsupportedClaim:
    """Afirmación factual detectada como no respaldada por los chunks."""

    claim: str
    reason: str
    item_id: str | None = None
    related_chunk_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.claim.strip():
            raise ValueError(
                "claim no puede estar vacío."
            )

        if not self.reason.strip():
            raise ValueError(
                "reason no puede estar vacío."
            )


@dataclass(frozen=True, slots=True)
class SemanticEvaluationResult:
    """Resultado completo del evaluador semántico (Sprint 4).

    ``status`` representa el estado TÉCNICO de ejecución del evaluador
    semántico, no el veredicto pedagógico del contenido (eso lo expresa
    ``FormatEvaluation.verdict``).

    Reglas de consistencia (idénticas a Data/IA):
    - success -> ``scores`` obligatorio, ``error_code`` ausente.
    - failed -> ``scores`` ausente, ``error_code`` obligatorio
      (y distinto de ``not_configured``).
    - unavailable -> ``scores`` ausente, ``error_code`` debe ser
      ``not_configured``.
    """

    status: SemanticStatus
    scores: SemanticScores | None = None
    observations: tuple[SemanticObservation, ...] = ()
    recommendations: tuple[SemanticRecommendation, ...] = ()
    unsupported_information: tuple[UnsupportedClaim, ...] = ()
    error_code: SemanticErrorCode | None = None
    error_message: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None

    def __post_init__(self) -> None:
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError(
                "latency_ms no puede ser negativo."
            )

        if self.status == "success":
            if self.scores is None:
                raise ValueError(
                    "Una evaluación semántica 'success' debe incluir scores."
                )
            if self.error_code is not None:
                raise ValueError(
                    "Una evaluación semántica 'success' no debe incluir "
                    "error_code."
                )

        elif self.status == "failed":
            if self.scores is not None:
                raise ValueError(
                    "Una evaluación semántica 'failed' no debe incluir "
                    "scores."
                )
            if self.error_code is None:
                raise ValueError(
                    "Una evaluación semántica 'failed' debe incluir "
                    "error_code."
                )
            if self.error_code == "not_configured":
                raise ValueError(
                    "error_code='not_configured' debe usar "
                    "status='unavailable'."
                )

        elif self.status == "unavailable":
            if self.scores is not None:
                raise ValueError(
                    "Una evaluación semántica 'unavailable' no debe "
                    "incluir scores."
                )
            if self.error_code != "not_configured":
                raise ValueError(
                    "Una evaluación semántica 'unavailable' debe usar "
                    "error_code='not_configured'."
                )


# ---------------------------------------------------------------------------
# Entidad persistible (compartida entre V1 y V2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FormatEvaluation:
    """Evaluación histórica de una generación concreta.

    Admite dos formas, según qué campos estén presentes:

    - **V1** (heurístico 1.1): ``status`` + ``scores`` (enteros) +
      ``unsupported_information`` (bool) + ``observations`` (strings).
    - **V2** (Sprint 4): ``verdict`` + ``heuristic_scores`` (floats) +
      ``semantic_evaluation`` (resultado estructurado completo).

    Una evaluación V2 puede, además, dejar poblados los campos V1 si en el
    futuro se decide traducir ``verdict`` a ``status`` por compatibilidad;
    hoy no se asume esa traducción.
    """

    evaluation_id: str
    format_id: str

    # V1 — ninguno es obligatorio a nivel de dataclass; se validan en
    # conjunto en __post_init__ para no romper evaluaciones V2 "puras".
    status: FormatEvaluationStatus | None = None
    scores: EvaluationScores | None = None
    unsupported_information: bool = False
    observations: tuple[str, ...] = ()
    evaluator_version: str | None = None
    rubric_version: str | None = None

    # V2
    verdict: EvaluationVerdict | None = None
    heuristic_scores: HeuristicScoresV2 | None = None
    semantic_evaluation: SemanticEvaluationResult | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.evaluation_id.strip():
            raise ValueError(
                "evaluation_id no puede estar vacío."
            )

        if not self.format_id.strip():
            raise ValueError(
                "format_id no puede estar vacío."
            )

        if any(
            not observation.strip()
            for observation in self.observations
        ):
            raise ValueError(
                "observations no puede contener valores vacíos."
            )

        if (
            self.evaluator_version is not None
            and not self.evaluator_version.strip()
        ):
            raise ValueError(
                "evaluator_version no puede estar vacío."
            )

        if (
            self.rubric_version is not None
            and not self.rubric_version.strip()
        ):
            raise ValueError(
                "rubric_version no puede estar vacío."
            )

        has_v1_signal = (
            self.status is not None
            or self.scores is not None
        )

        has_v2_signal = (
            self.verdict is not None
            or self.heuristic_scores is not None
            or self.semantic_evaluation is not None
        )

        if not has_v1_signal and not has_v2_signal:
            raise ValueError(
                "Una evaluación debe incluir al menos una señal real: "
                "V1 (status/scores) o V2 (verdict/heuristic_scores/"
                "semantic_evaluation)."
            )

        if self.status is not None and self.scores is None:
            raise ValueError(
                "Una evaluación V1 con status debe incluir scores."
            )

    @property
    def is_v2(self) -> bool:
        """Indica si la evaluación trae el contrato V2 (Sprint 4)."""
        return self.semantic_evaluation is not None or self.verdict is not None
