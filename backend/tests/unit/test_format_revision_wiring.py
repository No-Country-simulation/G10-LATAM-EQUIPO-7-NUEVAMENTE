"""Comprueba la configuración de la integración con el Agente Revisor."""

from fastapi.testclient import TestClient

from app.application.format_revision_service import FormatRevisionService
from app.core.config import settings
from app.infrastructure.integrations.http_agent_revision_adapter import (
    HTTPAgentRevisionAdapter,
)


def test_lifespan_wires_revision_service_with_http_adapter(client: TestClient) -> None:
    """El servicio se inicializa pero no ejecuta correcciones al iniciar."""
    service = getattr(client.app.state, "format_revision_service", None)
    assert isinstance(service, FormatRevisionService)
    assert isinstance(service._agent_revision, HTTPAgentRevisionAdapter)
    assert service._agent_revision._revise_path == settings.AGENTS_REVISE_PATH


def test_revision_path_is_configured_in_settings() -> None:
    """La ruta del Revisor se parametriza independientemente de /generate."""
    assert settings.AGENTS_REVISE_PATH.startswith("/")
    assert settings.AGENTS_REVISE_PATH != settings.AGENTS_GENERATE_PATH
