"""Pruebas de migración SQLite para metadatos pedagógicos."""

import sqlite3
from pathlib import Path

from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)


def test_initialize_adds_learning_metadata_column_to_legacy_database(
    tmp_path: Path,
) -> None:
    """Añade la columna sin eliminar documentos existentes."""
    database_path = (
        tmp_path / "legacy.db"
    )

    connection = sqlite3.connect(
        database_path
    )

    try:
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
                "manual.txt",
                "a" * 64,
                "text/plain",
                10,
                "indexed",
                "documents/doc_legacy/original.txt",
                "2026-10-07T12:00:00+00:00",
                "2026-10-07T12:00:00+00:00",
            ),
        )

        connection.commit()
    finally:
        connection.close()

    database = SQLiteDatabase(
        f"sqlite:///{database_path.as_posix()}"
    )

    database.initialize()

    with database.connect() as migrated:
        columns = {
            row["name"]
            for row in migrated.execute(
                "PRAGMA table_info(documents)"
            ).fetchall()
        }

        stored = migrated.execute(
            """
            SELECT document_id, learning_metadata_json
            FROM documents
            WHERE document_id = ?
            """,
            ("doc_legacy",),
        ).fetchone()

    assert (
        "learning_metadata_json"
        in columns
    )
    assert stored is not None
    assert (
        stored["document_id"]
        == "doc_legacy"
    )
    assert (
        stored["learning_metadata_json"]
        is None
    )
