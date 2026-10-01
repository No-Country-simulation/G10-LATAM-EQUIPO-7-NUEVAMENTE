"""Pruebas HTTP del flujo de adaptación educativa."""

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.application.adaptation_orchestration_service import (
    AdaptationDocumentStateError,
)
from app.application.document_service import (
    DocumentNotFoundError,
)
from app.application.format_generation_service import (
    FormatGenerationContractError,
    FormatGenerationIntegrationError,
)
from app.application.rag_integration_service import (
    RAGIntegrationError,
)
from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)


@dataclass(frozen=True, slots=True)
class StubGeneratedFormat:
    """Resultado mínimo requerido por el contrato HTTP."""

    format_type: GeneratedFormatType
    status: GeneratedFormatStatus
    error_message: str | None = None


class StubAdaptationOrchestrationService:
    """Doble controlado del orquestador para pruebas HTTP."""

    def __init__(
        self,
        *,
        results: list[StubGeneratedFormat] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.results = results or []
        self.error = error
        self.requests: list[
            dict[str, object]
        ] = []

    async def adapt_document(
        self,
        *,
        document_id: str,
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[StubGeneratedFormat]:
        """Registra la llamada y retorna el resultado configurado."""
        self.requests.append(
            {
                "document_id": document_id,
                "profile": profile,
                "niche": niche,
                "detail_level": detail_level,
                "learning_objective": learning_objective,
            }
        )

        if self.error is not None:
            raise self.error

        return self.results


def build_payload() -> dict[str, object]:
    """Construye una solicitud válida de adaptación."""
    return {
        "document_id": "doc_123",
        "profile": "intermediate",
        "niche": "general",
        "detail_level": "detailed",
        "learning_objective": (
            "Comprender los conceptos principales."
        ),
    }


def test_adaptation_executes_orchestration(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Ejecuta el orquestador y expone el resultado de cada formato."""
    service = StubAdaptationOrchestrationService(
        results=[
            StubGeneratedFormat(
                format_type=GeneratedFormatType.QUIZ,
                status=GeneratedFormatStatus.SUCCESS,
            ),
            StubGeneratedFormat(
                format_type=(
                    GeneratedFormatType.FLASHCARDS
                ),
                status=GeneratedFormatStatus.FAILED,
                error_message=(
                    "No fue posible generar Flashcards."
                ),
            ),
        ]
    )

    client.app.state.adaptation_orchestration_service = (
        service
    )

    response = client.post(
        f"{api_prefix}/adaptations",
        json=build_payload(),
    )

    assert response.status_code == 200

    assert service.requests == [
        {
            "document_id": "doc_123",
            "profile": "intermediate",
            "niche": "general",
            "detail_level": "detailed",
            "learning_objective": (
                "Comprender los conceptos principales."
            ),
        }
    ]

    assert response.json() == {
        "document_id": "doc_123",
        "results": [
            {
                "format": "quiz",
                "status": "success",
                "error_message": None,
            },
            {
                "format": "flashcards",
                "status": "failed",
                "error_message": (
                    "No fue posible generar Flashcards."
                ),
            },
        ],
    }


def test_adaptation_returns_404_for_unknown_document(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Traduce un documento inexistente a HTTP 404."""
    service = StubAdaptationOrchestrationService(
        error=DocumentNotFoundError(
            "No existe el documento doc_123."
        )
    )

    client.app.state.adaptation_orchestration_service = (
        service
    )

    response = client.post(
        f"{api_prefix}/adaptations",
        json=build_payload(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No existe el documento doc_123."
    )


def test_adaptation_returns_409_for_invalid_document_state(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Traduce un estado de documento inválido a HTTP 409."""
    service = StubAdaptationOrchestrationService(
        error=AdaptationDocumentStateError(
            "El documento no puede iniciar la adaptación."
        )
    )

    client.app.state.adaptation_orchestration_service = (
        service
    )

    response = client.post(
        f"{api_prefix}/adaptations",
        json=build_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "El documento no puede iniciar la adaptación."
    )


@pytest.mark.parametrize(
    "integration_error",
    [
        RAGIntegrationError(
            "No fue posible indexar el documento."
        ),
        FormatGenerationIntegrationError(
            "No fue posible comunicarse con Agentes."
        ),
        FormatGenerationContractError(
            "Agentes devolvió una respuesta inválida."
        ),
    ],
)
def test_adaptation_returns_502_for_integration_failures(
    client: TestClient,
    api_prefix: str,
    integration_error: Exception,
) -> None:
    """Traduce fallos externos o de contrato a HTTP 502."""
    service = StubAdaptationOrchestrationService(
        error=integration_error
    )

    client.app.state.adaptation_orchestration_service = (
        service
    )

    response = client.post(
        f"{api_prefix}/adaptations",
        json=build_payload(),
    )

    assert response.status_code == 502
    assert response.json()["detail"] == str(
        integration_error
    )


def test_adaptation_rejects_legacy_output_format(
    client: TestClient,
    api_prefix: str,
) -> None:
    """Rechaza el antiguo campo output_format enviado por Frontend."""
    service = StubAdaptationOrchestrationService()

    client.app.state.adaptation_orchestration_service = (
        service
    )

    payload = build_payload()
    payload["output_format"] = "all"

    response = client.post(
        f"{api_prefix}/adaptations",
        json=payload,
    )

    assert response.status_code == 422
    assert service.requests == []