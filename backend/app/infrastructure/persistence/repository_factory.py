"""Creación de adaptadores de persistencia según la configuración."""

from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.ports.document_repository_port import (
    DocumentRepositoryPort,
)


class UnsupportedDatabaseError(Exception):
    """El motor de persistencia configurado no está soportado."""


def create_document_repository(
    database_url: str,
) -> DocumentRepositoryPort:
    """Construye el adapter de persistencia configurado.

    Actualmente se implementa SQLite. La fábrica mantiene desacoplada
    la capa de aplicación del motor de persistencia concreto.
    """
    if database_url.startswith(
        "sqlite:///"
    ):
        database = SQLiteDatabase(
            database_url
        )

        database.initialize()

        return SQLiteDocumentRepositoryAdapter(
            database
        )

    raise UnsupportedDatabaseError(
        "Motor de base de datos no soportado por BackendAPI."
    )