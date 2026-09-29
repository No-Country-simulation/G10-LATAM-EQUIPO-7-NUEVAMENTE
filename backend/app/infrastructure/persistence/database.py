"""Configuración de la base de datos SQLite utilizada en desarrollo."""

import sqlite3
from pathlib import Path

_DOCUMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    content_type TEXT,
    size_bytes INTEGER NOT NULL,
    status TEXT NOT NULL,
    oci_object_name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_GENERATED_FORMATS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS generated_formats (
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
);
"""

_FORMAT_EVALUATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS format_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    format_id TEXT NOT NULL,

    status TEXT NOT NULL
        CHECK (
            status IN (
                'aprobado',
                'requiere_revision',
                'rechazado'
            )
        ),

    relevance_score INTEGER NOT NULL
        CHECK (relevance_score BETWEEN 1 AND 5),

    coherence_score INTEGER NOT NULL
        CHECK (coherence_score BETWEEN 1 AND 5),

    didactic_adaptation_score INTEGER NOT NULL
        CHECK (didactic_adaptation_score BETWEEN 1 AND 5),

    content_support_score INTEGER NOT NULL
        CHECK (content_support_score BETWEEN 1 AND 5),

    unsupported_information INTEGER NOT NULL
        CHECK (
            unsupported_information IN (0, 1)
        ),

    observations_json TEXT NOT NULL DEFAULT '[]',

    evaluator_version TEXT,
    rubric_version TEXT,

    created_at TEXT NOT NULL,

    FOREIGN KEY (format_id)
        REFERENCES generated_formats(format_id)
        ON DELETE CASCADE
);
"""

_SCHEMA_INDEXES_SQL = (
    """
    CREATE INDEX IF NOT EXISTS
        idx_generated_formats_document
    ON generated_formats(document_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS
        idx_generated_formats_document_type
    ON generated_formats(
        document_id,
        format_type
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS
        idx_format_evaluations_format
    ON format_evaluations(format_id);
    """,
)


class SQLiteDatabase:
    """Gestiona conexiones y creación del esquema SQLite."""

    _URL_PREFIX = "sqlite:///"

    def __init__(
        self,
        database_url: str,
    ) -> None:
        if not database_url.startswith(
            self._URL_PREFIX
        ):
            raise ValueError(
                "SQLiteDatabase requiere una URL "
                "con formato sqlite:///ruta."
            )

        raw_path = database_url.removeprefix(
            self._URL_PREFIX
        )

        if not raw_path:
            raise ValueError(
                "La ruta de SQLite no puede estar vacía."
            )

        self._database_path = Path(
            raw_path
        )

    @property
    def database_path(self) -> Path:
        """Ruta física del archivo SQLite."""
        return self._database_path

    def connect(
        self,
    ) -> sqlite3.Connection:
        """Abre una conexión configurada a SQLite."""
        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            self._database_path
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    def initialize(
        self,
    ) -> None:
        """Crea todas las estructuras requeridas por BackendAPI."""
        with self.connect() as connection:
            connection.execute(
                _DOCUMENTS_TABLE_SQL
            )

            connection.execute(
                _GENERATED_FORMATS_TABLE_SQL
            )

            connection.execute(
                _FORMAT_EVALUATIONS_TABLE_SQL
            )

            for statement in (
                _SCHEMA_INDEXES_SQL
            ):
                connection.execute(
                    statement
                )