"""Adaptador HTTP para la integración de BackendAPI con Agentes."""

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    FlashcardsContent,
    GeneratedContent,
    QuizContent,
    TLDRContent,
    VideoScriptContent,
)
from app.domain.generated_format import ChunkEvidence
from app.domain.learning_metadata import LearningMetadata
from app.ports.agents_port import (
    AgentGeneratedFormatResult,
    AgentGenerationInput,
    AgentGenerationResult,
    AgentsError,
)


class _ChunkEvidenceHTTPResponse(BaseModel):
    """Evidencia retornada por Agentes en sources_used."""

    model_config = ConfigDict(
        extra="ignore",
    )

    chunk_id: str
    document_id: str
    rank: int
    score: float
    text: str


class _LearningMetadataHTTPResponse(BaseModel):
    """Metadata pedagógica retornada una sola vez por Agentes."""

    model_config = ConfigDict(
        extra="forbid",
    )

    key_concepts: list[str]
    prerequisites: list[str]
    estimated_time_minutes: int = Field(
        ge=0
    )

    def to_domain(self) -> LearningMetadata:
        """Convierte el contrato HTTP al value object del dominio."""
        return LearningMetadata(
            key_concepts=tuple(
                self.key_concepts
            ),
            prerequisites=tuple(
                self.prerequisites
            ),
            estimated_time_minutes=(
                self.estimated_time_minutes
            ),
        )


class _GeneratedFormatHTTPResult(BaseModel):
    """Resultado atómico retornado por /api/v1/generate."""

    model_config = ConfigDict(
        extra="ignore",
    )

    format: GeneratedFormatType
    status: GeneratedFormatStatus
    content: dict[str, object] | None = None
    sources_used: list[_ChunkEvidenceHTTPResponse] = Field(
        default_factory=list
    )
    error_message: str | None = None


class _AgentGenerationHTTPResponse(BaseModel):
    """Respuesta HTTP completa esperada desde Agentes."""

    model_config = ConfigDict(
        extra="ignore",
    )

    document_id: str
    learning_metadata: _LearningMetadataHTTPResponse
    results: list[_GeneratedFormatHTTPResult]


class HTTPAgentsAdapter:
    """Implementa AgentsPort mediante el endpoint HTTP de Agentes.

    El adapter traduce exclusivamente entre:

    - el contrato interno estable de BackendAPI;
    - el contrato HTTP público de Agentes.

    No contiene lógica de negocio, prompts, retrieval ni persistencia.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        generate_path: str,
    ) -> None:
        if not generate_path.startswith("/"):
            raise ValueError(
                "generate_path debe comenzar con '/'."
            )

        self._client = client
        self._generate_path = generate_path

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
        """Solicita formatos y metadata pedagógica a Agentes.

        Args:
            request: Solicitud normalizada construida por BackendAPI.

        Returns:
            Resultado de generación expresado mediante el dominio interno.

        Raises:
            AgentsError: Si ocurre un timeout, error HTTP, error de
                conexión o Agentes devuelve un contrato incompatible.
        """
        payload = self._build_request_payload(
            request
        )

        try:
            response = await self._client.post(
                self._generate_path,
                json=payload,
            )

            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise AgentsError(
                "La solicitud de generación a Agentes "
                f"superó el tiempo permitido para "
                f"{request.document_id}."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise AgentsError(
                "Agentes rechazó la generación del documento "
                f"{request.document_id} con estado HTTP "
                f"{exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise AgentsError(
                "No fue posible conectar con Agentes para generar "
                f"formatos del documento {request.document_id}."
            ) from exc

        try:
            payload_response = (
                _AgentGenerationHTTPResponse.model_validate(
                    response.json()
                )
            )

            results = tuple(
                self._to_domain_result(
                    item
                )
                for item in payload_response.results
            )

            return AgentGenerationResult(
                document_id=(
                    payload_response.document_id
                ),
                results=results,
                learning_metadata=(
                    payload_response
                    .learning_metadata
                    .to_domain()
                ),
            )

        except (
            KeyError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise AgentsError(
                "Agentes devolvió una respuesta de generación "
                f"inválida para el documento {request.document_id}."
            ) from exc

    @staticmethod
    def _build_request_payload(
        request: AgentGenerationInput,
    ) -> dict[str, object]:
        """Traduce el contrato interno al request HTTP de Agentes."""
        context = request.generation_context

        payload: dict[str, object] = {
            "document_id": request.document_id,
            "formats": [
                format_type.value
                for format_type in request.formats
            ],
            "profile": context.profile,
            "niche": context.niche,
            "detail_level": context.detail_level,
        }

        if context.learning_objective is not None:
            payload[
                "learning_objective"
            ] = context.learning_objective

        return payload

    @classmethod
    def _to_domain_result(
        cls,
        result: _GeneratedFormatHTTPResult,
    ) -> AgentGeneratedFormatResult:
        """Convierte un resultado HTTP al contrato interno de Backend."""
        content = cls._build_content(
            format_type=result.format,
            content=result.content,
        )

        chunks_used = tuple(
            ChunkEvidence(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                rank=chunk.rank,
                score=chunk.score,
                text=chunk.text,
            )
            for chunk in result.sources_used
        )

        return AgentGeneratedFormatResult(
            format_type=result.format,
            status=result.status,
            content=content,
            chunks_used=chunks_used,
            error_message=result.error_message,
        )

    @staticmethod
    def _build_content(
        *,
        format_type: GeneratedFormatType,
        content: dict[str, object] | None,
    ) -> GeneratedContent | None:
        """Construye contenido canónico según el formato solicitado."""
        if content is None:
            return None

        if (
            format_type
            == GeneratedFormatType.QUIZ
        ):
            return QuizContent.from_dict(
                content
            )

        if (
            format_type
            == GeneratedFormatType.FLASHCARDS
        ):
            return FlashcardsContent.from_dict(
                content
            )

        if (
            format_type
            == GeneratedFormatType.TLDR
        ):
            return TLDRContent.from_dict(
                content
            )

        if (
            format_type
            == GeneratedFormatType.VIDEO_SCRIPT
        ):
            return VideoScriptContent.from_dict(
                content
            )

        raise ValueError(
            f"Formato no soportado: {format_type}."
        )
