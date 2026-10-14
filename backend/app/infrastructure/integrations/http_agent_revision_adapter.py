"""Adaptador HTTP del puerto de revisión de formatos mediante Agentes.

La integración es de una sola solicitud por invocación; no decide correcciones,
no evalúa y no persiste. Los HTTP 4xx/5xx con cuerpo contractual son resultados
fallidos del proveedor; los errores de transporte/contrato lanzan AgentRevisionError.
"""

from dataclasses import asdict

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.generated_content import (
    FlashcardsContent,
    GeneratedContent,
    QuizContent,
    TLDRContent,
    VideoScriptContent,
)
from app.domain.generated_format import ChunkEvidence
from app.ports.agent_revision_port import (
    AgentRevisionError,
    AgentRevisionFailure,
    AgentRevisionInput,
    AgentRevisionResult,
)


class _ChunkHTTPResponse(BaseModel):
    """Evidencia devuelta en sources_used, compatible con /generate."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    score: float
    text: str = Field(min_length=1)


class _ErrorHTTPResponse(BaseModel):
    """ErrorDetail canónico de Agentes."""

    model_config = ConfigDict(extra="ignore")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool
    http_status: int = Field(ge=400, le=599)
    upstream_status: int | None = None
    provider: str = Field(min_length=1)


class _RevisionHTTPResponse(BaseModel):
    """Respuesta de UN formato desde POST /api/v1/revise."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(min_length=1)
    format: GeneratedFormatType
    status: GeneratedFormatStatus
    content: dict[str, object] | None = None
    sources_used: list[_ChunkHTTPResponse] = Field(default_factory=list)
    error_message: str | None = None
    error: _ErrorHTTPResponse | None = None
    execution_time_seconds: float = Field(ge=0)


class HTTPAgentRevisionAdapter:
    """Implementa AgentRevisionPort usando un AsyncClient inyectado."""

    def __init__(self, *, client: httpx.AsyncClient, revise_path: str = "/api/v1/revise") -> None:
        if not revise_path.startswith("/"):
            raise ValueError("revise_path debe comenzar con '/'.")
        self._client = client
        self._revise_path = revise_path

    async def revise_format(self, request: AgentRevisionInput) -> AgentRevisionResult:
        """Envía una revisión, valida identidad y conserva errores por formato.

        Raises:
            AgentRevisionError: timeout, conexión, HTTP sin cuerpo contractual,
                respuesta incoherente o estructura de contenido inválida.
        """
        payload = self._build_request_payload(request)

        try:
            response = await self._client.post(self._revise_path, json=payload)
        except httpx.TimeoutException as exc:
            raise AgentRevisionError(
                f"La revisión del documento {request.document_id} superó el tiempo permitido."
            ) from exc
        except httpx.RequestError as exc:
            raise AgentRevisionError(
                f"No fue posible conectar con Agentes para revisar {request.document_id}."
            ) from exc

        try:
            body = _RevisionHTTPResponse.model_validate(response.json())
            self._validate_http_contract(response, body, request)
            content = self._deserialize_content(request.format_type, body.content)
            sources = tuple(
                ChunkEvidence(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    rank=chunk.rank,
                    score=chunk.score,
                    text=chunk.text,
                )
                for chunk in body.sources_used
            )
            error = (
                AgentRevisionFailure(**body.error.model_dump()) if body.error is not None else None
            )
            return AgentRevisionResult(
                document_id=body.document_id,
                format_type=body.format,
                status=body.status,
                content=content,
                chunks_used=sources,
                execution_time_seconds=body.execution_time_seconds,
                error_message=body.error_message,
                error=error,
            )
        except (AttributeError, ValueError, TypeError, KeyError, ValidationError) as exc:
            raise AgentRevisionError(
                f"Agentes devolvió una respuesta de revisión inválida "
                f"para {request.document_id} (HTTP {response.status_code})."
            ) from exc

    @staticmethod
    def _build_request_payload(request: AgentRevisionInput) -> dict[str, object]:
        """Serializa value objects internos al contrato HTTP V2 acordado."""
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
            "current_content": request.current_content.to_dict(),
            "generation_context": generation_context,
            "chunks_used": [chunk.to_dict() for chunk in request.chunks_used],
            "feedback": asdict(request.feedback),
        }

    @staticmethod
    def _validate_http_contract(
        response: httpx.Response,
        body: _RevisionHTTPResponse,
        request: AgentRevisionInput,
    ) -> None:
        """Impide aceptar estados, HTTP o identidades contradictorios."""
        if body.document_id != request.document_id or body.format != request.format_type:
            raise ValueError("Identidad de revisión diferente a la solicitada.")
        if response.status_code == 207:
            raise ValueError("/revise es una operación atómica: no admite HTTP 207.")
        if response.status_code == 200 and body.status != GeneratedFormatStatus.SUCCESS:
            raise ValueError("HTTP 200 requiere status success.")
        if response.status_code != 200 and body.status == GeneratedFormatStatus.SUCCESS:
            raise ValueError("Una revisión exitosa requiere HTTP 200.")
        if response.status_code != 200 and not 400 <= response.status_code <= 599:
            raise ValueError("Código HTTP no soportado para la revisión.")
        if body.status in (GeneratedFormatStatus.FAILED, GeneratedFormatStatus.NO_RESULTS):
            if body.error is None:
                raise ValueError("El fallo debe incluir error estructurado.")
            if response.status_code != body.error.http_status:
                raise ValueError("HTTP no coincide con error.http_status.")

    @staticmethod
    def _deserialize_content(
        format_type: GeneratedFormatType, content: dict[str, object] | None
    ) -> GeneratedContent | None:
        """Aplica validadores canónicos del dominio; no confía en JSON arbitrario."""
        if content is None:
            return None
        content_types = {
            GeneratedFormatType.QUIZ: QuizContent,
            GeneratedFormatType.FLASHCARDS: FlashcardsContent,
            GeneratedFormatType.TLDR: TLDRContent,
            GeneratedFormatType.VIDEO_SCRIPT: VideoScriptContent,
        }
        return content_types[format_type].from_dict(content)
