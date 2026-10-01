"""Pruebas del wiring principal de BackendAPI."""

from fastapi.testclient import TestClient

from app.application.format_generation_service import (
    FormatGenerationService,
)


def test_lifespan_initializes_format_generation_service(
    client: TestClient,
) -> None:
    """Inicializa la generación mediante el adapter de Agentes."""
    service = getattr(
        client.app.state,
        "format_generation_service",
        None,
    )

    assert isinstance(
        service,
        FormatGenerationService,
    )