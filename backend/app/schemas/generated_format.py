"""Schemas HTTP de formatos educativos generados."""

from pydantic import Field

from app.domain.enums import (
    DocumentFormatsStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    FlashcardItem,
    FlashcardsContent,
    QuizContent,
    QuizQuestion,
    TLDRContent,
    VideoScriptContent,
    VideoScriptScene,
)
from app.domain.generated_format import (
    GeneratedFormat,
)
from app.schemas.common import BaseSchema


class QuizQuestionResponse(BaseSchema):
    """Pregunta individual expuesta a Frontend."""

    question_id: str = Field(
        min_length=1,
    )
    question: str = Field(
        min_length=1,
    )
    options: list[str] = Field(
        min_length=2,
    )
    correct_answer: str = Field(
        min_length=1,
    )
    explanation: str = Field(
        min_length=1,
    )

    @classmethod
    def from_domain(
        cls,
        question: QuizQuestion,
    ) -> "QuizQuestionResponse":
        """Convierte una pregunta canónica al contrato HTTP."""
        return cls(
            question_id=question.question_id,
            question=question.question,
            options=list(
                question.options
            ),
            correct_answer=question.correct_answer,
            explanation=question.explanation,
        )


class QuizContentResponse(BaseSchema):
    """Contenido HTTP correspondiente a un Quiz."""

    title: str = Field(
        min_length=1,
    )
    instructions: str = Field(
        min_length=1,
    )
    questions: list[
        QuizQuestionResponse
    ]

    @classmethod
    def from_domain(
        cls,
        content: QuizContent,
    ) -> "QuizContentResponse":
        """Convierte QuizContent al contrato HTTP."""
        return cls(
            title=content.title,
            instructions=content.instructions,
            questions=[
                QuizQuestionResponse.from_domain(
                    question
                )
                for question
                in content.questions
            ],
        )


class FlashcardItemResponse(BaseSchema):
    """Flashcard individual expuesta a Frontend."""

    card_id: str = Field(
        min_length=1,
    )
    front: str = Field(
        min_length=1,
    )
    back: str = Field(
        min_length=1,
    )

    @classmethod
    def from_domain(
        cls,
        card: FlashcardItem,
    ) -> "FlashcardItemResponse":
        """Convierte una Flashcard canónica al contrato HTTP."""
        return cls(
            card_id=card.card_id,
            front=card.front,
            back=card.back,
        )


class FlashcardsContentResponse(BaseSchema):
    """Contenido HTTP correspondiente a Flashcards."""

    title: str = Field(
        min_length=1,
    )
    instructions: str = Field(
        min_length=1,
    )
    cards: list[
        FlashcardItemResponse
    ]

    @classmethod
    def from_domain(
        cls,
        content: FlashcardsContent,
    ) -> "FlashcardsContentResponse":
        """Convierte FlashcardsContent al contrato HTTP."""
        return cls(
            title=content.title,
            instructions=content.instructions,
            cards=[
                FlashcardItemResponse.from_domain(
                    card
                )
                for card
                in content.cards
            ],
        )


class TLDRContentResponse(BaseSchema):
    """Resumen ejecutivo expuesto a Frontend."""

    title: str = Field(
        min_length=1,
    )
    summary: str = Field(
        min_length=1,
    )
    key_points: list[str]
    conclusion: str = Field(
        min_length=1,
    )

    @classmethod
    def from_domain(
        cls,
        content: TLDRContent,
    ) -> "TLDRContentResponse":
        """Convierte TLDRContent al contrato HTTP."""
        return cls(
            title=content.title,
            summary=content.summary,
            key_points=list(
                content.key_points
            ),
            conclusion=content.conclusion,
        )


class VideoScriptSceneResponse(BaseSchema):
    """Escena individual de un guion de video."""

    scene_id: str = Field(
        min_length=1,
    )
    title: str = Field(
        min_length=1,
    )
    visual_description: str = Field(
        min_length=1,
    )
    narration: str = Field(
        min_length=1,
    )
    duration_seconds: int = Field(
        ge=0,
    )

    @classmethod
    def from_domain(
        cls,
        scene: VideoScriptScene,
    ) -> "VideoScriptSceneResponse":
        """Convierte una escena canónica al contrato HTTP."""
        return cls(
            scene_id=scene.scene_id,
            title=scene.title,
            visual_description=(
                scene.visual_description
            ),
            narration=scene.narration,
            duration_seconds=(
                scene.duration_seconds
            ),
        )


class VideoScriptContentResponse(BaseSchema):
    """Guion de video expuesto a Frontend."""

    title: str = Field(
        min_length=1,
    )
    estimated_duration_minutes: int = Field(
        ge=0,
    )
    scenes: list[
        VideoScriptSceneResponse
    ] = Field(
        min_length=1,
    )

    @classmethod
    def from_domain(
        cls,
        content: VideoScriptContent,
    ) -> "VideoScriptContentResponse":
        """Convierte VideoScriptContent al contrato HTTP."""
        return cls(
            title=content.title,
            estimated_duration_minutes=(
                content.estimated_duration_minutes
            ),
            scenes=[
                VideoScriptSceneResponse.from_domain(
                    scene
                )
                for scene
                in content.scenes
            ],
        )


GeneratedContentResponse = (
    QuizContentResponse
    | FlashcardsContentResponse
    | TLDRContentResponse
    | VideoScriptContentResponse
)


class GeneratedFormatResponse(BaseSchema):
    """Resultado público de un formato generado."""

    format_id: str = Field(
        min_length=1,
    )
    status: GeneratedFormatStatus
    content: GeneratedContentResponse | None = None
    error_message: str | None = None

    @classmethod
    def from_domain(
        cls,
        generated_format: GeneratedFormat,
    ) -> "GeneratedFormatResponse":
        """Convierte GeneratedFormat al contrato HTTP."""
        content = generated_format.content

        if isinstance(
            content,
            QuizContent,
        ):
            response_content: (
                GeneratedContentResponse
                | None
            ) = (
                QuizContentResponse.from_domain(
                    content
                )
            )

        elif isinstance(
            content,
            FlashcardsContent,
        ):
            response_content = (
                FlashcardsContentResponse.from_domain(
                    content
                )
            )

        elif isinstance(
            content,
            TLDRContent,
        ):
            response_content = (
                TLDRContentResponse.from_domain(
                    content
                )
            )

        elif isinstance(
            content,
            VideoScriptContent,
        ):
            response_content = (
                VideoScriptContentResponse.from_domain(
                    content
                )
            )

        else:
            response_content = None

        return cls(
            format_id=generated_format.format_id,
            status=generated_format.status,
            content=response_content,
            error_message=generated_format.error_message,
        )


class DocumentFormatsResponse(BaseSchema):
    """Formatos pedagógicos disponibles de un documento."""

    document_id: str = Field(
        min_length=1,
    )
    status: DocumentFormatsStatus
    formats: dict[
        GeneratedFormatType,
        GeneratedFormatResponse,
    ] | None = None
