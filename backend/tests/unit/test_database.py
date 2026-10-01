"""Pruebas unitarias de gestión de conexiones SQLite."""

import sqlite3
from pathlib import Path

import pytest

from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)


def test_database_connection_is_closed_after_context(
    tmp_path: Path,
) -> None:
    """La conexión debe cerrarse al abandonar el contexto."""
    database = SQLiteDatabase(
        "sqlite:///"
        f"{(tmp_path / 'connection.db').as_posix()}"
    )

    with database.connect() as connection:
        result = connection.execute(
            "SELECT 1"
        ).fetchone()

        assert result is not None
        assert result[0] == 1

    with pytest.raises(
        sqlite3.ProgrammingError,
        match="closed",
    ):
        connection.execute(
            "SELECT 1"
        )


def test_database_connection_commits_on_success(
    tmp_path: Path,
) -> None:
    """Los cambios exitosos deben persistirse antes del cierre."""
    database = SQLiteDatabase(
        "sqlite:///"
        f"{(tmp_path / 'commit.db').as_posix()}"
    )

    with database.connect() as connection:
        connection.execute(
            """
            CREATE TABLE example (
                value TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            INSERT INTO example (value)
            VALUES (?)
            """,
            ("persisted",),
        )

    with database.connect() as connection:
        row = connection.execute(
            """
            SELECT value
            FROM example
            """
        ).fetchone()

    assert row is not None
    assert row["value"] == "persisted"


def test_database_connection_rolls_back_on_error(
    tmp_path: Path,
) -> None:
    """Una excepción debe revertir la transacción antes del cierre."""
    database = SQLiteDatabase(
        "sqlite:///"
        f"{(tmp_path / 'rollback.db').as_posix()}"
    )

    with database.connect() as connection:
        connection.execute(
            """
            CREATE TABLE example (
                value TEXT NOT NULL
            )
            """
        )

        with (
            pytest.raises(
                RuntimeError,
                match="forced failure",
            ),
            database.connect() as connection,
        ):
            connection.execute(
                """
                INSERT INTO example (value)
                VALUES (?)
                """,
                ("must_not_persist",),
            )

            raise RuntimeError(
                "forced failure"
            )

    with database.connect() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM example
            """
        ).fetchone()

    assert row is not None
    assert row["total"] == 0