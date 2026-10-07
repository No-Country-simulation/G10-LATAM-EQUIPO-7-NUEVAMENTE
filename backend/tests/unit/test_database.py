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

def test_database_migrates_generated_formats_to_processing_without_data_loss(
    tmp_path: Path,
) -> None:
    """Migra el CHECK anterior conservando formatos y evaluaciones."""
    database_path = (
        tmp_path / "migration.db"
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        """
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            sha256 TEXT NOT NULL UNIQUE,
            content_type TEXT,
            size_bytes INTEGER NOT NULL,
            status TEXT NOT NULL,
            oci_object_name TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE generated_formats (
            format_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            format_type TEXT NOT NULL
                CHECK (
                    format_type IN (
                        'quiz',
                        'flashcards'
                    )
                ),
            status TEXT NOT NULL
                CHECK (
                    status IN (
                        'success',
                        'failed',
                        'no_results'
                    )
                ),
            content_json TEXT,
            chunks_used_json TEXT NOT NULL DEFAULT '[]',
            profile TEXT NOT NULL,
            niche TEXT NOT NULL,
            detail_level TEXT NOT NULL,
            learning_objective TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (document_id)
                REFERENCES documents(document_id)
                ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE format_evaluations (
            evaluation_id TEXT PRIMARY KEY,
            format_id TEXT NOT NULL,
            FOREIGN KEY (format_id)
                REFERENCES generated_formats(format_id)
                ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        INSERT INTO documents (
            document_id,
            original_filename,
            sha256,
            content_type,
            size_bytes,
            status,
            oci_object_name,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "doc_legacy",
            "legacy.txt",
            "a" * 64,
            "text/plain",
            10,
            "indexed",
            "documents/doc_legacy/original.txt",
            "2026-10-01T12:00:00+00:00",
            "2026-10-01T12:00:00+00:00",
        ),
    )

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
            "fmt_legacy",
            "doc_legacy",
            "quiz",
            "failed",
            None,
            "[]",
            "beginner",
            "general",
            "standard",
            None,
            "Fallo anterior",
            "2026-10-01T12:01:00+00:00",
            "2026-10-01T12:01:00+00:00",
        ),
    )

    connection.execute(
        """
        INSERT INTO format_evaluations (
            evaluation_id,
            format_id
        )
        VALUES (?, ?)
        """,
        (
            "eval_legacy",
            "fmt_legacy",
        ),
    )

    connection.commit()
    connection.close()

    database = SQLiteDatabase(
        f"sqlite:///{database_path.as_posix()}"
    )

    database.initialize()

    with database.connect() as connection:
        schema = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE
                type = 'table'
                AND name = 'generated_formats'
            """
        ).fetchone()

        assert schema is not None
        assert "'processing'" in (
            schema["sql"] or ""
        ).lower()

        legacy_format = connection.execute(
            """
            SELECT *
            FROM generated_formats
            WHERE format_id = ?
            """,
            ("fmt_legacy",),
        ).fetchone()

        assert legacy_format is not None
        assert (
            legacy_format["status"]
            == "failed"
        )

        legacy_evaluation = connection.execute(
            """
            SELECT *
            FROM format_evaluations
            WHERE evaluation_id = ?
            """,
            ("eval_legacy",),
        ).fetchone()

        assert legacy_evaluation is not None
        assert (
            legacy_evaluation["format_id"]
            == "fmt_legacy"
        )

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
                "fmt_processing",
                "doc_legacy",
                "flashcards",
                "processing",
                None,
                "[]",
                "beginner",
                "general",
                "standard",
                None,
                None,
                "2026-10-01T12:02:00+00:00",
                "2026-10-01T12:02:00+00:00",
            ),
        )

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        assert violations == []

    # También debe ser idempotente.
    database.initialize()
