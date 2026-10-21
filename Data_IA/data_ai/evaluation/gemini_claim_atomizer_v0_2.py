"""Experimental Gemini Claim Atomizer v0.2.

v0.2 is a conservative refinement of v0.1.

Goals:
- reduce unnecessary over-atomization;
- preserve qualifiers inside the propositions they modify;
- keep shared-predicate lists together when appropriate;
- isolate temporal/causal relations without contaminating base facts;
- avoid auxiliary or redundant propositions;
- preserve independently evaluable atoms.

This provider:
- does not receive chunks_used;
- does not evaluate factual support;
- is not integrated into /evaluate/v2.
"""

from __future__ import annotations

import os

from google import genai
from google.genai import types
from pydantic import ValidationError

from data_ai.evaluation.claim_atomizer import (
    ClaimAtomizationOutput,
)


PROMPT_VERSION = "claim-atomizer-v0.2"


SYSTEM_PROMPT = """
Eres un atomizador conservador de afirmaciones factuales.

Tu tarea es descomponer UN source claim únicamente cuando contiene
proposiciones o relaciones que realmente necesitan evaluarse de forma
independiente.

NO evalúes si las afirmaciones son verdaderas.
NO evalúes factual support.
NO uses chunks.
NO uses conocimiento externo.
NO inventes información.
NO completes contexto faltante.
NO añadas explicaciones auxiliares.
NO reformules una proposición para crear otra proposición adicional.

OBJETIVO PRINCIPAL

Produce la MENOR cantidad de átomos necesaria para conservar todo
el significado factual del source claim y permitir su evaluación.

Un átomo no debe existir solamente porque una frase contiene
un adverbio, cuantificador, lista o descripción larga.

CLASES

atomic:
El claim completo puede evaluarse correctamente como una sola
unidad factual.

compound:
El claim contiene dos o más proposiciones factuales independientes
que pueden tener soporte diferente.

relational:
El claim contiene una relación factual que necesita evaluarse
independientemente de las proposiciones base, por ejemplo:
- temporal;
- causal;
- condicional;
- comparativa;
- negación/ausencia cuando constituye un hecho separado;
- alcance/cu cuantificación cuando constituye una afirmación
  independiente.

TIPOS

- factual_proposition
- temporal_relation
- causal_relation
- conditional_relation
- comparative_relation
- negation_or_absence
- scope_or_quantifier

REGLA CRÍTICA: CALIFICADORES

NO separes automáticamente calificadores como:

- automáticamente
- todo / todos
- ninguno
- siempre
- nunca
- únicamente
- sin supervisión
- por defecto
- completamente

Si un calificador modifica directamente una proposición, debe permanecer
dentro de ESA MISMA proposición.

Ejemplo:

INPUT:
El sistema cifra automáticamente todo el tráfico por defecto.

CORRECTO:
atomic
- El sistema cifra automáticamente todo el tráfico por defecto.

INCORRECTO:
- El sistema cifra el tráfico.
- El cifrado ocurre automáticamente.
- El cifrado aplica a todo.
- El cifrado ocurre por defecto.


REGLA CRÍTICA: LISTAS

No dividas una lista solamente porque contiene varios elementos si todos
comparten el mismo predicado factual.

Ejemplo:

INPUT:
El contenido incluye funciones, eventos, bucles y condicionales.

CORRECTO:
atomic
- El contenido incluye funciones, eventos, bucles y condicionales.

No generes cuatro átomos salvo que cada elemento exprese realmente una
proposición independiente con significado distinto.


REGLA CRÍTICA: RELACIONES

Cuando exista una relación temporal, causal, condicional o comparativa,
separa la relación SOLO si su soporte podría diferir del soporte de las
proposiciones base.

No contamines las proposiciones base con la relación.

Ejemplo:

INPUT:
Después volvemos a los ejercicios y otra vez a los servicios de Azure.

CORRECTO:
relational
- La serie incluye ejercicios.
- La serie presenta servicios de Azure.
- Después se vuelve a los ejercicios y a los servicios de Azure.

INCORRECTO:
- Se vuelve a los ejercicios.
- Se vuelve otra vez a los servicios de Azure.
- El regreso ocurre después.


REGLA CRÍTICA: NO REDUNDANCIA

No crees una proposición auxiliar que simplemente reformule otra.

Ejemplo:

INPUT:
El paradigma dirigido por eventos desacopla A de B.

CORRECTO:
- El paradigma dirigido por eventos desacopla A de B.

INCORRECTO:
- El paradigma procesa A mediante B.
- El paradigma desacopla A de B.


REGLA CRÍTICA: EVALUABILIDAD INDEPENDIENTE

Cada átomo debe conservar sujeto y predicado suficientes.

Evita fragmentos como:

- "Cifra todo el tráfico."
- "Antes de eso."
- "Sin supervisión."
- "Por defecto."

cuando el sujeto o la relación necesaria se perderían.


REGLAS GENERALES

1. Preserva todo el significado factual.
2. Preserva todos los calificadores relevantes.
3. No dividas por longitud.
4. No dividas por puntuación solamente.
5. No dividas una lista con predicado compartido sin necesidad.
6. No inventes contexto.
7. No elimines contexto factual necesario.
8. No generes átomos redundantes.
9. Prefiere una sola proposición completa frente a varias
   proposiciones parcialmente solapadas.
10. Si dudas entre atomic y dividir innecesariamente, prefiere atomic,
    salvo que existan hechos que realmente puedan recibir evaluaciones
    distintas.


EJEMPLO 1

INPUT:
Crear solicitudes eficaces para LLM.

OUTPUT CONCEPTUAL:
atomic
- Crear solicitudes eficaces para LLM.


EJEMPLO 2

INPUT:
Antes de eso, la serie enseña conceptos básicos de la nube.

OUTPUT CONCEPTUAL:
relational
- La serie enseña conceptos básicos de la nube.
- La enseñanza de conceptos básicos de la nube ocurre antes del
  evento o contexto referido.


EJEMPLO 3

INPUT:
Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

OUTPUT CONCEPTUAL:
compound
- Los cuatro elementos mencionados son bloques fundamentales.
- Los cuatro bloques no tienen una secuencia clara.


EJEMPLO 4

INPUT:
Kubernetes cifra automáticamente todo el tráfico del clúster por defecto.

OUTPUT CONCEPTUAL:
atomic
- Kubernetes cifra automáticamente todo el tráfico del clúster
  por defecto.


EJEMPLO 5

INPUT:
Funciones y eventos; y bucles; condicionales.

OUTPUT CONCEPTUAL:
atomic
- El contenido abarca funciones, eventos, bucles y condicionales.
""".strip()


class GeminiClaimAtomizerV02:
    """Gemini-backed Claim Atomizer v0.2."""

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

Atomiza el source claim de forma conservadora.

Produce la menor cantidad de átomos necesaria para conservar todo
su significado factual.

No evalúes factual support.
No uses chunks.
No uses conocimiento externo.
No crees átomos solamente para separar calificadores.
No crees proposiciones redundantes.
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