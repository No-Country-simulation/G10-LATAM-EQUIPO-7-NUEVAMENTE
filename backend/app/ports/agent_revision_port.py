"""Puerto tipado para revisar UN formato mediante el proveedor Agentes.

La capa de aplicación utiliza el protocolo, nunca HTTP ni estructuras
internas de LangGraph. No controla el presupuesto de correcciones.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from app.domain.enums import GeneratedFormatStatus, GeneratedFormatType
from app.domain.generated_content import (
    FlashcardsContent,
    GeneratedContent,
    QuizContent,
    TLDRContent,
    VideoScriptContent,
)
from app.domain.generated_format import ChunkEvidence, GenerationContext
from app.domain.revision_feedback import RevisionFeedback


class AgentRevisionError(Exception):
    """Error de transporte o incumplimiento del contrato externo."""


@dataclass(frozen=True, slots=True)
class AgentRevisionInput:
    """Solicitud de corrección de una versión pedagógica existente."""

    document_id: str
    format_type: GeneratedFormatType
    current_content: GeneratedContent
    generation_context: GenerationContext
    chunks_used: tuple[ChunkEvidence, ...]
    feedback: RevisionFeedback

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id es obligatorio.")
        expected_content_types = {
            GeneratedFormatType.QUIZ: QuizContent,
            GeneratedFormatType.FLASHCARDS: FlashcardsContent,
            GeneratedFormatType.TLDR: TLDRContent,
            GeneratedFormatType.VIDEO_SCRIPT: VideoScriptContent,
        }
        if not isinstance(self.current_content, expected_content_types[self.format_type]):
            raise ValueError("current_content no coincide con el formato solicitado.")
        if not self.chunks_used:
            raise ValueError("La revisión requiere al menos una evidencia factual.")
        if any(chunk.document_id != self.document_id for chunk in self.chunks_used):
            raise ValueError("Todos los chunks deben pertenecer al documento solicitado.")
        ids = [chunk.chunk_id for chunk in self.chunks_used]
        ranks = [chunk.rank for chunk in self.chunks_used]
        if len(ids) != len(set(ids)) or len(ranks) != len(set(ranks)):
            raise ValueError("Los chunk_id y rank deben ser únicos.")


@dataclass(frozen=True, slots=True)
class AgentRevisionFailure:
    """Error estructurado ya normalizado por Agentes."""

    code: str
    message: str
    retryable: bool
    http_status: int
    provider: str
    upstream_status: int | None = None

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip() or not self.provider.strip():
            raise ValueError("El error debe incluir code, message y provider.")
        if not 400 <= self.http_status <= 599:
            raise ValueError("http_status debe representar un error HTTP.")


@dataclass(frozen=True, slots=True)
class AgentRevisionResult:
    """Respuesta atómica; los fallos no sustituyen contenido previo."""

    document_id: str
    format_type: GeneratedFormatType
    status: GeneratedFormatStatus
    content: GeneratedContent | None
    chunks_used: tuple[ChunkEvidence, ...]
    execution_time_seconds: float
    error_message: str | None = None
    error: AgentRevisionFailure | None = None

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id es obligatorio.")
        if not isfinite(self.execution_time_seconds) or self.execution_time_seconds < 0:
            raise ValueError("execution_time_seconds debe ser finito y no negativo.")
        if self.status == GeneratedFormatStatus.SUCCESS:
            expected_content_types = {
                GeneratedFormatType.QUIZ: QuizContent,
                GeneratedFormatType.FLASHCARDS: FlashcardsContent,
                GeneratedFormatType.TLDR: TLDRContent,
                GeneratedFormatType.VIDEO_SCRIPT: VideoScriptContent,
            }
            if self.content is not None and not isinstance(
                self.content, expected_content_types[self.format_type]
            ):
                raise ValueError("La corrección devolvió contenido de otro formato.")
            if self.content is None or not self.chunks_used:
                raise ValueError("La corrección exitosa requiere contenido y fuentes completas.")
            if self.error is not None or self.error_message is not None:
                raise ValueError("Una corrección exitosa no puede contener errores.")
        elif self.status in (GeneratedFormatStatus.FAILED, GeneratedFormatStatus.NO_RESULTS):
            if self.content is not None or self.chunks_used:
                raise ValueError("Una corrección fallida no debe reemplazar contenido existente.")
        else:
            raise ValueError("La revisión solo puede devolver un estado terminal.")
        ids = [chunk.chunk_id for chunk in self.chunks_used]
        ranks = [chunk.rank for chunk in self.chunks_used]
        if len(ids) != len(set(ids)) or len(ranks) != len(set(ranks)):
            raise ValueError("Evidencias repetidas en la revisión.")
        if any(chunk.document_id != self.document_id for chunk in self.chunks_used):
            raise ValueError("Evidencias de otro documento en la revisión.")


class AgentRevisionPort(Protocol):
    """Contrato interno invocable por los casos de uso de BackendAPI."""

    async def revise_format(self, request: AgentRevisionInput) -> AgentRevisionResult:
        """Solicita una corrección sin hacer evaluación, persistencia o reintentos."""
        ...
