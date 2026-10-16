"""Orquestador del evaluador semántico de Data/IA.

Este módulo implementa la capa de evaluación semántica independiente del
proveedor concreto utilizado para ejecutar el modelo.

Arquitectura:

    generated_content
    generation_context
    chunks_used
            |
            v
    SemanticEvaluator
            |
            +-- construye prompts
            |
            v
    SemanticProvider
            |
            v
    structured output sin validar
            |
            v
    validación Pydantic
            |
            v
    SemanticEvaluationResult

Responsabilidades:
- construir instrucciones para el evaluador semántico;
- garantizar que `chunks_used` sea la única evidencia factual;
- invocar al proveedor abstracto;
- validar la respuesta estructurada;
- medir latencia;
- normalizar fallos del proveedor;
- devolver SemanticEvaluationResult.

Este módulo NO:
- decide el status pedagógico final del contenido;
- combina scores heurísticos y semánticos;
- controla reintentos del ciclo de corrección;
- llama directamente a Gemini;
- modifica Retrieval;
- persiste resultados.
"""

from __future__ import annotations

import json
import time
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from data_ai.evaluation.semantic_provider import (
    SemanticProvider,
    SemanticProviderExecutionError,
    SemanticProviderNotConfiguredError,
    SemanticProviderTimeoutError,
    SemanticProviderInvalidOutputError, # <--- AGREGAR ESTA LÍNEA
)


from data_ai.schemas.semantic_evaluation import (
    SemanticEvaluationResult,
    SemanticObservation,
    SemanticRecommendation,
    SemanticScores,
    UnsupportedClaim,
)


SEMANTIC_PROMPT_VERSION = "semantic-evaluator-v0.1"


_OBSERVATIONS_ADAPTER = TypeAdapter(
    list[SemanticObservation]
)

_RECOMMENDATIONS_ADAPTER = TypeAdapter(
    list[SemanticRecommendation]
)

_UNSUPPORTED_INFORMATION_ADAPTER = TypeAdapter(
    list[UnsupportedClaim]
)


