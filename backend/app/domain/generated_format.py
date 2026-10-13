"""Entidades asociadas a formatos educativos generados."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

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


@dataclass(frozen=True, slots=True)
class GenerationContext:
    """Snapshot del contexto pedagógico usado durante generación."""

    profile: str
    niche: str
    detail_level: str
    learning_objective: str | None = None

    def __post_init__(self) -> None:
        if not self.profile.strip():
            raise ValueError(
                "profile no puede estar vacío."
            )

        if not self.niche.strip():
            raise ValueError(
                "niche no puede estar vacío."
            )

        if not self.detail_level.strip():
            raise ValueError(
                "detail_level no puede estar vacío."
            )

        if (
            self.learning_objective is not None
            and not self.learning_objective.strip()
        ):
            raise ValueError(
                "learning_objective no puede estar vacío."
            )


@dataclass(frozen=True, slots=True)
class ChunkEvidence:
    """Evidencia exacta utilizada por Agentes durante la generación."""

    chunk_id: str
    document_id: str
    rank: int
    score: float
    text: str

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError(
                "chunk_id no puede estar vacío."
            )

        if not self.document_id.strip():
            raise ValueError(
                "document_id no puede estar vacío."
            )

        if self.rank < 1:
            raise ValueError(
                "rank debe ser mayor o igual a 1."
            )

        if not self.text.strip():
            raise ValueError(
                "text no puede estar vacío."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte la evidencia a JSON."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "rank": self.rank,
            "score": self.score,
            "text": self.text,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "ChunkEvidence":
        """Construye evidencia desde JSON."""
        return cls(
            chunk_id=str(
                data["chunk_id"]
            ),
            document_id=str(
                data["document_id"]
            ),
            rank=int(
                data["rank"]
            ),
            score=float(
                data["score"]
            ),
            text=str(
                data["text"]
            ),
        )


@dataclass(frozen=True, slots=True)
class GeneratedFormat:
    """Generación persistible producida por Agentes.

    Una generación exitosa debe incluir tanto contenido válido como
    las evidencias completas utilizadas durante retrieval. Backend no
    debe consultar directamente el Vector Store para reconstruirlas.
    """

    format_id: str
    document_id: str
    format_type: GeneratedFormatType
    status: GeneratedFormatStatus
    generation_context: GenerationContext

    content: GeneratedContent | None = None
    chunks_used: tuple[ChunkEvidence, ...] = ()
    error_message: str | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.format_id.strip():
            raise ValueError(
                "format_id no puede estar vacío."
            )

        if not self.document_id.strip():
            raise ValueError(
                "document_id no puede estar vacío."
            )

        self._validate_processing_contract()
        self._validate_success_contract()
        self._validate_evidence()

    def _validate_processing_contract(
        self,
    ) -> None:
        """Valida que un intento en proceso no tenga resultado todavía."""
        if (
            self.status
            != GeneratedFormatStatus.PROCESSING
        ):
            return

        if self.content is not None:
            raise ValueError(
                "Una generación processing no puede incluir content."
            )

        if self.chunks_used:
            raise ValueError(
                "Una generación processing no puede incluir chunks_used."
            )

        if self.error_message is not None:
            raise ValueError(
                "Una generación processing no puede incluir error_message."
            )

    def _validate_success_contract(
        self,
    ) -> None:
        """Valida el contenido exitoso según su tipo de formato."""
        if (
            self.status
            != GeneratedFormatStatus.SUCCESS
        ):
            return

        if self.content is None:
            raise ValueError(
                "Una generación exitosa debe incluir content."
            )

        if not self.chunks_used:
            raise ValueError(
                "Una generación exitosa debe incluir chunks_used completos."
            )

        expected_content_types = {
            GeneratedFormatType.QUIZ: QuizContent,
            GeneratedFormatType.FLASHCARDS: (
                FlashcardsContent
            ),
            GeneratedFormatType.TLDR: TLDRContent,
            GeneratedFormatType.VIDEO_SCRIPT: (
                VideoScriptContent
            ),
        }

        expected_content_type = (
            expected_content_types[
                self.format_type
            ]
        )

        if not isinstance(
            self.content,
            expected_content_type,
        ):
            raise ValueError(
                "El contenido de "
                f"{self.format_type.value} debe cumplir "
                f"{expected_content_type.__name__}."
            )

    def _validate_evidence(
        self,
    ) -> None:
        """Valida identidad y orden de las evidencias utilizadas."""
        chunk_ids = [
            chunk.chunk_id
            for chunk in self.chunks_used
        ]

        ranks = [
            chunk.rank
            for chunk in self.chunks_used
        ]

        if (
            len(chunk_ids)
            != len(set(chunk_ids))
        ):
            raise ValueError(
                "Los chunk_id de chunks_used deben ser únicos."
            )

        if (
            len(ranks)
            != len(set(ranks))
        ):
            raise ValueError(
                "Los rank de chunks_used deben ser únicos."
            )

        invalid_chunks = [
            chunk.chunk_id
            for chunk in self.chunks_used
            if (
                chunk.document_id
                != self.document_id
            )
        ]

        if invalid_chunks:
            raise ValueError(
                "Todos los chunks_used deben pertenecer al "
                "document_id de la generación. "
                f"Chunks inválidos: {invalid_chunks}"
            )

    @property
    def is_evaluation_ready(self) -> bool:
        """Indica si Data/IA puede evaluar inmediatamente la generación."""
        return (
            self.status
            == GeneratedFormatStatus.SUCCESS
            and self.content is not None
            and bool(self.chunks_used)
        )
