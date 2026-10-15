"""
Contrato V2 del Evaluador Semántico de Data/IA.

COPIA de los modelos Pydantic de DataIA_Semantic_Evaluator_Contract_V2.md (secciones 7 y 8). No se
modifican a mano: si Data publica una versión nueva, se reemplaza este archivo. Sirve para:

* validar localmente la petición ANTES de enviarla (el request de Data es extra="forbid": un campo
  de más, uno que falte o una cadena vacía devuelven 422);
* interpretar la respuesta con las mismas reglas de consistencia que usa Data.

Estado según el documento: el /evaluate público sigue devolviendo la respuesta V1.1 hasta que Data
complete la migración, así que una respuesta V1.1 NO valida como EvaluationResponseV2.
"""
from typing import Annotated, List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ======================================================================
# REQUEST (sección 7 del contrato)
# ======================================================================
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuizQuestion(StrictModel):
    question_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_length=2)
    correct_answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)


class QuizContent(StrictModel):
    title: str = Field(..., min_length=1)
    instructions: str = Field(..., min_length=1)
    questions: List[QuizQuestion] = Field(..., min_length=1)


class FlashcardItem(StrictModel):
    card_id: str = Field(..., min_length=1)
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)


class FlashcardsContent(StrictModel):
    title: str = Field(..., min_length=1)
    instructions: str = Field(..., min_length=1)
    cards: List[FlashcardItem] = Field(..., min_length=1)


class TLDRContent(StrictModel):
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    key_points: List[str] = Field(default_factory=list)
    conclusion: str = Field(..., min_length=1)


class VideoScriptScene(StrictModel):
    scene_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    visual_description: str = Field(..., min_length=1)
    narration: str = Field(..., min_length=1)
    duration_seconds: int = Field(default=0, ge=0)


class VideoScriptContent(StrictModel):
    title: str = Field(..., min_length=1)
    estimated_duration_minutes: int = Field(default=0, ge=0)
    scenes: List[VideoScriptScene] = Field(..., min_length=1)


class ChunkUsed(StrictModel):
    chunk_id: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    rank: int = Field(..., ge=1)
    score: float
    text: str = Field(..., min_length=1)


class GenerationContext(StrictModel):
    profile: str = Field(..., min_length=1)
    niche: str = Field(..., min_length=1)
    detail_level: str = Field(..., min_length=1)
    learning_objective: str | None = Field(default=None, min_length=1)


class EvaluationRequestBase(StrictModel):
    document_id: str = Field(..., min_length=1)
    generation_context: GenerationContext
    chunks_used: List[ChunkUsed] = Field(..., min_length=1)


class QuizEvaluationRequest(EvaluationRequestBase):
    format: Literal["quiz"]
    generated_content: QuizContent


class FlashcardsEvaluationRequest(EvaluationRequestBase):
    format: Literal["flashcards"]
    generated_content: FlashcardsContent


class TLDREvaluationRequest(EvaluationRequestBase):
    format: Literal["tldr"]
    generated_content: TLDRContent


class VideoScriptEvaluationRequest(EvaluationRequestBase):
    format: Literal["video_script"]
    generated_content: VideoScriptContent


EvaluationRequest = Annotated[
    Union[
        QuizEvaluationRequest,
        FlashcardsEvaluationRequest,
        TLDREvaluationRequest,
        VideoScriptEvaluationRequest,
    ],
    Field(discriminator="format"),
]


# ======================================================================
# RESPONSE V2 (sección 8 del contrato)
# ======================================================================
EvaluationVerdict = Literal[
    "approved",
    "requires_revision",
    "rejected",
]

SemanticDimension = Literal[
    "relevance",
    "coherence",
    "didactic_adaptation",
    "content_support",
]

SemanticSeverity = Literal[
    "low",
    "medium",
    "high",
]

SemanticStatus = Literal[
    "success",
    "failed",
    "unavailable",
]

SemanticErrorCode = Literal[
    "timeout",
    "provider_error",
    "invalid_output",
    "not_configured",
]


class HeuristicScoresV2(BaseModel):
    relevance: float = Field(..., ge=1.0, le=5.0)
    coherence: float = Field(..., ge=1.0, le=5.0)
    didactic_adaptation: float = Field(..., ge=1.0, le=5.0)
    content_support: float = Field(..., ge=1.0, le=5.0)


class SemanticScores(BaseModel):
    relevance: float = Field(..., ge=1.0, le=5.0)
    coherence: float = Field(..., ge=1.0, le=5.0)
    didactic_adaptation: float = Field(..., ge=1.0, le=5.0)
    content_support: float = Field(..., ge=1.0, le=5.0)


class SemanticObservation(BaseModel):
    dimension: SemanticDimension
    severity: SemanticSeverity
    message: str = Field(..., min_length=1)
    item_id: str | None = None


class SemanticRecommendation(BaseModel):
    dimension: SemanticDimension
    message: str = Field(..., min_length=1)
    item_id: str | None = None


class UnsupportedClaim(BaseModel):
    claim: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    item_id: str | None = None
    related_chunk_ids: list[str] = Field(default_factory=list)


class SemanticEvaluationResult(BaseModel):
    status: SemanticStatus
    scores: SemanticScores | None = None
    observations: list[SemanticObservation] = Field(default_factory=list)
    recommendations: list[SemanticRecommendation] = Field(default_factory=list)
    unsupported_information: list[UnsupportedClaim] = Field(default_factory=list)
    error_code: SemanticErrorCode | None = None
    error_message: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_status_consistency(self):
        if self.status == "success":
            if self.scores is None:
                raise ValueError("status='success' must include scores.")
            if self.error_code is not None:
                raise ValueError("status='success' must not include error_code.")

        elif self.status == "failed":
            if self.scores is not None:
                raise ValueError("status='failed' must not include scores.")
            if self.error_code is None:
                raise ValueError("status='failed' must include error_code.")
            if self.error_code == "not_configured":
                raise ValueError(
                    "not_configured must use status='unavailable'."
                )

        elif self.status == "unavailable":
            if self.scores is not None:
                raise ValueError("status='unavailable' must not include scores.")
            if self.error_code != "not_configured":
                raise ValueError(
                    "status='unavailable' must use not_configured."
                )

        return self


class EvaluationResponseV2(BaseModel):
    document_id: str = Field(..., min_length=1)
    format: Literal["quiz", "flashcards", "tldr", "video_script"]
    verdict: EvaluationVerdict | None = None
    heuristic_scores: HeuristicScoresV2 | None = None
    semantic_evaluation: SemanticEvaluationResult
    evaluator_version: str = Field(..., min_length=1)
    rubric_version: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_evaluation_consistency(self):
        has_heuristic_signal = self.heuristic_scores is not None
        has_semantic_signal = self.semantic_evaluation.status == "success"

        if (
            not (has_heuristic_signal or has_semantic_signal)
            and self.verdict is not None
        ):
            raise ValueError(
                "verdict must be None when neither heuristic "
                "nor semantic evaluation produced a valid signal."
            )

        return self
