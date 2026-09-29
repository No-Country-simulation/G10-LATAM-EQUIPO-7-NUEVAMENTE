"""Adapter SQLite para evaluaciones de formatos."""

import sqlite3

from app.domain.format_evaluation import (
    FormatEvaluation,
)
from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.models import (
    FormatEvaluationRecord,
)
from app.ports.format_evaluation_repository_port import (
    FormatEvaluationAlreadyExistsError,
    FormatEvaluationRepositoryError,
)


class SQLiteFormatEvaluationRepositoryAdapter:
    """Implementa persistencia histórica de evaluaciones."""

    def __init__(
        self,
        database: SQLiteDatabase,
    ) -> None:
        self._database = database

    def create(
        self,
        evaluation: FormatEvaluation,
    ) -> FormatEvaluation:
        """Persiste una evaluación nueva sin sobrescribir anteriores."""
        record = FormatEvaluationRecord.from_domain(
            evaluation
        )

        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO format_evaluations (
                        evaluation_id,
                        format_id,
                        status,
                        relevance_score,
                        coherence_score,
                        didactic_adaptation_score,
                        content_support_score,
                        unsupported_information,
                        observations_json,
                        evaluator_version,
                        rubric_version,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.evaluation_id,
                        record.format_id,
                        record.status,
                        record.relevance_score,
                        record.coherence_score,
                        (
                            record
                            .didactic_adaptation_score
                        ),
                        record.content_support_score,
                        (
                            record
                            .unsupported_information
                        ),
                        record.observations_json,
                        record.evaluator_version,
                        record.rubric_version,
                        record.created_at,
                    ),
                )

        except sqlite3.IntegrityError as exc:
            raise FormatEvaluationAlreadyExistsError(
                "No fue posible persistir la evaluación "
                f"{evaluation.evaluation_id}."
            ) from exc

        except sqlite3.Error as exc:
            raise FormatEvaluationRepositoryError(
                "No fue posible persistir la evaluación."
            ) from exc

        return evaluation

    def find_by_id(
        self,
        evaluation_id: str,
    ) -> FormatEvaluation | None:
        """Busca una evaluación por identificador."""
        try:
            with self._database.connect() as connection:
                row = connection.execute(
                    """
                    SELECT *
                    FROM format_evaluations
                    WHERE evaluation_id = ?
                    """,
                    (evaluation_id,),
                ).fetchone()

        except sqlite3.Error as exc:
            raise FormatEvaluationRepositoryError(
                "No fue posible consultar la evaluación."
            ) from exc

        if row is None:
            return None

        return (
            FormatEvaluationRecord
            .from_row(row)
            .to_domain()
        )

    def find_by_format_id(
        self,
        format_id: str,
    ) -> list[FormatEvaluation]:
        """Obtiene todo el historial de evaluación de una generación."""
        try:
            with self._database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM format_evaluations
                    WHERE format_id = ?
                    ORDER BY created_at ASC
                    """,
                    (format_id,),
                ).fetchall()

        except sqlite3.Error as exc:
            raise FormatEvaluationRepositoryError(
                "No fue posible consultar el historial "
                "de evaluaciones."
            ) from exc

        return [
            FormatEvaluationRecord
            .from_row(row)
            .to_domain()
            for row in rows
        ]