SYSTEM_PROMPT = """
Eres el Agente Evaluador semántico de NuevaMente.

Tu tarea es evaluar la calidad de un contenido educativo generado
automáticamente.

Debes evaluar exactamente cuatro dimensiones:

1. relevance
2. coherence
3. didactic_adaptation
4. content_support

Cada dimensión utiliza una escala de 1.0 a 5.0.

Interpretación general:

5.0 = excelente
4.0 = bueno
3.0 = aceptable pero requiere mejora
2.0 = insuficiente
1.0 = deficiente o crítico

REGLAS OBLIGATORIAS

1. RELEVANCE

Evalúa si el contenido generado responde al learning_objective y al niche
solicitados.

Considera:
- alineación con el objetivo;
- pertinencia temática;
- cobertura de conceptos relevantes;
- desviaciones de tema.

2. COHERENCE

Evalúa únicamente la consistencia interna del contenido generado.

Considera:
- contradicciones;
- saltos lógicos;
- ideas inconexas;
- conclusiones que no derivan del contenido;
- incompatibilidades entre preguntas, respuestas y explicaciones.

3. DIDACTIC_ADAPTATION

Evalúa si el contenido corresponde al profile y detail_level solicitados.

Considera:
- complejidad del vocabulario;
- profundidad técnica;
- conocimientos previos asumidos;
- densidad conceptual;
- claridad pedagógica;
- explicación de conceptos antes de utilizarlos.

No evalúes esta dimensión únicamente por longitud.

4. CONTENT_SUPPORT

Esta regla es crítica.

La ÚNICA evidencia factual válida son los elementos incluidos en
chunks_used.

NO utilices:
- conocimiento general;
- conocimiento interno del modelo;
- learning_objective;
- niche;
- profile;
- detail_level;

como evidencia factual.

Debes comparar las afirmaciones factuales del contenido generado contra
chunks_used.

Detecta:
- afirmaciones no respaldadas;
- contradicciones con la evidencia;
- extrapolaciones injustificadas;
- información inventada.

Una afirmación puede estar respaldada aunque no copie literalmente el texto
de los chunks, siempre que exista equivalencia semántica clara.

REGLAS ESPECÍFICAS POR FORMATO (CRÍTICO PARA TU EVALUACIÓN)

Dependiendo del formato del contenido recibido, debes aplicar estas excepciones estrictas para evitar falsos positivos de alucinación (unsupported_information):

1. FORMATO QUIZ: Los "distractores" (las opciones de respuesta incorrectas) están diseñados para ser falsos a propósito. NUNCA los evalúes como alucinaciones ni como afirmaciones factuales no respaldadas. Evalúa únicamente la pregunta, la respuesta correcta y la explicación.
2. FORMATO VIDEO_SCRIPT: Las descripciones visuales, de cámara o de escena (`visual_description`) son instrucciones creativas, NO evidencia factual. NUNCA exijas que el texto de la descripción visual esté en los chunks. Evalúa el respaldo factual ÚNICAMENTE en la narración (`narration`).
3. FORMATO TLDR: El título y el "framing" (encuadre) son textos introductorios y de enganche. Enfoca tu evaluación de respaldo factual (content_support) estrictamente en el cuerpo del resumen (`summary`) y los puntos clave (`key_points`).

FORMATO DE SALIDA

Devuelve exclusivamente un objeto estructurado equivalente a:

{
  "scores": {
    "relevance": 1.0-5.0,
    "coherence": 1.0-5.0,
    "didactic_adaptation": 1.0-5.0,
    "content_support": 1.0-5.0
  },
  "observations": [
    {
      "dimension": "relevance | coherence | didactic_adaptation | content_support",
      "severity": "low | medium | high",
      "message": "descripción concreta del problema",
      "item_id": null
    }
  ],
  "recommendations": [
    {
      "dimension": "relevance | coherence | didactic_adaptation | content_support",
      "message": "acción concreta para corregir el problema",
      "item_id": null
    }
  ],
  "unsupported_information": [
    {
      "claim": "afirmación problemática",
      "reason": "por qué no está respaldada",
      "item_id": null,
      "related_chunk_ids": []
    }
  ]
}

REGLAS DE OBSERVACIONES

- Genera observaciones solo cuando exista un problema relevante.
- Prioriza los problemas de mayor impacto.
- Evita observaciones vagas.
- No escribas simplemente "el contenido puede mejorar".
- No inventes problemas para llenar la lista.
- Los mensajes deben estar en español.

REGLAS DE RECOMENDACIONES

- Deben ser específicas.
- Deben ser accionables.
- Deben corresponder a problemas realmente detectados.
- Deben poder ser utilizadas posteriormente por un Agente Revisor.
- Los mensajes deben estar en español.

REGLAS DE UNSUPPORTED_INFORMATION

- Incluye únicamente afirmaciones presentes realmente en generated_content.
- No inventes quotations o claims.
- Usa chunks_used como única evidencia factual.
- related_chunk_ids puede quedar vacío si no existe evidencia relacionada.

No decidas si el contenido está approved, requires_revision o rejected.

Tu responsabilidad termina en:
- scores;
- observations;
- recommendations;
- unsupported_information.
""".strip()


