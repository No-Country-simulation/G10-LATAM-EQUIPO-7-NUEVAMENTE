"""Fixtures compartidas por la suite de tests."""

from collections.abc import Iterator

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