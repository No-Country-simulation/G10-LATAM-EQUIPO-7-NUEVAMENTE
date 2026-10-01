"""Motor heurístico de evaluación de calidad para Quiz y Flashcards."""

import json
import re
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


def _normalizar_palabras(texto: str) -> list[str]:
    """
    Normaliza texto a palabras minúsculas sin puntuación.
    """
    return re.findall(r"\b\w+\b", texto.lower(), flags=re.UNICODE)


def evaluate(
    generated_content: GeneratedContent,
    chunks_used: List[ChunkUsed],
    generation_context: GenerationContext,
) -> tuple[EvaluationScores, bool]:
    """
    Calcula los scores de calidad y detecta información no respaldada.

    Parameters
    ----------
    generated_content:
        Quiz o Flashcards previamente validados.

    chunks_used:
        Chunks utilizados como evidencia durante la generación.

    generation_context:
        Contexto empleado para adaptar el contenido.

    Returns
    -------
    tuple[EvaluationScores, bool]
        Scores calculados e indicador de información no respaldada.
    """

    # Convertir modelos Pydantic a estructuras internas
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

    # ========================================================
    # 1. RELEVANCIA
    # ========================================================

    objetivo = (
        context_dict.get("learning_objective") or ""
    ).lower()

    nicho = (
        context_dict.get("niche") or ""
    ).lower()

    coincide_objetivo = (
        bool(objetivo)
        and objetivo in content_text
    )

    coincide_nicho = (
        bool(nicho)
        and nicho in content_text
    )

    relevancia = (
        5
        if coincide_objetivo or coincide_nicho
        else 3
    )

    # ========================================================
    # 2. COHERENCIA
    # ========================================================

    coherencia = (
        5
        if len(content_dict) >= 1 and len(content_text) > 50
        else 2
    )

    # ========================================================
    # 3. ADAPTACIÓN DIDÁCTICA
    # ========================================================

    perfil = (
        context_dict.get("profile") or ""
    ).lower()

    nivel_detalle = (
        context_dict.get("detail_level") or ""
    ).lower()

    adaptacion = 5

    if (
        perfil == "principiante"
        and len(content_text) > 3000
    ):
        adaptacion = 3

    elif (
        nivel_detalle == "alto"
        and len(content_text) < 200
    ):
        adaptacion = 2

    # ========================================================
    # 4. INFORMACIÓN RESPALDADA
    # ========================================================

    palabras_contenido = [
        palabra
        for palabra in _normalizar_palabras(content_text)
        if len(palabra) > 5
    ]

    palabras_chunks = set(
        _normalizar_palabras(chunks_text)
    )

    palabras_no_respaldadas = [
        palabra
        for palabra in palabras_contenido
        if palabra not in palabras_chunks
    ]

    ratio_no_respaldado = (
        len(palabras_no_respaldadas)
        / max(len(palabras_contenido), 1)
    )

    informacion_no_respaldada = (
        ratio_no_respaldado > 0.25
    )

    informacion_respaldada = (
        1
        if informacion_no_respaldada
        else 5
    )

    # ========================================================
    # 5. RESULTADO
    # ========================================================

    scores = EvaluationScores(
        relevancia=relevancia,
        coherencia=coherencia,
        adaptacion_didactica=adaptacion,
        informacion_respaldada=informacion_respaldada,
    )

    return scores, informacion_no_respaldada
