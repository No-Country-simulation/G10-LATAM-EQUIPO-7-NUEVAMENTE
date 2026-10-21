"""Adaptador SQLite para recuperaciones controladas de revisiones vencidas.

La escritura usa BEGIN IMMEDIATE para serializar comprobación y transición.
"""

import sqlite3
from datetime import UTC, datetime

from app.infrastructure.persistence.database import SQLiteDatabase
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryError
from app.ports.stale_revision_recovery_port import StaleRevisionCandidate


class SQLiteStaleRevisionRecoveryAdapter:
    """Detecta y cierra solo correcciones en processing con antigüedad vencida."""

    _SELECT_STALE = """
        SELECT format_id, revision_of_format_id, document_id, updated_at
        FROM generated_formats
        WHERE revision_of_format_id IS NOT NULL
          AND status = 'processing'
          AND updated_at <= ?
        ORDER BY updated_at ASC, format_id ASC
    """

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    @staticmethod
    def _to_utc(value: datetime) -> str:
        """Serializa un instante UTC con el formato canónico de dominio."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Las fechas de recuperación deben tener zona horaria.")
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _decode(rows: list[sqlite3.Row]) -> tuple[StaleRevisionCandidate, ...]:
        """Convierte registros persistidos en candidatos con identidad explícita."""
        try:
            return tuple(
                StaleRevisionCandidate(
                    format_id=row["format_id"],
                    original_format_id=row["revision_of_format_id"],
                    document_id=row["document_id"],
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            )
        except (TypeError, ValueError, KeyError) as exc:
            raise GeneratedFormatRepositoryError(
                "Existen revisiones vencidas con fechas o identidad inválidas."
            ) from exc

    def find_stale(self, *, cutoff: datetime) -> tuple[StaleRevisionCandidate, ...]:
        """Realiza solo lectura de las revisiones vencidas."""
        timestamp = self._to_utc(cutoff)
        try:
            with self._database.connect() as connection:
                rows = connection.execute(self._SELECT_STALE, (timestamp,)).fetchall()
        except sqlite3.Error as exc:
            raise GeneratedFormatRepositoryError(
                "No fue posible consultar las revisiones vencidas."
            ) from exc
        return self._decode(rows)

    def fail_stale(
        self, *, cutoff: datetime, failed_at: datetime, error_message: str
    ) -> tuple[str, ...]:
        """Cierra candidatos de modo atómico; no reescribe éxitos ni fallos.

        La selección y actualización quedan protegidas por la misma
        transacción con bloqueo de escritura adquirido anticipadamente.
        """
        timestamp = self._to_utc(cutoff)
        failed_timestamp = self._to_utc(failed_at)
        if not isinstance(error_message, str) or not error_message.strip():
            raise ValueError("error_message debe tener contenido.")
        try:
            with self._database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(self._SELECT_STALE, (timestamp,)).fetchall()
                identifiers: list[str] = []
                for candidate in self._decode(rows):
                    cursor = connection.execute(
                        """
                        UPDATE generated_formats
                        SET status = 'failed', error_message = ?, updated_at = ?
                        WHERE format_id = ?
                          AND revision_of_format_id IS NOT NULL
                          AND status = 'processing'
                          AND updated_at <= ?
                        """,
                        (error_message, failed_timestamp, candidate.format_id, timestamp),
                    )
                    if cursor.rowcount != 1:
                        raise GeneratedFormatRepositoryError(
                            "La revisión cambió de estado durante la recuperación."
                        )
                    identifiers.append(candidate.format_id)
                return tuple(identifiers)
        except sqlite3.Error as exc:
            raise GeneratedFormatRepositoryError(
                "No fue posible finalizar las revisiones vencidas."
            ) from exc
