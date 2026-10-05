"""Fixtures compartidas por la suite de tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.infrastructure.persistence.repository_factory import (
    create_generated_format_repository,
)
from app.main import create_app
from tests.fakes import (
    FakeAdaptationOrchestrationService,
    FakeObjectStorage,
)


@pytest.fixture
def object_storage() -> FakeObjectStorage:
    """Proporciona almacenamiento de objetos falso para las pruebas."""
    return FakeObjectStorage()


@pytest.fixture
def client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    object_storage: FakeObjectStorage,
) -> Iterator[TestClient]:
    """Crea un cliente con una base SQLite aislada por prueba."""
    database_path = (
        tmp_path / "nuevamente_test.db"
    )

    monkeypatch.setattr(
        settings,
        "DATABASE_URL",
        (
            "sqlite:///"
            f"{database_path.as_posix()}"
        ),
    )

    with TestClient(
        create_app()
    ) as test_client:
        test_client.app.state.object_storage = (
            object_storage
        )

        yield test_client


@pytest.fixture
def fake_adaptation_orchestration_service(
    client: TestClient,
) -> FakeAdaptationOrchestrationService:
    """Reemplaza el orquestador real para pruebas HTTP de documentos.

    El servicio real permanece disponible en las pruebas que no solicitan
    explícitamente esta fixture.
    """
    generated_format_repository = (
        create_generated_format_repository(
            settings.DATABASE_URL
        )
    )

    service = (
        FakeAdaptationOrchestrationService(
            document_service=(
                client.app.state.document_service
            ),
            generated_format_repository=(
                generated_format_repository
            ),
        )
    )

    client.app.state.adaptation_orchestration_service = (
        service
    )

    return service


@pytest.fixture(scope="session")
def api_prefix() -> str:
    return settings.API_V1_PREFIX


@pytest.fixture
def temporary_upload_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Redirige las cargas a un directorio temporal."""
    upload_directory = (
        tmp_path / "uploads"
    )

    monkeypatch.setattr(
        settings,
        "UPLOAD_DIR",
        str(upload_directory),
    )

    return upload_directory