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
    HeuristicScoresV2,
    SemanticEvaluationResult,
    SemanticObservation,
    SemanticRecommendation,
    SemanticScores,
    UnsupportedClaim,
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
    document_title: str | None = None
    document_description: str | None = None
    is_active: bool = True

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
            document_title=document.document_title,
            document_description=(
                document.document_description
            ),
            is_active=document.is_active,
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
            document_title=(
                row["document_title"]
                if "document_title" in tuple(row.keys())
                else None
            ),
            document_description=(
                row["document_description"]
                if "document_description" in tuple(row.keys())
                else None
            ),
            is_active=(
                bool(row["is_active"])
                if "is_active" in tuple(row.keys())
                else True
            ),
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
            document_title=self.document_title,
            document_description=(
                self.document_description
            ),
            is_active=self.is_active,
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
    revision_of_format_id: str | None = None

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
            revision_of_format_id=generated_format.revision_of_format_id,
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
            revision_of_format_id=row["revision_of_format_id"],
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
            revision_of_format_id=self.revision_of_format_id,
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


def _semantic_evaluation_to_dict(
    result: SemanticEvaluationResult,
) -> dict:
    """Serializa el resultado semántico V2 completo a un dict JSON-able."""
    return {
        "status": result.status,
        "scores": (
            {
                "relevance": result.scores.relevance,
                "coherence": result.scores.coherence,
                "didactic_adaptation": (
                    result.scores.didactic_adaptation
                ),
                "content_support": result.scores.content_support,
            }
            if result.scores is not None
            else None
        ),
        "observations": [
            {
                "dimension": observation.dimension,
                "severity": observation.severity,
                "message": observation.message,
                "item_id": observation.item_id,
            }
            for observation in result.observations
        ],
        "recommendations": [
            {
                "dimension": recommendation.dimension,
                "message": recommendation.message,
                "item_id": recommendation.item_id,
            }
            for recommendation in result.recommendations
        ],
        "unsupported_information": [
            {
                "claim": claim.claim,
                "reason": claim.reason,
                "item_id": claim.item_id,
                "related_chunk_ids": list(
                    claim.related_chunk_ids
                ),
            }
            for claim in result.unsupported_information
        ],
        "error_code": result.error_code,
        "error_message": result.error_message,
        "model": result.model,
        "prompt_version": result.prompt_version,
        "latency_ms": result.latency_ms,
    }


def _semantic_evaluation_from_dict(
    data: dict,
) -> SemanticEvaluationResult:
    """Reconstruye el resultado semántico V2 desde el dict persistido."""
    scores_data = data.get("scores")

    return SemanticEvaluationResult(
        status=data["status"],
        scores=(
            SemanticScores(
                relevance=scores_data["relevance"],
                coherence=scores_data["coherence"],
                didactic_adaptation=(
                    scores_data["didactic_adaptation"]
                ),
                content_support=(
                    scores_data["content_support"]
                ),
            )
            if scores_data is not None
            else None
        ),
        observations=tuple(
            SemanticObservation(
                dimension=observation["dimension"],
                severity=observation["severity"],
                message=observation["message"],
                item_id=observation.get("item_id"),
            )
            for observation in data.get(
                "observations", []
            )
        ),
        recommendations=tuple(
            SemanticRecommendation(
                dimension=recommendation["dimension"],
                message=recommendation["message"],
                item_id=recommendation.get("item_id"),
            )
            for recommendation in data.get(
                "recommendations", []
            )
        ),
        unsupported_information=tuple(
            UnsupportedClaim(
                claim=claim["claim"],
                reason=claim["reason"],
                item_id=claim.get("item_id"),
                related_chunk_ids=tuple(
                    claim.get(
                        "related_chunk_ids", []
                    )
                ),
            )
            for claim in data.get(
                "unsupported_information", []
            )
        ),
        error_code=data.get("error_code"),
        error_message=data.get("error_message"),
        model=data.get("model"),
        prompt_version=data.get("prompt_version"),
        latency_ms=data.get("latency_ms"),
    )


