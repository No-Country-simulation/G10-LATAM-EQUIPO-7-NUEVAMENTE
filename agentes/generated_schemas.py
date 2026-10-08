from typing import List

from pydantic import BaseModel, Field


class LearningMetadata(BaseModel):
    key_concepts: List[str] = Field(
        ...,
        description="Lista de 3 a 5 conceptos clave abordados en el contenido.",
    )
    prerequisites: List[str] = Field(
        ...,
        description="Conocimientos previos recomendados para entender el tema.",
    )
    estimated_time_minutes: int = Field(
        ...,
        description="Tiempo estimado de estudio o lectura en minutos.",
    )


class CardItem(BaseModel):
    card_id: str = Field(
        ...,
        description="Identificador único de la tarjeta.",
    )
    front: str = Field(
        ...,
        description="Concepto o pregunta.",
    )
    back: str = Field(
        ...,
        description="Definición o respuesta.",
    )


class FlashcardsContent(BaseModel):
    title: str
    instructions: str
    cards: List[CardItem]


class QuizItem(BaseModel):
    question_id: str
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


class QuizContent(BaseModel):
    title: str
    instructions: str
    questions: List[QuizItem]


class TLDRContent(BaseModel):
    title: str
    summary: str
    key_points: List[str]
    conclusion: str


class VideoScene(BaseModel):
    scene_id: str
    title: str
    narration: str
    visual_description: str
    duration_seconds: int


class VideoScriptContent(BaseModel):
    title: str
    estimated_duration_minutes: int
    scenes: List[VideoScene]