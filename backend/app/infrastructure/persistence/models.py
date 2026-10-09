"""Modelos y conversiones utilizadas por la persistencia."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.domain.document import Document
from app.domain.enums import (
    DocumentStatus,
    FormatEvaluationStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.format_evaluation import (
    EvaluationScores,
    FormatEvaluation,
)
from app.domain.generated_content import (
    FlashcardsContent,
    GeneratedContent,
    QuizContent,
    TLDRContent,
    VideoScriptContent,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.domain.learning_metadata import LearningMetadata


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """Representación persistible de un documento."""

    document_id: str
    original_filename: str
    sha256: str
    content_type: str | None
    size_bytes: int
    status: str
    oci_object_name: str | None
    learning_metadata_json: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(
        cls,
        document: Document,
    ) -> "DocumentRecord":
        """Convierte una entidad de dominio en un registro persistible."""
        return cls(
            document_id=document.document_id,
            original_filename=document.original_filename,
            sha256=document.sha256,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            status=document.status.value,
            oci_object_name=document.oci_object_name,
            learning_metadata_json=(
                json.dumps(
                    document.learning_metadata.to_dict(),
                    ensure_ascii=False,
                )
                if document.learning_metadata
                is not None
                else None
            ),
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )

    @classmethod
    def from_row(
        cls,
        row: sqlite3.Row,
    ) -> "DocumentRecord":
        """Construye un registro a partir de una fila SQLite."""
        return cls(
            document_id=row["document_id"],
            original_filename=row["original_filename"],
            sha256=row["sha256"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            status=row["status"],
            oci_object_name=row["oci_object_name"],
            learning_metadata_json=row[
                "learning_metadata_json"
            ],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_domain(
        self,
    ) -> Document:
        """Convierte el registro persistido en una entidad de dominio."""
        return Document(
            document_id=self.document_id,
            original_filename=self.original_filename,
            sha256=self.sha256,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            status=DocumentStatus(
                self.status
            ),
            oci_object_name=self.oci_object_name,
            learning_metadata=(
                self._deserialize_learning_metadata()
            ),
            created_at=datetime.fromisoformat(
                self.created_at
            ),
            updated_at=datetime.fromisoformat(
                self.updated_at
            ),
        )

    def _deserialize_learning_metadata(
        self,
    ) -> LearningMetadata | None:
        """Reconstruye la metadata pedagógica persistida del documento."""
        if self.learning_metadata_json is None:
            return None

        data = json.loads(
            self.learning_metadata_json
        )

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "learning_metadata_json debe representar un objeto."
            )

        return LearningMetadata.from_dict(
            data
        )


@dataclass(frozen=True, slots=True)
class GeneratedFormatRecord:
    """Representación persistible de un formato generado."""

    format_id: str
    document_id: str
    format_type: str
    status: str
    content_json: str | None
    chunks_used_json: str
    profile: str
    niche: str
    detail_level: str
    learning_objective: str | None
    error_message: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(
        cls,
        generated_format: GeneratedFormat,
    ) -> "GeneratedFormatRecord":
        """Convierte una generación a representación SQLite."""
        return cls(
            format_id=generated_format.format_id,
            document_id=generated_format.document_id,
            format_type=generated_format.format_type.value,
            status=generated_format.status.value,
            content_json=(
                json.dumps(
                    generated_format.content.to_dict(),
                    ensure_ascii=False,
                )
                if generated_format.content
                is not None
                else None
            ),
            chunks_used_json=json.dumps(
                [
                    chunk.to_dict()
                    for chunk
                    in generated_format.chunks_used
                ],
                ensure_ascii=False,
            ),
            profile=(
                generated_format
                .generation_context
                .profile
            ),
            niche=(
                generated_format
                .generation_context
                .niche
            ),
            detail_level=(
                generated_format
                .generation_context
                .detail_level
            ),
            learning_objective=(
                generated_format
                .generation_context
                .learning_objective
            ),
            error_message=(
                generated_format.error_message
            ),
            created_at=(
                generated_format
                .created_at
                .isoformat()
            ),
            updated_at=(
                generated_format
                .updated_at
                .isoformat()
            ),
        )

    @classmethod
    def from_row(
        cls,
        row: sqlite3.Row,
    ) -> "GeneratedFormatRecord":
        """Construye un registro desde SQLite."""
        return cls(
            format_id=row["format_id"],
            document_id=row["document_id"],
            format_type=row["format_type"],
            status=row["status"],
            content_json=row["content_json"],
            chunks_used_json=row[
                "chunks_used_json"
            ],
            profile=row["profile"],
            niche=row["niche"],
            detail_level=row["detail_level"],
            learning_objective=row[
                "learning_objective"
            ],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_domain(
        self,
    ) -> GeneratedFormat:
        """Convierte persistencia a entidad GeneratedFormat."""
        format_type = GeneratedFormatType(
            self.format_type
        )

        content = self._deserialize_content(
            format_type
        )

        chunks_used = (
            self._deserialize_chunks_used()
        )

        return GeneratedFormat(
            format_id=self.format_id,
            document_id=self.document_id,
            format_type=format_type,
            status=GeneratedFormatStatus(
                self.status
            ),
            generation_context=GenerationContext(
                profile=self.profile,
                niche=self.niche,
                detail_level=self.detail_level,
                learning_objective=(
                    self.learning_objective
                ),
            ),
            content=content,
            chunks_used=chunks_used,
            error_message=self.error_message,
            created_at=datetime.fromisoformat(
                self.created_at
            ),
            updated_at=datetime.fromisoformat(
                self.updated_at
            ),
        )

    def _deserialize_content(
        self,
        format_type: GeneratedFormatType,
    ) -> GeneratedContent | None:
        """Reconstruye el contrato canónico según el formato."""
        if self.content_json is None:
            return None

        data = json.loads(
            self.content_json
        )

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "content_json debe representar un objeto."
            )

        if (
            format_type
            == GeneratedFormatType.QUIZ
        ):
            return QuizContent.from_dict(
                data
            )

        if (
            format_type
            == GeneratedFormatType.FLASHCARDS
        ):
            return FlashcardsContent.from_dict(
                data
            )

        if (
            format_type
            == GeneratedFormatType.TLDR
        ):
            return TLDRContent.from_dict(
                data
            )

        if (
            format_type
            == GeneratedFormatType.VIDEO_SCRIPT
        ):
            return VideoScriptContent.from_dict(
                data
            )

        raise ValueError(
            f"Formato persistido no soportado: {format_type}."
        )

    def _deserialize_chunks_used(
        self,
    ) -> tuple[ChunkEvidence, ...]:
        """Reconstruye íntegramente las evidencias persistidas."""
        chunks_data = json.loads(
            self.chunks_used_json
        )

        if not isinstance(
            chunks_data,
            list,
        ):
            raise ValueError(
                "chunks_used_json debe representar una lista."
            )

        parsed_chunks: list[
            ChunkEvidence
        ] = []

        for index, chunk in enumerate(
            chunks_data
        ):
            if not isinstance(
                chunk,
                dict,
            ):
                raise ValueError(
                    f"chunks_used_json[{index}] "
                    "debe representar un objeto."
                )

            parsed_chunks.append(
                ChunkEvidence.from_dict(
                    chunk
                )
            )

        return tuple(
            parsed_chunks
        )


@dataclass(frozen=True, slots=True)
class FormatEvaluationRecord:
    """Representación persistible de una evaluación."""

    evaluation_id: str
    format_id: str
    status: str
    relevance_score: int
    coherence_score: int
    didactic_adaptation_score: int
    content_support_score: int
    unsupported_information: int
    observations_json: str
    evaluator_version: str | None
    rubric_version: str | None
    created_at: str

    @classmethod
    def from_domain(
        cls,
        evaluation: FormatEvaluation,
    ) -> "FormatEvaluationRecord":
        """Convierte evaluación a persistencia."""
        return cls(
            evaluation_id=evaluation.evaluation_id,
            format_id=evaluation.format_id,
            status=evaluation.status.value,
            relevance_score=(
                evaluation.scores.relevance
            ),
            coherence_score=(
                evaluation.scores.coherence
            ),
            didactic_adaptation_score=(
                evaluation
                .scores
                .didactic_adaptation
            ),
            content_support_score=(
                evaluation.scores.content_support
            ),
            unsupported_information=int(
                evaluation
                .unsupported_information
            ),
            observations_json=json.dumps(
                list(
                    evaluation.observations
                ),
                ensure_ascii=False,
            ),
            evaluator_version=(
                evaluation.evaluator_version
            ),
            rubric_version=(
                evaluation.rubric_version
            ),
            created_at=(
                evaluation
                .created_at
                .isoformat()
            ),
        )

    @classmethod
    def from_row(
        cls,
        row: sqlite3.Row,
    ) -> "FormatEvaluationRecord":
        """Construye un registro desde SQLite."""
        return cls(
            evaluation_id=row[
                "evaluation_id"
            ],
            format_id=row["format_id"],
            status=row["status"],
            relevance_score=row[
                "relevance_score"
            ],
            coherence_score=row[
                "coherence_score"
            ],
            didactic_adaptation_score=row[
                "didactic_adaptation_score"
            ],
            content_support_score=row[
                "content_support_score"
            ],
            unsupported_information=row[
                "unsupported_information"
            ],
            observations_json=row[
                "observations_json"
            ],
            evaluator_version=row[
                "evaluator_version"
            ],
            rubric_version=row[
                "rubric_version"
            ],
            created_at=row["created_at"],
        )

    def to_domain(
        self,
    ) -> FormatEvaluation:
        """Convierte el registro persistido a dominio."""
        observations = json.loads(
            self.observations_json
        )

        if not isinstance(
            observations,
            list,
        ):
            raise ValueError(
                "observations_json debe representar una lista."
            )

        return FormatEvaluation(
            evaluation_id=self.evaluation_id,
            format_id=self.format_id,
            status=FormatEvaluationStatus(
                self.status
            ),
            scores=EvaluationScores(
                relevance=self.relevance_score,
                coherence=self.coherence_score,
                didactic_adaptation=(
                    self
                    .didactic_adaptation_score
                ),
                content_support=(
                    self.content_support_score
                ),
            ),
            unsupported_information=bool(
                self.unsupported_information
            ),
            observations=tuple(
                str(observation)
                for observation in observations
            ),
            evaluator_version=(
                self.evaluator_version
            ),
            rubric_version=(
                self.rubric_version
            ),
            created_at=datetime.fromisoformat(
                self.created_at
            ),
        )
