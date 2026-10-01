import json
from typing import List, Union

from data_ai.schemas.format_evaluation import (
    ChunkUsed,
    EvaluationScores,
    FlashcardsContent,
    GenerationContext,
    QuizContent,
)


GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
]


def evaluate(
    generated_content: GeneratedContent,
    chunks_used: List[ChunkUsed],
    generation_context: GenerationContext,
) -> tuple[EvaluationScores, bool]:
    """
    Calcula los scores de calidad y detecta información no respaldada.
    """

    # Convertimos los contratos Pydantic a estructuras internas
    content_dict = generated_content.model_dump()
    chunks_dict = [chunk.model_dump() for chunk in chunks_used]
    context_dict = generation_context.model_dump()

    content_text = json.dumps(
        content_dict,
        ensure_ascii=False,
    ).lower()

    chunks_text = " ".join(
        json.dumps(chunk, ensure_ascii=False).lower()
        for chunk in chunks_dict
    )

    objetivo = (
        context_dict.get("learning_objective") or ""
    ).lower()

    nicho = context_dict.get("niche", "").lower()

    relevancia = (
        5
        if (
            objetivo and objetivo in content_text
        )
        or (
            nicho and nicho in content_text
        )
        else 3
    )

    coherencia = (
        5
        if len(content_dict) >= 1 and len(content_text) > 50
        else 2
    )

    perfil = context_dict.get("profile", "").lower()
    nivel_detalle = context_dict.get(
        "detail_level",
        "",
    ).lower()

    adaptacion = 5

    if perfil == "principiante" and len(content_text) > 3000:
        adaptacion = 3
    elif nivel_detalle == "alto" and len(content_text) < 200:
        adaptacion = 2

    valores_generados = " ".join(
        str(value)
        for value in content_dict.values()
    ).lower()

    palabras_clave = [
        word
        for word in valores_generados.split()
        if len(word) > 5
    ]

    palabras_no_respaldadas = [
        word
        for word in palabras_clave
        if word not in chunks_text
    ]

    ratio_no_respaldado = (
        len(palabras_no_respaldadas)
        / max(len(palabras_clave), 1)
    )

    informacion_no_respaldada = (
        ratio_no_respaldado > 0.25
    )

    informacion_respaldada = (
        1 if informacion_no_respaldada else 5
    )

    scores = EvaluationScores(
        relevancia=relevancia,
        coherencia=coherencia,
        adaptacion_didactica=adaptacion,
        informacion_respaldada=informacion_respaldada,
    )

    return scores, informacion_no_respaldada
