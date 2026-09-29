"""Entidades asociadas a evaluaciones realizadas por Data/IA."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.enums import (
    FormatEvaluationStatus,
)


@dataclass(frozen=True, slots=True)
class EvaluationScores:
    """Puntajes emitidos por Data/IA."""

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


@dataclass(frozen=True, slots=True)
class FormatEvaluation:
    """Evaluación histórica de una generación concreta."""

    evaluation_id: str
    format_id: str
    status: FormatEvaluationStatus
    scores: EvaluationScores
    unsupported_information: bool

    observations: tuple[str, ...] = ()
    evaluator_version: str | None = None
    rubric_version: str | None = None

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