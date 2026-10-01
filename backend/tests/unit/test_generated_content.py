"""Pruebas unitarias de los contratos de contenido generado."""

import pytest

from app.domain.generated_content import (
    FlashcardsContent,
    QuizContent,
)


def test_quiz_from_dict_rejects_invalid_question_item() -> None:
    """Un Quiz no debe descartar preguntas inválidas silenciosamente."""
    payload = {
        "title": "Quiz de prueba",
        "instructions": "Seleccione la respuesta correcta.",
        "questions": [
            {
                "question_id": "q_1",
                "question": "¿Qué componente coordina el producto?",
                "options": [
                    "BackendAPI",
                    "Frontend",
                ],
                "correct_answer": "BackendAPI",
                "explanation": (
                    "BackendAPI coordina las integraciones."
                ),
            },
            "pregunta_invalida",
        ],
    }

    with pytest.raises(
        ValueError,
        match=r"questions\[1\] debe ser un objeto",
    ):
        QuizContent.from_dict(
            payload
        )


def test_flashcards_from_dict_rejects_invalid_card_item() -> None:
    """Flashcards no debe descartar tarjetas inválidas silenciosamente."""
    payload = {
        "title": "Flashcards de prueba",
        "instructions": "Revise cada tarjeta.",
        "cards": [
            {
                "card_id": "card_1",
                "front": "BackendAPI",
                "back": "Orquestador del producto.",
            },
            "flashcard_invalida",
        ],
    }

    with pytest.raises(
        ValueError,
        match=r"cards\[1\] debe ser un objeto",
    ):
        FlashcardsContent.from_dict(
            payload
        )