def _heuristic_scores_v2_to_dict(
    scores: HeuristicScoresV2,
) -> dict:
    """Serializa los scores heurísticos V2 (float) a un dict JSON-able."""
    return {
        "relevance": scores.relevance,
        "coherence": scores.coherence,
        "didactic_adaptation": scores.didactic_adaptation,
        "content_support": scores.content_support,
    }


def _heuristic_scores_v2_from_dict(
    data: dict,
) -> HeuristicScoresV2:
    """Reconstruye los scores heurísticos V2 desde el dict persistido."""
    return HeuristicScoresV2(
        relevance=data["relevance"],
        coherence=data["coherence"],
        didactic_adaptation=data["didactic_adaptation"],
        content_support=data["content_support"],
    )


@dataclass(frozen=True, slots=True)
class FormatEvaluationRecord:
    """Representación persistible de una evaluación (V1 y V2).

    Los campos V1 (``status`` en adelante hasta ``content_support_score``)
    son ``None`` en una evaluación V2 "pura". Los campos V2 (``verdict``
    en adelante) son ``None`` en una evaluación V1 histórica.
    """

    evaluation_id: str
    format_id: str

    # V1 (heurístico 1.1) — nullable para admitir evaluaciones V2 puras
    status: str | None
    relevance_score: int | None
    coherence_score: int | None
    didactic_adaptation_score: int | None
    content_support_score: int | None
    unsupported_information: int
    observations_json: str

    evaluator_version: str | None
    rubric_version: str | None

    # V2 (Sprint 4) — nullable para admitir evaluaciones V1 históricas
    verdict: str | None
    heuristic_scores_json: str | None
    semantic_evaluation_json: str | None

    created_at: str

    @classmethod
    def from_domain(
        cls,
        evaluation: FormatEvaluation,
    ) -> "FormatEvaluationRecord":
        """Convierte evaluación a persistencia."""
        scores = evaluation.scores

        return cls(
            evaluation_id=evaluation.evaluation_id,
            format_id=evaluation.format_id,
            status=(
                evaluation.status.value
                if evaluation.status is not None
                else None
            ),
            relevance_score=(
                scores.relevance
                if scores is not None
                else None
            ),
            coherence_score=(
                scores.coherence
                if scores is not None
                else None
            ),
            didactic_adaptation_score=(
                scores.didactic_adaptation
                if scores is not None
                else None
            ),
            content_support_score=(
                scores.content_support
                if scores is not None
                else None
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
            verdict=evaluation.verdict,
            heuristic_scores_json=(
                json.dumps(
                    _heuristic_scores_v2_to_dict(
                        evaluation.heuristic_scores
                    ),
                    ensure_ascii=False,
                )
                if evaluation.heuristic_scores
                is not None
                else None
            ),
            semantic_evaluation_json=(
                json.dumps(
                    _semantic_evaluation_to_dict(
                        evaluation.semantic_evaluation
                    ),
                    ensure_ascii=False,
                )
                if evaluation.semantic_evaluation
                is not None
                else None
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
            verdict=row["verdict"],
            heuristic_scores_json=row[
                "heuristic_scores_json"
            ],
            semantic_evaluation_json=row[
                "semantic_evaluation_json"
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

        has_v1_scores = (
            self.relevance_score is not None
        )

        return FormatEvaluation(
            evaluation_id=self.evaluation_id,
            format_id=self.format_id,
            status=(
                FormatEvaluationStatus(
                    self.status
                )
                if self.status is not None
                else None
            ),
            scores=(
                EvaluationScores(
                    relevance=self.relevance_score,
                    coherence=self.coherence_score,
                    didactic_adaptation=(
                        self
                        .didactic_adaptation_score
                    ),
                    content_support=(
                        self.content_support_score
                    ),
                )
                if has_v1_scores
                else None
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
            verdict=self.verdict,
            heuristic_scores=(
                _heuristic_scores_v2_from_dict(
                    json.loads(
                        self.heuristic_scores_json
                    )
                )
                if self.heuristic_scores_json
                is not None
                else None
            ),
            semantic_evaluation=(
                _semantic_evaluation_from_dict(
                    json.loads(
                        self
                        .semantic_evaluation_json
                    )
                )
                if self.semantic_evaluation_json
                is not None
                else None
            ),
            created_at=datetime.fromisoformat(
                self.created_at
            ),
        )
