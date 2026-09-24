"""Pruebas de selección de persistencia de documentos."""

import pytest

from app.infrastructure.persistence.repository_factory import (
    UnsupportedDatabaseError,
    create_document_repository,
)
from app.infrastructure.persistence.sqlite_document_repository import (
    SQLiteDocumentRepository,
)


def test_factory_creates_sqlite_repository(
    tmp_path,
) -> None:
    database_path = tmp_path / "documents.db"

    repository = create_document_repository(
        f"sqlite:///{database_path.as_posix()}"
    )

    assert isinstance(
        repository,
        SQLiteDocumentRepository,
    )
    assert database_path.exists()


def test_factory_rejects_unsupported_database() -> None:
    with pytest.raises(UnsupportedDatabaseError):
        create_document_repository(
            "postgresql://localhost/nuevamente"
        )