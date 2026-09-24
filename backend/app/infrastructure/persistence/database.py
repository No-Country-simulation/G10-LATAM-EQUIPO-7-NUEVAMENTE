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


class SQLiteDatabase:
    """Gestiona conexiones y creación del esquema SQLite."""

    _URL_PREFIX = "sqlite:///"

    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(self._URL_PREFIX):
            raise ValueError(
                "SQLiteDatabase requiere una URL con formato sqlite:///ruta."
            )

        raw_path = database_url.removeprefix(self._URL_PREFIX)

        if not raw_path:
            raise ValueError("La ruta de SQLite no puede estar vacía.")

        self._database_path = Path(raw_path)

    @property
    def database_path(self) -> Path:
        """Ruta física del archivo SQLite."""
        return self._database_path

    def connect(self) -> sqlite3.Connection:
        """Abre una conexión configurada a SQLite."""
        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    def initialize(self) -> None:
        """Crea las estructuras requeridas si todavía no existen."""
        with self.connect() as connection:
            connection.execute(_DOCUMENTS_TABLE_SQL)