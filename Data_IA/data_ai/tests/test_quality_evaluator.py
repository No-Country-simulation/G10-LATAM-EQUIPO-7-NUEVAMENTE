"""
Tests automáticos de la capa quality_evaluator.

Valida:
- la estructura interna QualityEvaluationResult;
- la compatibilidad con EvaluationScores;
- la firma esperada de evaluate();
- el comportamiento temporal mientras la lógica real no está integrada.
"""

import pytest

from data_ai.evaluation.quality_evaluator import (
    QualityEvaluationResult,
    evaluate,
)
from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    EvaluationScores,
    GenerationContext,
    QuizContent,
    QuizQuestion,
)


def build_quiz_content() -> QuizContent:
    """Construye un Quiz válido para pruebas."""
    return QuizContent(
        title="Quiz sobre FastAPI",
        instructions="Selecciona la respuesta correcta.",
        questions=[
            QuizQuestion(
                question_id="Q1",
                question="¿Qué clase se utiliza para crear una aplicación FastAPI?",
                options=["FastAPI", "Flask", "Django"],
                correct_answer="FastAPI",
                explanation="La clase FastAPI se utiliza para crear la aplicación.",
            )
        ],
    )


def build_chunks() -> list[ChunkUsed]:
    """Construye evidencia válida para pruebas."""
    return [
        ChunkUsed(
            chunk_id="DOC-001_CH_001",
            document_id="DOC-001",
            rank=1,
            score=0.91,
            text=(
                "Para crear una aplicación se importa FastAPI desde "
                "el paquete fastapi y se instancia la clase FastAPI."
            ),
        )
    ]


def build_generation_context() -> GenerationContext:
    """Construye un contexto de generación válido."""
    return GenerationContext(
        profile="student",
        niche="technology",
        detail_level="beginner",
        learning_objective="Comprender conceptos básicos de FastAPI",
    )


def test_quality_evaluation_result_is_valid():
    """QualityEvaluationResult debe almacenar una salida válida."""
    result = QualityEvaluationResult(
        status="aprobado",
        scores=EvaluationScores(
            relevancia=5,
            coherencia=5,
            adaptacion_didactica=4,
            informacion_respaldada=5,
        ),
        informacion_no_respaldada=False,
        observaciones=[],
    )

    assert result.status == "aprobado"
    assert result.scores.relevancia == 5
    assert result.scores.coherencia == 5
    assert result.scores.adaptacion_didactica == 4
    assert result.scores.informacion_respaldada == 5
    assert result.informacion_no_respaldada is False
    assert result.observaciones == []


def test_evaluate_placeholder_raises_not_implemented():
    """
    Mientras la lógica real no esté integrada,
    evaluate() debe lanzar NotImplementedError.
    """
    generated_content = build_quiz_content()
    chunks_used = build_chunks()
    generation_context = build_generation_context()

    with pytest.raises(
        NotImplementedError,
        match="La lógica del quality evaluator todavía no ha sido integrada.",
    ):
        evaluate(
            generated_content=generated_content,
            chunks_used=chunks_used,
            generation_context=generation_context,
        )


def test_generation_context_without_learning_objective_is_accepted():
    """
    La interfaz debe aceptar generation_context sin learning_objective,
    ya que ese campo es opcional.
    """
    generated_content = build_quiz_content()
    chunks_used = build_chunks()

    generation_context = GenerationContext(
        profile="student",
        niche="technology",
        detail_level="beginner",
    )

    assert generation_context.learning_objective is None

    with pytest.raises(NotImplementedError):
        evaluate(
            generated_content=generated_content,
            chunks_used=chunks_used,
            generation_context=generation_context,
        )