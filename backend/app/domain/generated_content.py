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


GeneratedContent = (
    QuizContent
    | FlashcardsContent
)