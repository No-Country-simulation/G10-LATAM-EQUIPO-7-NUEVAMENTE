"""Creación de adapters de persistencia según configuración."""

from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_format_evaluation_repository_adapter import (
    SQLiteFormatEvaluationRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)
from app.ports.document_repository_port import (
    DocumentRepositoryPort,
)
from app.ports.format_evaluation_repository_port import (
    FormatEvaluationRepositoryPort,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryPort,
)


class UnsupportedDatabaseError(Exception):
    """El motor configurado no está soportado."""


def _create_database(
    database_url: str,
) -> SQLiteDatabase:
    """Construye e inicializa SQLite."""
    if not database_url.startswith(
        "sqlite:///"
    ):
        raise UnsupportedDatabaseError(
            "Motor de base de datos no soportado por BackendAPI."
        )

    database = SQLiteDatabase(
        database_url
    )

    database.initialize()

    return database


def create_document_repository(
    database_url: str,
) -> DocumentRepositoryPort:
    """Construye el repositorio de documentos."""
    return SQLiteDocumentRepositoryAdapter(
        _create_database(
            database_url
        )
    )


def create_generated_format_repository(
    database_url: str,
) -> GeneratedFormatRepositoryPort:
    """Construye el repositorio de formatos generados."""
    return SQLiteGeneratedFormatRepositoryAdapter(
        _create_database(
            database_url
        )
    )


def create_format_evaluation_repository(
    database_url: str,
) -> FormatEvaluationRepositoryPort:
    """Construye el repositorio de evaluaciones."""
    return SQLiteFormatEvaluationRepositoryAdapter(
        _create_database(
            database_url
        )
    )