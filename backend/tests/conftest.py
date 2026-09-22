"""Fixtures compartidas por la suite de tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def api_prefix() -> str:
    return settings.API_V1_PREFIX


@pytest.fixture
def temporary_upload_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Redirige las cargas a un directorio temporal durante las pruebas."""
    upload_directory = tmp_path / "uploads"

    monkeypatch.setattr(
        settings,
        "UPLOAD_DIR",
        str(upload_directory),
    )

    return upload_directory