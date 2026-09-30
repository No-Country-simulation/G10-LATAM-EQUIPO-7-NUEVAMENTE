"""
Contratos de evaluación de formatos generados por NuevaMente.

Sprint 2:
- Formatos soportados: quiz y flashcards.
- Data/IA recibe:
    document_id
    format
    generated_content
    generation_context
    chunks_used
- Data/IA devuelve:
    document_id
    format
    status
    scores
    informacion_no_respaldada
    observaciones

El campo `format` discrimina automáticamente el tipo esperado de
`generated_content`.

Requiere Pydantic v2.
"""

from typing import Annotated, List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# CONFIGURACIÓN BASE
# ============================================================

class StrictModel(BaseModel):
    """Modelo base: no permite campos adicionales no definidos."""

    model_config = ConfigDict(extra="forbid")


# ============================================================
# QUIZ
# ============================================================

class QuizQuestion(StrictModel):
    """Una pregunta individual del quiz."""

    question_id: str = Field(
        ...,
        min_length=1,
        description="Identificador único de la pregunta dentro del quiz.",
    )
    question: str = Field(
        ...,
        min_length=1,
        description="Texto de la pregunta.",
    )
    options: List[str] = Field(
        ...,
        min_length=2,
        description="Opciones disponibles para responder.",
    )
    correct_answer: str = Field(
        ...,
        min_length=1,
        description="Respuesta correcta. Debe coincidir con una opción.",
    )
    explanation: str = Field(
        ...,
        min_length=1,
        description="Explicación de la respuesta correcta.",
    )

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

    title: str = Field(
        ...,
        min_length=1,
        description="Título del quiz.",
    )
    instructions: str = Field(
        ...,
        min_length=1,
        description="Instrucciones para responder el quiz.",
    )
    questions: List[QuizQuestion] = Field(
        ...,
        min_length=1,
        description="Preguntas que componen el quiz.",
    )

    @model_validator(mode="after")
    def validate_unique_question_ids(self):
        question_ids = [question.question_id for question in self.questions]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Los question_id deben ser únicos.")

        return self


# ============================================================
# FLASHCARDS
# ============================================================

class FlashcardItem(StrictModel):
    """Una flashcard individual."""

    card_id: str = Field(
        ...,
        min_length=1,
        description="Identificador único de la flashcard dentro del conjunto.",
    )
    front: str = Field(
        ...,
        min_length=1,
        description="Pregunta, concepto o estímulo mostrado al usuario.",
    )
    back: str = Field(
        ...,
        min_length=1,
        description="Respuesta o contenido mostrado al reverso.",
    )

    @model_validator(mode="after")
    def validate_flashcard(self):
        if self.front.strip() == self.back.strip():
            raise ValueError("front y back no deben ser idénticos.")

        return self


class FlashcardsContent(StrictModel):
    """Contenido generado para el formato flashcards."""

    title: str = Field(
        ...,
        min_length=1,
        description="Título del conjunto de flashcards.",
    )
    instructions: str = Field(
        ...,
        min_length=1,
        description="Instrucciones de uso para el usuario.",
    )
    cards: List[FlashcardItem] = Field(
        ...,
        min_length=1,
        description="Lista de flashcards generadas.",
    )

    @model_validator(mode="after")
    def validate_unique_card_ids(self):
        card_ids = [card.card_id for card in self.cards]

        if len(card_ids) != len(set(card_ids)):
            raise ValueError("Los card_id deben ser únicos.")

        return self


# ============================================================
# CHUNKS UTILIZADOS COMO EVIDENCIA
# ============================================================

class ChunkUsed(StrictModel):
    """Chunk recuperado por Agentes y utilizado como evidencia."""

    chunk_id: str = Field(
        ...,
        min_length=1,
        description="Identificador único del chunk.",
    )
    document_id: str = Field(
        ...,
        min_length=1,
        description="Documento al que pertenece el chunk.",
    )
    rank: int = Field(
        ...,
        ge=1,
        description="Posición del chunk dentro de los resultados recuperados.",
    )
    score: float = Field(
        ...,
        description="Score de retrieval informado por Agentes.",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Texto del chunk utilizado como evidencia.",
    )

# ============================================================
# CONTEXTO DE GENERACIÓN
# ============================================================

