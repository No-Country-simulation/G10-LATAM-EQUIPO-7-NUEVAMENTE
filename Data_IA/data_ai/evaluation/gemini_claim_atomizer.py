"""Experimental Gemini provider for Claim Atomization v0.1.

This provider:
- receives only the source claim;
- does not receive chunks_used;
- does not evaluate factual support;
- returns structured atomization output;
- is not integrated into /evaluate/v2.
"""

from __future__ import annotations

import os
import time

from google import genai
from google.genai import types
from pydantic import ValidationError

from data_ai.evaluation.claim_atomizer import (
    ClaimAtomizationOutput,
)


PROMPT_VERSION = "claim-atomizer-v0.1"


SYSTEM_PROMPT = """
Eres un atomizador de afirmaciones factuales.

Tu tarea es descomponer UN claim fuente en afirmaciones factuales
mínimas que puedan evaluarse de forma independiente.

NO evalúes si las afirmaciones son verdaderas.
NO evalúes si están respaldadas por evidencia.
NO uses conocimiento externo.
NO inventes información.
NO completes contexto faltante.
NO elimines calificadores relevantes.

Debes preservar expresiones como:
- automáticamente;
- todos;
- ninguno;
- siempre;
- únicamente;
- antes;
- después;
- otra vez;
- sin;
- por defecto;
- completamente.

CLASES DE ATOMIZACIÓN

atomic:
El claim ya puede evaluarse como una única unidad factual.

compound:
El claim contiene dos o más proposiciones factuales independientes.

relational:
El claim contiene una relación factual relevante como:
- temporal;
- causal;
- condicional;
- comparativa;
- negación/ausencia;
- alcance/cu cuantificación.

TIPOS DE ÁTOMO

- factual_proposition
- temporal_relation
- causal_relation
- conditional_relation
- comparative_relation
- negation_or_absence
- scope_or_quantifier

REGLAS

1. No dividas solo porque una oración sea larga.
2. No combines proposiciones independientes si deben poder evaluarse separadas.
3. No elimines relaciones temporales, causales, negativas o condicionales.
4. No conviertas un calificador en algo más débil.
5. Un claim atómico debe producir exactamente un átomo.
6. Cada átomo debe conservar significado suficiente para ser evaluado de forma independiente.
7. No produzcas fragmentos como "Antes de eso". Reconstruye la relación completa.
8. No generes afirmaciones que no estén presentes en el source claim.

EJEMPLO 1

Input:
Crear solicitudes eficaces para LLM.

Output conceptual:
atomization_class = atomic
atoms:
- Crear solicitudes eficaces para LLM.
  factual_proposition

EJEMPLO 2

Input:
Antes de eso, la serie enseña conceptos básicos de la nube.

Output conceptual:
atomization_class = relational
atoms:
- La serie enseña conceptos básicos de la nube.
  factual_proposition
- La enseñanza de conceptos básicos de la nube ocurre antes del evento o contexto referido.
  temporal_relation

EJEMPLO 3

Input:
Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

Output conceptual:
atomization_class = compound
atoms:
- Los cuatro elementos mencionados son bloques fundamentales.
  factual_proposition
- Los cuatro bloques no tienen una secuencia clara.
  negation_or_absence
""".strip()


class GeminiClaimAtomizer:
    """Gemini-backed experimental Claim Atomization provider."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        resolved_api_key = (
            api_key
            or os.getenv(
                "DATA_IA_GEMINI_API_KEY",
                "",
            )
        ).strip()

        resolved_model = (
            model
            or os.getenv(
                "DATA_IA_GEMINI_MODEL",
                "",
            )
        ).strip()

        if not resolved_api_key:
            raise ValueError(
                "DATA_IA_GEMINI_API_KEY is required."
            )

        if not resolved_model:
            raise ValueError(
                "DATA_IA_GEMINI_MODEL is required."
            )

        self._client = genai.Client(
            api_key=resolved_api_key,
        )

        self._model = resolved_model

    @property
    def model(self) -> str:
        return self._model

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION

    def atomize(
        self,
        *,
        source_claim_id: str,
        claim_text: str,
        format: str,
    ) -> ClaimAtomizationOutput:
        del source_claim_id

        prompt = f"""
FORMAT:
{format}

SOURCE CLAIM:
{claim_text}

INSTRUCCIÓN:
Descompón el source claim siguiendo estrictamente las reglas del sistema.

No evalúes soporte factual.
No uses chunks.
No uses conocimiento externo.
Devuelve únicamente la estructura solicitada.
""".strip()

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ClaimAtomizationOutput,
                temperature=0.0,
            ),
        )

        parsed = getattr(
            response,
            "parsed",
            None,
        )

        if parsed is not None:
            if isinstance(
                parsed,
                ClaimAtomizationOutput,
            ):
                return parsed

            return ClaimAtomizationOutput.model_validate(
                parsed
            )

        raw_text = (
            getattr(
                response,
                "text",
                None,
            )
            or ""
        ).strip()

        if not raw_text:
            raise RuntimeError(
                "Gemini returned an empty atomization response."
            )

        try:
            return ClaimAtomizationOutput.model_validate_json(
                raw_text
            )
        except ValidationError as exc:
            raise ValueError(
                "Gemini returned invalid atomization output."
            ) from exc