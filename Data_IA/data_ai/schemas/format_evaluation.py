"""
Schemas para la evaluación de formatos generados por NuevaMente.

Sprint 2:
- Formatos soportados: quiz y flashcards.
- Data/IA recibe:
    document_id
    format
    generated_content
    chunks_used
- El campo `format` discrimina automáticamente el tipo esperado de
  `generated_content`.

Requiere Pydantic v2.
"""

from typing import Annotated, List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Modelo base: no permite campos adicionales no definidos."""

    model_config = ConfigDict(extra="forbid")


class QuizQuestion(StrictModel):
    """Una pregunta individual del quiz."""

    question_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_length=2)
    correct_answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_question(self):
        cleaned_options = [option.strip() for option in self.options]

        if any(not option for option in cleaned_options):
            raise ValueError("Las opciones no pueden estar vacías.")

        if len(cleaned_options) != len(set(cleaned_options)):
            raise ValueError("Las opciones no deben contener duplicados.")

        if self.correct_answer.strip() not in cleaned_options:
            raise ValueError(
                "correct_answer debe coincidir con una de las opciones."
            )

        return self


class QuizContent(StrictModel):
    """Contenido generado para el formato quiz."""

    title: str = Field(..., min_length=1)
    instructions: str = Field(..., min_length=1)
    questions: List[QuizQuestion] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_question_ids(self):
        question_ids = [question.question_id for question in self.questions]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Los question_id deben ser únicos.")

        return self


class FlashcardItem(StrictModel):
    """Una flashcard individual."""

    card_id: str = Field(..., min_length=1)
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_flashcard(self):
        if self.front.strip() == self.back.strip():
            raise ValueError("front y back no deben ser idénticos.")

        return self


class FlashcardsContent(StrictModel):
    """Contenido generado para el formato flashcards."""

    title: str = Field(..., min_length=1)
    instructions: str = Field(..., min_length=1)
    cards: List[FlashcardItem] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_card_ids(self):
        card_ids = [card.card_id for card in self.cards]

        if len(card_ids) != len(set(card_ids)):
            raise ValueError("Los card_id deben ser únicos.")

        return self


class ChunkUsed(StrictModel):
    """Chunk recuperado por Agentes y utilizado como evidencia."""

    chunk_id: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    rank: int = Field(..., ge=1)
    score: float
    text: str = Field(..., min_length=1)


class EvaluationRequestBase(StrictModel):
    """Campos comunes a cualquier solicitud de evaluación."""

    document_id: str = Field(..., min_length=1)
    chunks_used: List[ChunkUsed] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_chunks(self):
        chunk_ids = [chunk.chunk_id for chunk in self.chunks_used]
        ranks = [chunk.rank for chunk in self.chunks_used]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("Los chunk_id de chunks_used deben ser únicos.")

        if len(ranks) != len(set(ranks)):
            raise ValueError("Los rank de chunks_used deben ser únicos.")

        invalid_document_ids = [
            chunk.chunk_id
            for chunk in self.chunks_used
            if chunk.document_id != self.document_id
        ]

        if invalid_document_ids:
            raise ValueError(
                "Todos los chunks_used deben pertenecer al document_id "
                f"de la solicitud. Chunks inválidos: {invalid_document_ids}"
            )

        return self


class QuizEvaluationRequest(EvaluationRequestBase):
    """Solicitud de evaluación para un quiz."""

    format: Literal["quiz"]
    generated_content: QuizContent


class FlashcardsEvaluationRequest(EvaluationRequestBase):
    """Solicitud de evaluación para flashcards."""

    format: Literal["flashcards"]
    generated_content: FlashcardsContent


EvaluationRequest = Annotated[
    Union[
        QuizEvaluationRequest,
        FlashcardsEvaluationRequest,
    ],
    Field(discriminator="format"),
]


__all__ = [
    "ChunkUsed",
    "EvaluationRequest",
    "EvaluationRequestBase",
    "FlashcardItem",
    "FlashcardsContent",
    "FlashcardsEvaluationRequest",
    "QuizContent",
    "QuizEvaluationRequest",
    "QuizQuestion",
]
