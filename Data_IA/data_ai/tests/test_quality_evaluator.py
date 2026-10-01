from data_ai.evaluation.quality_evaluator import evaluate
from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    FlashcardsContent,
    GenerationContext,
    QuizContent,
    QuizQuestion,
    FlashcardItem,
)


def build_chunks() -> list[ChunkUsed]:
    return [
        ChunkUsed(
            chunk_id="DOC-001_CH_001",
            document_id="DOC-001",
            rank=1,
            score=0.95,
            text=(
                "Python es un lenguaje de programación utilizado "
                "para desarrollo backend y ciencia de datos."
            ),
        )
    ]


def test_quiz_aprobado():
    content = QuizContent(
        title="Quiz de Python",
        instructions="Selecciona la respuesta correcta.",
        questions=[
            QuizQuestion(
                question_id="Q1",
                question="¿Qué es Python?",
                options=[
                    "Un lenguaje de programación",
                    "Un sistema operativo",
                    "Una base de datos",
                ],
                correct_answer="Un lenguaje de programación",
                explanation=(
                    "Python es un lenguaje de programación "
                    "utilizado en múltiples áreas."
                ),
            )
        ],
    )

    context = GenerationContext(
        profile="avanzado",
        niche="python",
        detail_level="medio",
        learning_objective="python",
    )

    scores, informacion_no_respaldada = evaluate(
        generated_content=content,
        chunks_used=build_chunks(),
        generation_context=context,
    )

    assert scores.relevancia == 5
    assert scores.coherencia == 5
    assert scores.adaptacion_didactica == 5
    assert isinstance(informacion_no_respaldada, bool)


def test_quiz_principiante_requiere_revision():
    texto_largo = "Python es un lenguaje de programación. " * 150

    content = QuizContent(
        title="Quiz largo de Python",
        instructions=texto_largo,
        questions=[
            QuizQuestion(
                question_id="Q1",
                question="¿Qué es Python?",
                options=[
                    "Lenguaje de programación",
                    "Base de datos",
                ],
                correct_answer="Lenguaje de programación",
                explanation=texto_largo,
            )
        ],
    )

    context = GenerationContext(
        profile="principiante",
        niche="python",
        detail_level="medio",
        learning_objective="python",
    )

    scores, _ = evaluate(
        generated_content=content,
        chunks_used=build_chunks(),
        generation_context=context,
    )

    assert scores.adaptacion_didactica == 3


def test_flashcards_detecta_informacion_no_respaldada():
    content = FlashcardsContent(
        title="Flashcards de Python",
        instructions="Estudia las tarjetas.",
        cards=[
            FlashcardItem(
                card_id="F1",
                front="¿Qué permite Python?",
                back=(
                    "Python permite construir naves espaciales "
                    "intergalácticas mediante reactores cuánticos."
                ),
            )
        ],
    )

    context = GenerationContext(
        profile="student",
        niche="python",
        detail_level="beginner",
        learning_objective="python",
    )

    scores, informacion_no_respaldada = evaluate(
        generated_content=content,
        chunks_used=build_chunks(),
        generation_context=context,
    )

    assert informacion_no_respaldada is True
    assert scores.informacion_respaldada == 1


def test_learning_objective_opcional():
    content = FlashcardsContent(
        title="Flashcards",
        instructions="Repasa conceptos.",
        cards=[
            FlashcardItem(
                card_id="F1",
                front="¿Qué es Python?",
                back="Python es un lenguaje de programación.",
            )
        ],
    )

    context = GenerationContext(
        profile="student",
        niche="python",
        detail_level="beginner",
    )

    scores, informacion_no_respaldada = evaluate(
        generated_content=content,
        chunks_used=build_chunks(),
        generation_context=context,
    )

    assert scores.relevancia in (3, 5)
    assert isinstance(informacion_no_respaldada, bool)


def test_evaluacion_relevancia_nicho_generico():
    """Valida que un nicho genérico sin objetivo no castigue la relevancia."""
    content = FlashcardsContent(
        title="Flashcards",
        instructions="Repasa conceptos.",
        cards=[
            FlashcardItem(
                card_id="F2",
                front="¿Qué es Python?",
                back="Python es un lenguaje de programación.",
            )
        ],
    )

    context = GenerationContext(
        profile="student",
        niche="General", 
        detail_level="beginner",
        learning_objective="", 
    )

    scores, _ = evaluate(
        generated_content=content,
        chunks_used=build_chunks(),
        generation_context=context,
    )

    assert scores.relevancia == 5