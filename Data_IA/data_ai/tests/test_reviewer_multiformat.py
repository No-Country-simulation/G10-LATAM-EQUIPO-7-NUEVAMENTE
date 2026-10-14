"""Tests multiformato para el reviewer heurístico."""

from data_ai.evaluation.reviewer import (
    evaluar_contenido,
)
from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    GenerationContext,
    TLDRContent,
    VideoScriptContent,
    VideoScriptScene,
)


def _context() -> GenerationContext:
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="medium",
        learning_objective=(
            "Comprender conceptos de arquitectura backend."
        ),
    )


def _chunks() -> list[ChunkUsed]:
    return [
        ChunkUsed(
            chunk_id="chunk_1",
            document_id="doc_123",
            rank=1,
            score=1.0,
            text=(
                "Una arquitectura backend organiza servicios, "
                "rutas, lógica de negocio y persistencia de datos."
            ),
        ),
    ]


def test_reviewer_supports_tldr():
    content = TLDRContent(
        title="Arquitectura backend",
        summary=(
            "Una arquitectura backend organiza servicios, "
            "rutas y lógica de negocio."
        ),
        key_points=[
            "Organiza servicios.",
            "Separa lógica de negocio.",
        ],
        conclusion=(
            "La separación de responsabilidades facilita "
            "el mantenimiento."
        ),
    )

    result = evaluar_contenido(
        generated_content=content,
        chunks_used=_chunks(),
        generation_context=_context(),
    )

    assert result.status in {
        "aprobado",
        "requiere_revision",
        "rechazado",
    }

    assert 1 <= result.scores.relevancia <= 5
    assert 1 <= result.scores.coherencia <= 5

    assert (
        1
        <= result.scores.adaptacion_didactica
        <= 5
    )

    assert (
        1
        <= result.scores.informacion_respaldada
        <= 5
    )


def test_reviewer_supports_video_script():
    content = VideoScriptContent(
        title="Arquitectura backend",
        estimated_duration_minutes=1,
        scenes=[
            VideoScriptScene(
                scene_id="scene_1",
                title="Introducción",
                visual_description=(
                    "Diagrama de componentes backend."
                ),
                narration=(
                    "Una arquitectura backend organiza "
                    "servicios, rutas y lógica de negocio."
                ),
                duration_seconds=30,
            ),
        ],
    )

    result = evaluar_contenido(
        generated_content=content,
        chunks_used=_chunks(),
        generation_context=_context(),
    )

    assert result.status in {
        "aprobado",
        "requiere_revision",
        "rechazado",
    }

    assert 1 <= result.scores.relevancia <= 5
    assert 1 <= result.scores.coherencia <= 5

    assert (
        1
        <= result.scores.adaptacion_didactica
        <= 5
    )

    assert (
        1
        <= result.scores.informacion_respaldada
        <= 5
    )