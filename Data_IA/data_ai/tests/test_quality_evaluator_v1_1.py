from data_ai.evaluation.quality_evaluator import evaluate
from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    GenerationContext,
    TLDRContent,
    VideoScriptContent,
    VideoScriptScene,
)


def _chunk(text: str) -> list[ChunkUsed]:
    return [
        ChunkUsed(
            chunk_id="DOC-001_CH_001",
            document_id="DOC-001",
            rank=1,
            score=0.9,
            text=text,
        )
    ]


def _context(
    *,
    profile: str = "student",
    niche: str = "frontend",
    detail_level: str = "medium",
    learning_objective: str | None = None,
) -> GenerationContext:
    return GenerationContext(
        profile=profile,
        niche=niche,
        detail_level=detail_level,
        learning_objective=learning_objective,
    )


def test_v11_normaliza_acentos_en_respaldo():
    content = TLDRContent(
        title="Resumen",
        summary="La pagina contiene codigo HTML.",
        key_points=["El codigo define la pagina."],
        conclusion="La pagina usa codigo.",
    )

    scores, unsupported = evaluate(
        generated_content=content,
        chunks_used=_chunk(
            "La página contiene código HTML. "
            "El código define la página."
        ),
        generation_context=_context(),
    )

    assert unsupported is False
    assert scores.informacion_respaldada >= 4


def test_v11_learning_objective_no_cuenta_como_evidencia_factual():
    content = TLDRContent(
        title="Resumen de Kubernetes",
        summary=(
            "Kubernetes permite orquestar microservicios "
            "en clusters distribuidos."
        ),
        key_points=[
            "Kubernetes administra clusters distribuidos."
        ],
        conclusion=(
            "Kubernetes es una plataforma clave "
            "para microservicios."
        ),
    )

    scores, unsupported = evaluate(
        generated_content=content,
        chunks_used=_chunk(
            "Docker permite empaquetar aplicaciones "
            "en contenedores."
        ),
        generation_context=_context(
            profile="student",
            niche="devops",
            learning_objective=(
                "Comprender Kubernetes y microservicios"
            ),
        ),
    )

    assert unsupported is True
    assert scores.informacion_respaldada == 1


def test_v11_tldr_titulo_no_se_evalua_como_hecho():
    content = TLDRContent(
        title=(
            "Guía revolucionaria intergaláctica "
            "para estudiantes"
        ),
        summary="HTML define elementos.",
        key_points=["HTML define elementos."],
        conclusion="HTML define elementos.",
    )

    scores, unsupported = evaluate(
        generated_content=content,
        chunks_used=_chunk(
            "HTML define elementos."
        ),
        generation_context=_context(),
    )

    assert unsupported is False
    assert scores.informacion_respaldada == 5


def test_v11_video_visual_description_no_es_hecho_factual():
    content = VideoScriptContent(
        title="Introducción a HTML",
        estimated_duration_minutes=1,
        scenes=[
            VideoScriptScene(
                scene_id="SCENE-001",
                title="Apertura espectacular",
                visual_description=(
                    "Un dinosaurio cuántico vuela "
                    "sobre una galaxia."
                ),
                narration=(
                    "HTML define elementos "
                    "de una página."
                ),
                duration_seconds=30,
            )
        ],
    )

    scores, unsupported = evaluate(
        generated_content=content,
        chunks_used=_chunk(
            "HTML define elementos de una página."
        ),
        generation_context=_context(),
    )

    assert unsupported is False
    assert scores.informacion_respaldada == 5


def test_v11_video_alucinacion_en_narracion_sigue_detectandose():
    content = VideoScriptContent(
        title="Introducción a HTML",
        estimated_duration_minutes=1,
        scenes=[
            VideoScriptScene(
                scene_id="SCENE-001",
                title="Escena",
                visual_description="Código HTML en pantalla.",
                narration=(
                    "HTML permite teletransportar dinosaurios "
                    "mediante reactores cuánticos "
                    "y motores interestelares."
                ),
                duration_seconds=30,
            )
        ],
    )

    scores, unsupported = evaluate(
        generated_content=content,
        chunks_used=_chunk(
            "HTML define elementos y atributos "
            "de una página web."
        ),
        generation_context=_context(),
    )

    assert unsupported is True
    assert scores.informacion_respaldada == 1
