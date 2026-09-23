"""Creación de repositorios de documentos según la configuración."""

from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_document_repository import (
    SQLiteDocumentRepository,
)
from app.ports.document_repository import DocumentRepository


class UnsupportedDatabaseError(Exception):
    """El motor de persistencia configurado no está soportado."""


def create_document_repository(
    database_url: str,
) -> DocumentRepository:
    """Construye el repositorio configurado para documentos.

    Actualmente se implementa SQLite para desarrollo. La selección
    centralizada permite incorporar PostgreSQL/Supabase posteriormente
    sin modificar endpoints ni casos de uso.
    """
    if database_url.startswith("sqlite:///"):
        database = SQLiteDatabase(database_url)
        database.initialize()

        return SQLiteDocumentRepository(database)

    raise UnsupportedDatabaseError(
        "Motor de base de datos no soportado por BackendAPI."
    )