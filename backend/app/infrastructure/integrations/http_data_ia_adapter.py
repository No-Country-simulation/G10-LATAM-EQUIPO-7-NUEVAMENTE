"""Adaptador HTTP para la integración de BackendAPI con Data/IA."""

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.enums import (
    FormatEvaluationStatus,
    GeneratedFormatType,
)
from app.domain.format_evaluation import (
    EvaluationScores,
)
from app.ports.data_ia_port import (
    DataIAError,
    DataIAEvaluationInput,
    DataIAEvaluationResult,
)


class _EvaluationScoresHTTPResponse(BaseModel):
    """Puntajes retornados por el contrato HTTP de Data/IA."""

    model_config = ConfigDict(
        extra="forbid",
    )

    relevancia: int = Field(
        ge=1,
        le=5,
    )
    coherencia: int = Field(
        ge=1,
        le=5,
    )
    adaptacion_didactica: int = Field(
        ge=1,
        le=5,
    )
    informacion_respaldada: int = Field(
        ge=1,
        le=5,
    )

    def to_domain(
        self,
    ) -> EvaluationScores:
        """Convierte los nombres HTTP al dominio estable de BackendAPI."""
        return EvaluationScores(
            relevance=self.relevancia,
            coherence=self.coherencia,
            didactic_adaptation=(
                self.adaptacion_didactica
            ),
            content_support=(
                self.informacion_respaldada
            ),
        )


class _DataIAEvaluationHTTPResponse(BaseModel):
    """Respuesta HTTP esperada desde POST /evaluate."""

    model_config = ConfigDict(
        extra="ignore",
    )

    document_id: str = Field(
        min_length=1
    )
    format: GeneratedFormatType
    status: FormatEvaluationStatus
    scores: _EvaluationScoresHTTPResponse
    informacion_no_respaldada: bool
    observaciones: list[str] = Field(
        default_factory=list
    )
    evaluator_version: str | None = None
    rubric_version: str | None = None


class HTTPDataIAAdapter:
    """Implementa DataIAPort mediante el servicio HTTP de Data/IA.

    El adapter traduce únicamente entre el contrato interno de BackendAPI
    y el contrato HTTP de evaluación. No decide si un formato debe ser
    evaluado, no altera el estado de generación y no persiste resultados.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        evaluate_path: str,
    ) -> None:
        if not evaluate_path.startswith("/"):
            raise ValueError(
                "evaluate_path debe comenzar con '/'."
            )

        self._client = client
        self._evaluate_path = (
            evaluate_path
        )

    async def evaluate(
        self,
        request: DataIAEvaluationInput,
    ) -> DataIAEvaluationResult:
        """Solicita la evaluación de un formato ya generado.

        Raises:
            DataIAError: Si ocurre un timeout, error HTTP, error de
                conexión o Data/IA devuelve un contrato incompatible.
        """
        payload = self._build_request_payload(
            request
        )

        try:
            response = await self._client.post(
                self._evaluate_path,
                json=payload,
            )

            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise DataIAError(
                "La solicitud de evaluación a Data/IA "
                f"superó el tiempo permitido para "
                f"{request.document_id}."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise DataIAError(
                "Data/IA rechazó la evaluación del documento "
                f"{request.document_id} con estado HTTP "
                f"{exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise DataIAError(
                "No fue posible conectar con Data/IA para evaluar "
                f"el documento {request.document_id}."
            ) from exc

        try:
            payload_response = (
                _DataIAEvaluationHTTPResponse
                .model_validate(
                    response.json()
                )
            )

            return DataIAEvaluationResult(
                document_id=(
                    payload_response.document_id
                ),
                format_type=(
                    payload_response.format
                ),
                status=(
                    payload_response.status
                ),
                scores=(
                    payload_response
                    .scores
                    .to_domain()
                ),
                unsupported_information=(
                    payload_response
                    .informacion_no_respaldada
                ),
                observations=tuple(
                    payload_response.observaciones
                ),
                evaluator_version=(
                    payload_response
                    .evaluator_version
                ),
                rubric_version=(
                    payload_response
                    .rubric_version
                ),
            )

        except (
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise DataIAError(
                "Data/IA devolvió una respuesta de evaluación "
                f"inválida para el documento {request.document_id}."
            ) from exc

    @staticmethod
    def _build_request_payload(
        request: DataIAEvaluationInput,
    ) -> dict[str, object]:
        """Traduce el contrato interno al request HTTP de Data/IA."""
        context = request.generation_context

        generation_context: dict[
            str,
            object,
        ] = {
            "profile": context.profile,
            "niche": context.niche,
            "detail_level": (
                context.detail_level
            ),
        }

        if (
            context.learning_objective
            is not None
        ):
            generation_context[
                "learning_objective"
            ] = context.learning_objective

        return {
            "document_id": request.document_id,
            "format": request.format_type.value,
            "generated_content": (
                request.generated_content.to_dict()
            ),
            "generation_context": (
                generation_context
            ),
            "chunks_used": [
                chunk.to_dict()
                for chunk
                in request.chunks_used
            ],
        }