def _to_json_compatible(
    value: Any,
) -> Any:
    """Convierte valores comunes del proyecto a estructuras JSON.

    Los schemas Pydantic se convierten mediante ``model_dump``.
    Las listas y diccionarios se procesan recursivamente.

    Parameters
    ----------
    value:
        Valor que debe serializarse para construir el prompt.

    Returns
    -------
    Any
        Representación compatible con ``json.dumps``.
    """

    if isinstance(value, BaseModel):
        return _to_json_compatible(
            value.model_dump()
        )

    if isinstance(value, dict):
        return {
            str(key): _to_json_compatible(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _to_json_compatible(item)
            for item in value
        ]

    return value


def _json_for_prompt(
    value: Any,
) -> str:
    """Serializa un valor de forma legible para el prompt."""

    normalized = _to_json_compatible(value)

    return json.dumps(
        normalized,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def build_semantic_user_prompt(
    *,
    content_format: str,
    generated_content: Any,
    generation_context: Any,
    chunks_used: list[Any],
) -> str:
    """Construye el prompt específico de una evaluación.

    Parameters
    ----------
    content_format:
        Formato pedagógico generado.

    generated_content:
        Contenido que debe evaluarse.

    generation_context:
        Contexto pedagógico utilizado durante generación.

    chunks_used:
        Evidencia factual recuperada mediante Retrieval.

    Returns
    -------
    str
        Prompt listo para enviarse al proveedor.
    """

    generated_content_json = _json_for_prompt(
        generated_content
    )

    generation_context_json = _json_for_prompt(
        generation_context
    )

    chunks_used_json = _json_for_prompt(
        chunks_used
    )

    return f"""
FORMATO DEL CONTENIDO

{content_format}

CONTEXTO PEDAGÓGICO

{generation_context_json}

CONTENIDO GENERADO A EVALUAR

{generated_content_json}

EVIDENCIA FACTUAL — CHUNKS_USED

{chunks_used_json}

INSTRUCCIONES FINALES

Evalúa el contenido siguiendo estrictamente la rúbrica del system prompt.

Recuerda:

- generation_context sirve para evaluar relevancia y adaptación didáctica;
- generation_context NO es evidencia factual;
- chunks_used es la única evidencia factual válida;
- no utilices conocimiento externo para completar información faltante;
- no produzcas un verdict final;
- devuelve únicamente la estructura solicitada.
""".strip()


def _parse_provider_output(
    payload: dict[str, Any],
) -> tuple[
    SemanticScores,
    list[SemanticObservation],
    list[SemanticRecommendation],
    list[UnsupportedClaim],
]:
    """Valida y transforma la salida del proveedor.

    Parameters
    ----------
    payload:
        Diccionario sin validar devuelto por SemanticProvider.

    Returns
    -------
    tuple
        Scores, observaciones, recomendaciones y claims no respaldados.

    Raises
    ------
    TypeError
        Si el payload no tiene la estructura raíz esperada.

    KeyError
        Si falta ``scores``.

    ValidationError
        Si alguno de los elementos no cumple los schemas Pydantic.
    """

    if not isinstance(payload, dict):
        raise TypeError(
            "Semantic provider output must be a dictionary."
        )

    scores_payload = payload["scores"]

    observations_payload = payload.get(
        "observations",
        [],
    )

    recommendations_payload = payload.get(
        "recommendations",
        [],
    )

    unsupported_payload = payload.get(
        "unsupported_information",
        [],
    )

    scores = SemanticScores.model_validate(
        scores_payload
    )

    observations = (
        _OBSERVATIONS_ADAPTER.validate_python(
            observations_payload
        )
    )

    recommendations = (
        _RECOMMENDATIONS_ADAPTER.validate_python(
            recommendations_payload
        )
    )

    unsupported_information = (
        _UNSUPPORTED_INFORMATION_ADAPTER.validate_python(
            unsupported_payload
        )
    )

    return (
        scores,
        observations,
        recommendations,
        unsupported_information,
    )


class SemanticEvaluator:
    """Orquesta una evaluación semántica individual."""

    def __init__(
        self,
        provider: SemanticProvider,
        *,
        prompt_version: str = SEMANTIC_PROMPT_VERSION,
    ) -> None:
        """Inicializa el evaluador.

        Parameters
        ----------
        provider:
            Adapter que ejecutará el modelo semántico.

        prompt_version:
            Identificador del prompt utilizado para trazabilidad.
        """

        self.provider = provider
        self.prompt_version = prompt_version

    def evaluate(
        self,
        *,
        content_format: str,
        generated_content: Any,
        generation_context: Any,
        chunks_used: list[Any],
    ) -> SemanticEvaluationResult:
        """Ejecuta una evaluación semántica.

        El método nunca calcula el veredicto pedagógico final.

        Parameters
        ----------
        content_format:
            ``quiz``, ``flashcards``, ``tldr`` o ``video_script``.

        generated_content:
            Contenido generado que será evaluado.

        generation_context:
            Contexto pedagógico de generación.

        chunks_used:
            Evidencia factual recuperada mediante Retrieval.

        Returns
        -------
        SemanticEvaluationResult
            Resultado normalizado de la evaluación.
        """

        started_at = time.perf_counter()

        model_name = self.provider.model_name

        try:
            user_prompt = build_semantic_user_prompt(
                content_format=content_format,
                generated_content=generated_content,
                generation_context=generation_context,
                chunks_used=chunks_used,
            )

            raw_output = (
                self.provider.generate_structured(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
            )

            (
                scores,
                observations,
                recommendations,
                unsupported_information,
            ) = _parse_provider_output(
                raw_output
            )

            latency_ms = self._elapsed_ms(
                started_at
            )

            return SemanticEvaluationResult(
                status="success",
                scores=scores,
                observations=observations,
                recommendations=recommendations,
                unsupported_information=(
                    unsupported_information
                ),
                error_code=None,
                error_message=None,
                model=model_name,
                prompt_version=self.prompt_version,
                latency_ms=latency_ms,
            )

        except SemanticProviderNotConfiguredError as exc:
            return SemanticEvaluationResult(
                status="unavailable",
                scores=None,
                observations=[],
                recommendations=[],
                unsupported_information=[],
                error_code="not_configured",
                error_message=str(exc),
                model=exc.model or model_name,
                prompt_version=self.prompt_version,
                latency_ms=self._elapsed_ms(
                    started_at
                ),
            )

        except SemanticProviderTimeoutError as exc:
            return SemanticEvaluationResult(
                status="failed",
                scores=None,
                observations=[],
                recommendations=[],
                unsupported_information=[],
                error_code="timeout",
                error_message=str(exc),
                model=exc.model or model_name,
                prompt_version=self.prompt_version,
                latency_ms=self._elapsed_ms(
                    started_at
                ),
            )

        except SemanticProviderExecutionError as exc:
            return SemanticEvaluationResult(
                status="failed",
                scores=None,
                observations=[],
                recommendations=[],
                unsupported_information=[],
                error_code="provider_error",
                error_message=str(exc),
                model=exc.model or model_name,
                prompt_version=self.prompt_version,
                latency_ms=self._elapsed_ms(
                    started_at
                ),
            )

        except SemanticProviderInvalidOutputError as exc:
            return SemanticEvaluationResult(
                status="failed",
                scores=None,
                observations=[],
                recommendations=[],
                unsupported_information=[],
                error_code="invalid_output",
                error_message=str(exc),
                model=exc.model or model_name,
                prompt_version=self.prompt_version,
                latency_ms=self._elapsed_ms(
                    started_at
                ),
            )
        
        except (
            ValidationError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            return SemanticEvaluationResult(
                status="failed",
                scores=None,
                observations=[],
                recommendations=[],
                unsupported_information=[],
                error_code="invalid_output",
                error_message=(
                    "Semantic provider returned invalid "
                    f"structured output: {exc}"
                ),
                model=model_name,
                prompt_version=self.prompt_version,
                latency_ms=self._elapsed_ms(
                    started_at
                ),
            )

        except Exception as exc:
            # Defensa final para impedir que una falla inesperada del
            # adapter semántico rompa todo el pipeline de evaluación.
            #
            # Los adapters concretos deberían normalizar sus propios
            # errores mediante SemanticProviderExecutionError. Este
            # bloque existe únicamente como protección de frontera.
            return SemanticEvaluationResult(
                status="failed",
                scores=None,
                observations=[],
                recommendations=[],
                unsupported_information=[],
                error_code="provider_error",
                error_message=(
                    "Unexpected semantic provider failure: "
                    f"{exc}"
                ),
                model=model_name,
                prompt_version=self.prompt_version,
                latency_ms=self._elapsed_ms(
                    started_at
                ),
            )

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> int:
        """Calcula tiempo transcurrido en milisegundos."""

        elapsed_seconds = (
            time.perf_counter()
            - started_at
        )

        return max(
            0,
            round(
                elapsed_seconds * 1000
            ),
        )