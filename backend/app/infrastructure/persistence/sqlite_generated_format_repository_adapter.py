"""Adapter SQLite para formatos generados."""

import sqlite3

from app.domain.generated_format import (
    GeneratedFormat,
)
from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.models import (
    GeneratedFormatRecord,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatAlreadyExistsError,
    GeneratedFormatRepositoryError,
)


class SQLiteGeneratedFormatRepositoryAdapter:
    """Implementa persistencia SQLite de formatos generados."""

    def __init__(
        self,
        database: SQLiteDatabase,
    ) -> None:
        self._database = database

    def create(
        self,
        generated_format: GeneratedFormat,
    ) -> GeneratedFormat:
        """Persiste una nueva generación."""
        record = GeneratedFormatRecord.from_domain(
            generated_format
        )

        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO generated_formats (
                        format_id,
                        document_id,
                        format_type,
                        status,
                        content_json,
                        chunks_used_json,
                        profile,
                        niche,
                        detail_level,
                        learning_objective,
                        error_message,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.format_id,
                        record.document_id,
                        record.format_type,
                        record.status,
                        record.content_json,
                        record.chunks_used_json,
                        record.profile,
                        record.niche,
                        record.detail_level,
                        record.learning_objective,
                        record.error_message,
                        record.created_at,
                        record.updated_at,
                    ),
                )

        except sqlite3.IntegrityError as exc:
            raise GeneratedFormatAlreadyExistsError(
                "No fue posible persistir el formato "
                f"{generated_format.format_id}."
            ) from exc

        except sqlite3.Error as exc:
            raise GeneratedFormatRepositoryError(
                "No fue posible persistir el formato generado."
            ) from exc

        return generated_format

    def find_by_id(
        self,
        format_id: str,
    ) -> GeneratedFormat | None:
        """Busca una generación mediante format_id."""
        try:
            with self._database.connect() as connection:
                row = connection.execute(
                    """
                    SELECT *
                    FROM generated_formats
                    WHERE format_id = ?
                    """,
                    (format_id,),
                ).fetchone()

        except sqlite3.Error as exc:
            raise GeneratedFormatRepositoryError(
                "No fue posible consultar el formato generado."
            ) from exc

        if row is None:
            return None

        try:
            return (
                GeneratedFormatRecord
                .from_row(row)
                .to_domain()
            )
        except (
            TypeError,
            ValueError,
            KeyError,
        ) as exc:
            raise GeneratedFormatRepositoryError(
                "El formato persistido contiene datos inválidos."
            ) from exc

    def find_by_document_id(
        self,
        document_id: str,
    ) -> list[GeneratedFormat]:
        """Obtiene el historial de generaciones del documento."""
        try:
            with self._database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM generated_formats
                    WHERE document_id = ?
                    ORDER BY created_at ASC
                    """,
                    (document_id,),
                ).fetchall()

        except sqlite3.Error as exc:
            raise GeneratedFormatRepositoryError(
                "No fue posible consultar los formatos "
                "del documento."
            ) from exc

        try:
            return [
                GeneratedFormatRecord
                .from_row(row)
                .to_domain()
                for row in rows
            ]
        except (
            TypeError,
            ValueError,
            KeyError,
        ) as exc:
            raise GeneratedFormatRepositoryError(
                "Existen formatos persistidos con datos inválidos."
            ) from exc