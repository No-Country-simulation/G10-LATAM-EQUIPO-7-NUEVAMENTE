from fastapi.testclient import TestClient

from app.core.config import settings


def test_root(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == settings.PROJECT_NAME


def test_health(client: TestClient, api_prefix: str) -> None:
    response = client.get(f"{api_prefix}/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["version"] == settings.VERSION
    assert "timestamp" in body