"""Contratos canónicos de contenido educativo generado."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    """Pregunta individual perteneciente a un Quiz."""

    question_id: str
    question: str
    options: tuple[str, ...]
    correct_answer: str
    explanation: str

    def __post_init__(self) -> None:
        if not self.question_id.strip():
            raise ValueError(
                "question_id no puede estar vacío."
            )

        if not self.question.strip():
            raise ValueError(
                "question no puede estar vacío."
            )

        if len(self.options) < 2:
            raise ValueError(
                "options debe contener al menos dos opciones."
            )

        cleaned_options = tuple(
            option.strip()
            for option in self.options
        )

        if any(
            not option
            for option in cleaned_options
        ):
            raise ValueError(
                "Las opciones no pueden estar vacías."
            )

        if (
            len(cleaned_options)
            != len(set(cleaned_options))
        ):
            raise ValueError(
                "Las opciones no deben contener duplicados."
            )

        if (
            self.correct_answer.strip()
            not in cleaned_options
        ):
            raise ValueError(
                "correct_answer debe coincidir "
                "con una de las opciones."
            )

        if not self.explanation.strip():
            raise ValueError(
                "explanation no puede estar vacío."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte la pregunta al contrato JSON canónico."""
        return {
            "question_id": self.question_id,
            "question": self.question,
            "options": list(self.options),
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "QuizQuestion":
        """Construye una pregunta desde el contrato JSON."""
        options = data.get("options")

        if not isinstance(
            options,
            list,
        ):
            raise ValueError(
                "options debe ser una lista."
            )

        return cls(
            question_id=str(
                data["question_id"]
            ),
            question=str(
                data["question"]
            ),
            options=tuple(
                str(option)
                for option in options
            ),
            correct_answer=str(
                data["correct_answer"]
            ),
            explanation=str(
                data["explanation"]
            ),
        )


@dataclass(frozen=True, slots=True)
class QuizContent:
    """Contenido canónico correspondiente a un Quiz."""

    title: str
    instructions: str
    questions: tuple[QuizQuestion, ...]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError(
                "title no puede estar vacío."
            )

        if not self.instructions.strip():
            raise ValueError(
                "instructions no puede estar vacío."
            )

        if not self.questions:
            raise ValueError(
                "questions debe contener al menos una pregunta."
            )

        question_ids = [
            question.question_id
            for question in self.questions
        ]

        if (
            len(question_ids)
            != len(set(question_ids))
        ):
            raise ValueError(
                "Los question_id deben ser únicos."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte el Quiz al contrato JSON canónico."""
        return {
            "title": self.title,
            "instructions": self.instructions,
            "questions": [
                question.to_dict()
                for question in self.questions
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "QuizContent":
        """Construye un Quiz íntegro desde JSON."""
        questions = data.get(
            "questions"
        )

        if not isinstance(
            questions,
            list,
        ):
            raise ValueError(
                "questions debe ser una lista."
            )

        parsed_questions: list[
            QuizQuestion
        ] = []

        for index, question in enumerate(
            questions
        ):
            if not isinstance(
                question,
                dict,
            ):
                raise ValueError(
                    f"questions[{index}] debe ser un objeto."
                )

            parsed_questions.append(
                QuizQuestion.from_dict(
                    question
                )
            )

        return cls(
            title=str(
                data["title"]
            ),
            instructions=str(
                data["instructions"]
            ),
            questions=tuple(
                parsed_questions
            ),
        )


@dataclass(frozen=True, slots=True)
class FlashcardItem:
    """Flashcard individual."""

    card_id: str
    front: str
    back: str

    def __post_init__(self) -> None:
        if not self.card_id.strip():
            raise ValueError(
                "card_id no puede estar vacío."
            )

        if not self.front.strip():
            raise ValueError(
                "front no puede estar vacío."
            )

        if not self.back.strip():
            raise ValueError(
                "back no puede estar vacío."
            )

        if (
            self.front.strip()
            == self.back.strip()
        ):
            raise ValueError(
                "front y back no deben ser idénticos."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte la Flashcard al contrato JSON."""
        return {
            "card_id": self.card_id,
            "front": self.front,
            "back": self.back,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "FlashcardItem":
        """Construye una Flashcard desde JSON."""
        return cls(
            card_id=str(
                data["card_id"]
            ),
            front=str(
                data["front"]
            ),
            back=str(
                data["back"]
            ),
        )


@dataclass(frozen=True, slots=True)
class FlashcardsContent:
    """Contenido canónico correspondiente a Flashcards."""

    title: str
    instructions: str
    cards: tuple[FlashcardItem, ...]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError(
                "title no puede estar vacío."
            )

        if not self.instructions.strip():
            raise ValueError(
                "instructions no puede estar vacío."
            )

        if not self.cards:
            raise ValueError(
                "cards debe contener al menos una Flashcard."
            )

        card_ids = [
            card.card_id
            for card in self.cards
        ]

        if (
            len(card_ids)
            != len(set(card_ids))
        ):
            raise ValueError(
                "Los card_id deben ser únicos."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte Flashcards al contrato JSON canónico."""
        return {
            "title": self.title,
            "instructions": self.instructions,
            "cards": [
                card.to_dict()
                for card in self.cards
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "FlashcardsContent":
        """Construye Flashcards íntegramente desde JSON."""
        cards = data.get(
            "cards"
        )

        if not isinstance(
            cards,
            list,
        ):
            raise ValueError(
                "cards debe ser una lista."
            )

        parsed_cards: list[
            FlashcardItem
        ] = []

        for index, card in enumerate(
            cards
        ):
            if not isinstance(
                card,
                dict,
            ):
                raise ValueError(
                    f"cards[{index}] debe ser un objeto."
                )

            parsed_cards.append(
                FlashcardItem.from_dict(
                    card
                )
            )

        return cls(
            title=str(
                data["title"]
            ),
            instructions=str(
                data["instructions"]
            ),
            cards=tuple(
                parsed_cards
            ),
        )


@dataclass(frozen=True, slots=True)
class TLDRContent:
    """Resumen ejecutivo canónico alineado con Data/IA."""

    title: str
    summary: str
    key_points: tuple[str, ...]
    conclusion: str

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError(
                "title no puede estar vacío."
            )

        if not self.summary.strip():
            raise ValueError(
                "summary no puede estar vacío."
            )

        if not self.conclusion.strip():
            raise ValueError(
                "conclusion no puede estar vacío."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte TLDR al contrato JSON canónico."""
        return {
            "title": self.title,
            "summary": self.summary,
            "key_points": list(
                self.key_points
            ),
            "conclusion": self.conclusion,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "TLDRContent":
        """Construye TLDR desde el contrato acordado con Data/IA."""
        key_points = data.get(
            "key_points",
            [],
        )

        if not isinstance(
            key_points,
            list,
        ):
            raise ValueError(
                "key_points debe ser una lista."
            )

        return cls(
            title=str(
                data["title"]
            ),
            summary=str(
                data["summary"]
            ),
            key_points=tuple(
                str(key_point)
                for key_point
                in key_points
            ),
            conclusion=str(
                data["conclusion"]
            ),
        )


@dataclass(frozen=True, slots=True)
class VideoScriptScene:
    """Escena individual del guion de video canónico."""

    scene_id: str
    title: str
    visual_description: str
    narration: str
    duration_seconds: int = 0

    def __post_init__(self) -> None:
        if not self.scene_id.strip():
            raise ValueError(
                "scene_id no puede estar vacío."
            )

        if not self.title.strip():
            raise ValueError(
                "title no puede estar vacío."
            )

        if not self.visual_description.strip():
            raise ValueError(
                "visual_description no puede estar vacío."
            )

        if not self.narration.strip():
            raise ValueError(
                "narration no puede estar vacío."
            )

        if self.duration_seconds < 0:
            raise ValueError(
                "duration_seconds debe ser mayor o igual a 0."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte una escena al contrato JSON canónico."""
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "visual_description": (
                self.visual_description
            ),
            "narration": self.narration,
            "duration_seconds": (
                self.duration_seconds
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "VideoScriptScene":
        """Construye una escena desde JSON."""
        return cls(
            scene_id=str(
                data["scene_id"]
            ),
            title=str(
                data["title"]
            ),
            visual_description=str(
                data["visual_description"]
            ),
            narration=str(
                data["narration"]
            ),
            duration_seconds=int(
                data.get(
                    "duration_seconds",
                    0,
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class VideoScriptContent:
    """Guion de video canónico alineado con Data/IA."""

    title: str
    estimated_duration_minutes: int
    scenes: tuple[
        VideoScriptScene,
        ...
    ]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError(
                "title no puede estar vacío."
            )

        if self.estimated_duration_minutes < 0:
            raise ValueError(
                "estimated_duration_minutes debe ser "
                "mayor o igual a 0."
            )

        if not self.scenes:
            raise ValueError(
                "scenes debe contener al menos una escena."
            )

    def to_dict(self) -> dict[str, object]:
        """Convierte Video Script al contrato JSON canónico."""
        return {
            "title": self.title,
            "estimated_duration_minutes": (
                self.estimated_duration_minutes
            ),
            "scenes": [
                scene.to_dict()
                for scene in self.scenes
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> "VideoScriptContent":
        """Construye Video Script desde el contrato de Data/IA."""
        scenes = data.get(
            "scenes"
        )

        if not isinstance(
            scenes,
            list,
        ):
            raise ValueError(
                "scenes debe ser una lista."
            )

        parsed_scenes: list[
            VideoScriptScene
        ] = []

        for index, scene in enumerate(
            scenes
        ):
            if not isinstance(
                scene,
                dict,
            ):
                raise ValueError(
                    f"scenes[{index}] debe ser un objeto."
                )

            parsed_scenes.append(
                VideoScriptScene.from_dict(
                    scene
                )
            )

        return cls(
            title=str(
                data["title"]
            ),
            estimated_duration_minutes=int(
                data.get(
                    "estimated_duration_minutes",
                    0,
                )
            ),
            scenes=tuple(
                parsed_scenes
            ),
        )


GeneratedContent = (
    QuizContent
    | FlashcardsContent
    | TLDRContent
    | VideoScriptContent
)
