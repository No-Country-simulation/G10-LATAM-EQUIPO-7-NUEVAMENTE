"""Puerto de persistencia de evaluaciones."""

from typing import Protocol

from app.domain.format_evaluation import (
    FormatEvaluation,
)


class FormatEvaluationRepositoryError(
    Exception
):
    """Error general de persistencia de evaluaciones."""


class FormatEvaluationAlreadyExistsError(
    FormatEvaluationRepositoryError
):
    """La evaluación ya existe."""


class FormatEvaluationRepositoryPort(
    Protocol
):
    """Operaciones requeridas para persistir evaluaciones."""

    def create(
        self,
        evaluation: FormatEvaluation,
    ) -> FormatEvaluation:
        """Persiste una evaluación histórica."""
        ...

    def find_by_id(
        self,
        evaluation_id: str,
    ) -> FormatEvaluation | None:
        """Busca una evaluación."""
        ...

    def find_by_format_id(
        self,
        format_id: str,
    ) -> list[FormatEvaluation]:
        """Obtiene las evaluaciones históricas de una generación."""
        ...