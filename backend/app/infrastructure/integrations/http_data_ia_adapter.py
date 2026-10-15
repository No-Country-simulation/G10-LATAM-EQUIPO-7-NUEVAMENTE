"""Adaptador HTTP para la integración de BackendAPI con Data/IA."""

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.enums import FormatEvaluationStatus, GeneratedFormatType
from app.domain.format_evaluation import EvaluationScores
from app.infrastructure.integrations.http_data_ia_v2_mapper import (
    parse_evaluation_v2,
)
from app.ports.data_ia_port import (
    DataIAError,
    DataIAEvaluationInput,
    DataIAEvaluationResult,
    DataIAV2EvaluationResult,
)


class _EvaluationScoresHTTPResponse(BaseModel):
    """Puntajes retornados por el contrato HTTP V1.1 de Data/IA."""

    model_config = ConfigDict(extra="forbid")

    relevancia: int = Field(ge=1, le=5)
    coherencia: int = Field(ge=1, le=5)
    adaptacion_didactica: int = Field(ge=1, le=5)
    informacion_respaldada: int = Field(ge=1, le=5)

    def to_domain(self) -> EvaluationScores:
        """Traduce nombres públicos V1.1 a nombres de dominio."""
        return EvaluationScores(
            relevance=self.relevancia,
            coherence=self.coherencia,
            didactic_adaptation=self.adaptacion_didactica,
            content_support=self.informacion_respaldada,
        )


class _DataIAEvaluationHTTPResponse(BaseModel):
    """Contrato legacy para POST /evaluate."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(min_length=1)
    format: GeneratedFormatType
    status: FormatEvaluationStatus
    scores: _EvaluationScoresHTTPResponse
    informacion_no_respaldada: bool
    observaciones: list[str] = Field(default_factory=list)
    evaluator_version: str | None = None
    rubric_version: str | None = None


class HTTPDataIAAdapter:
    """Encapsula HTTP y desacopla Data/IA del dominio de BackendAPI.

    La ruta /evaluate/v2 utiliza exclusivamente el contrato V2; las demás
    rutas mantienen la compatibilidad legacy con /evaluate (V1.1).
    La validación y el mapeo profundo V2 viven en un módulo independiente.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        evaluate_path: str,
    ) -> None:
        if not evaluate_path.startswith("/"):
            raise ValueError("evaluate_path debe comenzar con '/'.")
        self._client = client
        self._evaluate_path = evaluate_path

    async def evaluate(
        self,
        request: DataIAEvaluationInput,
    ) -> DataIAEvaluationResult | DataIAV2EvaluationResult:
        """Solicita evaluación y valida la versión elegida mediante la ruta.

        Raises:
            DataIAError: error HTTP, timeout, conectividad, JSON o esquema.
        """
        payload = self._build_request_payload(request)
        try:
            response = await self._client.post(self._evaluate_path, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise DataIAError(
                "La solicitud de evaluación a Data/IA "
                f"superó el tiempo permitido para {request.document_id}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise DataIAError(
                "Data/IA rechazó la evaluación del documento "
                f"{request.document_id} con estado HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise DataIAError(
                "No fue posible conectar con Data/IA para evaluar "
                f"el documento {request.document_id}."
            ) from exc

        try:
            response_data = response.json()
            if self._evaluate_path.rstrip("/") == "/evaluate/v2":
                return parse_evaluation_v2(response_data)

            payload_response = _DataIAEvaluationHTTPResponse.model_validate(
                response_data
            )
            return DataIAEvaluationResult(
                document_id=payload_response.document_id,
                format_type=payload_response.format,
                status=payload_response.status,
                scores=payload_response.scores.to_domain(),
                unsupported_information=payload_response.informacion_no_respaldada,
                observations=tuple(payload_response.observaciones),
                evaluator_version=payload_response.evaluator_version,
                rubric_version=payload_response.rubric_version,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise DataIAError(
                "Data/IA devolvió una respuesta de evaluación "
                f"inválida para el documento {request.document_id}."
            ) from exc

    @staticmethod
    def _build_request_payload(
        request: DataIAEvaluationInput,
    ) -> dict[str, object]:
        """Construye los cinco campos canónicos enviados a Data/IA."""
        context = request.generation_context
        generation_context: dict[str, object] = {
            "profile": context.profile,
            "niche": context.niche,
            "detail_level": context.detail_level,
        }
        if context.learning_objective is not None:
            generation_context["learning_objective"] = context.learning_objective

        return {
            "document_id": request.document_id,
            "format": request.format_type.value,
            "generated_content": request.generated_content.to_dict(),
            "generation_context": generation_context,
            "chunks_used": [chunk.to_dict() for chunk in request.chunks_used],
        }