class GenerationContext(StrictModel):
    """
    Contexto utilizado por Agentes para adaptar el contenido generado.

    Estos valores deben corresponder a los mismos parámetros utilizados
    durante /generate para que Data/IA pueda evaluar la adaptación
    didáctica con una referencia explícita.
    """

    profile: str = Field(
        ...,
        min_length=1,
        description=(
            "Perfil objetivo utilizado durante la generación "
            "(por ejemplo: student, professional, general_public)."
        ),
    )

    niche: str = Field(
        ...,
        min_length=1,
        description=(
            "Área, dominio o nicho para el que se generó el contenido."
        ),
    )

    detail_level: str = Field(
        ...,
        min_length=1,
        description=(
            "Nivel de profundidad utilizado durante la generación."
        ),
    )

    learning_objective: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Objetivo de aprendizaje específico, si fue proporcionado "
            "durante la generación."
        ),
    )

# ============================================================
# REQUEST BASE
# ============================================================

class EvaluationRequestBase(StrictModel):
    """Campos comunes a cualquier solicitud de evaluación."""

    document_id: str = Field(
        ...,
        min_length=1,
        description="Identificador del documento original.",
    )
    generation_context: GenerationContext = Field(
        ...,
        description=(
            "Contexto utilizado durante la generación del contenido. "
            "Sirve como referencia para evaluar adaptación didáctica."
        ),
    )
    chunks_used: List[ChunkUsed] = Field(
        ...,
        min_length=1,
        description="Chunks utilizados por Agentes para generar el formato.",
    )

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


# ============================================================
# REQUESTS ESPECÍFICOS
# ============================================================

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


# ============================================================
# RESPONSE
# ============================================================

class EvaluationScores(StrictModel):
    """Puntajes de calidad para el contenido generado."""

    relevancia: int = Field(
        ...,
        ge=1,
        le=5,
        description="Qué tan pertinente es el contenido respecto al material fuente.",
    )
    coherencia: int = Field(
        ...,
        ge=1,
        le=5,
        description="Consistencia lógica, claridad y estructura del contenido.",
    )
    adaptacion_didactica: int = Field(
        ...,
        ge=1,
        le=5,
        description="Adecuación del contenido al propósito educativo esperado.",
    )
    informacion_respaldada: int = Field(
        ...,
        ge=1,
        le=5,
        description="Grado de respaldo del contenido en los chunks utilizados.",
    )


class EvaluationResponse(StrictModel):
    """Respuesta estructurada del servicio de evaluación Data/IA."""

    document_id: str = Field(
        ...,
        min_length=1,
        description="Identificador del documento original.",
    )
    format: Literal["quiz", "flashcards"] = Field(
        ...,
        description="Formato educativo evaluado.",
    )
    status: Literal[
        "aprobado",
        "requiere_revision",
        "rechazado",
    ] = Field(
        ...,
        description="Resultado global de la evaluación.",
    )
    scores: EvaluationScores = Field(
        ...,
        description="Puntajes de calidad del contenido evaluado.",
    )
    informacion_no_respaldada: bool = Field(
        ...,
        description=(
            "Indica si se detectó información que no está respaldada "
            "por los chunks utilizados."
        ),
    )
    observaciones: List[str] = Field(
        default_factory=list,
        description="Comentarios o hallazgos detectados durante la evaluación.",
    )

    @model_validator(mode="after")
    def validate_status_consistency(self):
        """
        Reglas:
        - rechazado:
            informacion_no_respaldada = True
            o algún score <= 2
        - requiere_revision:
            ningún score <= 2
            y al menos un score == 3
        - aprobado:
            todos los scores >= 4
            e informacion_no_respaldada = False
        """

        values = [
            self.scores.relevancia,
            self.scores.coherencia,
            self.scores.adaptacion_didactica,
            self.scores.informacion_respaldada,
        ]

        if self.informacion_no_respaldada:
            expected_status = "rechazado"
        elif any(score <= 2 for score in values):
            expected_status = "rechazado"
        elif any(score == 3 for score in values):
            expected_status = "requiere_revision"
        else:
            expected_status = "aprobado"

        if self.status != expected_status:
            raise ValueError(
                "status inconsistente con la evaluación. "
                f"Se esperaba '{expected_status}' y se recibió '{self.status}'."
            )

        return self


__all__ = [
    "ChunkUsed",
    "GenerationContext",
    "EvaluationRequest",
    "EvaluationRequestBase",
    "EvaluationResponse",
    "EvaluationScores",
    "FlashcardItem",
    "FlashcardsContent",
    "FlashcardsEvaluationRequest",
    "QuizContent",
    "QuizEvaluationRequest",
    "QuizQuestion",
]
