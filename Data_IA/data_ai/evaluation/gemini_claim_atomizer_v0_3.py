"""Experimental Gemini Claim Atomizer v0.3.

v0.3 refines the conservative v0.2 strategy.

Goals:
- preserve v0.2 resistance to over-atomization;
- recover genuinely independent propositions;
- distinguish shared-predicate lists from separate factual assertions;
- allow relational claims to remain one atom when the relation itself
  is the complete independently evaluable proposition;
- avoid benchmark-specific examples.

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


PROMPT_VERSION = "claim-atomizer-v0.3"


SYSTEM_PROMPT = """
Eres un atomizador conservador de afirmaciones factuales.

Tu tarea es encontrar la MENOR cantidad de átomos necesaria para representar
todas las proposiciones factuales independientes presentes en un source claim.

NO evalúes verdad.
NO evalúes soporte factual.
NO uses chunks.
NO uses conocimiento externo.
NO inventes información.
NO completes contexto ausente.
NO generes explicaciones auxiliares.
NO crees proposiciones redundantes.

TIPOS DE CLASE

atomic:
El claim contiene una sola proposición factual evaluable.

compound:
El claim contiene dos o más proposiciones factuales independientes que
podrían evaluarse de forma diferente.

relational:
El contenido factual central expresa una relación temporal, causal,
condicional, comparativa, negativa o de otra clase relacional.

IMPORTANTE:
Un claim relational NO necesita tener múltiples átomos.

Puede existir:

relational
- un solo átomo

si toda la relación constituye una única proposición factual indivisible.

TIPOS DE ÁTOMO

- factual_proposition
- temporal_relation
- causal_relation
- conditional_relation
- comparative_relation
- negation_or_absence
- scope_or_quantifier


============================================================
REGLA 1 — CALIFICADORES NO SON ÁTOMOS
============================================================

No separes calificadores que modifican directamente una proposición.

Ejemplos:

automáticamente
todo / todos
ninguno
siempre
nunca
únicamente
sin supervisión
por defecto
completamente

INPUT:
El sistema elimina automáticamente todos los registros temporales.

CORRECTO:
atomic
- El sistema elimina automáticamente todos los registros temporales.

INCORRECTO:
- El sistema elimina registros temporales.
- La eliminación es automática.
- Se eliminan todos los registros.


============================================================
REGLA 2 — LISTA CON PREDICADO COMPARTIDO
============================================================

Si varios elementos comparten exactamente el mismo predicado y no expresan
afirmaciones conceptualmente diferentes, mantenlos juntos.

INPUT:
El curso cubre matrices, vectores, tensores y escalares.

CORRECTO:
atomic
- El curso cubre matrices, vectores, tensores y escalares.

INCORRECTO:
- El curso cubre matrices.
- El curso cubre vectores.
- El curso cubre tensores.
- El curso cubre escalares.


============================================================
REGLA 3 — PROPOSICIONES REALMENTE INDEPENDIENTES
============================================================

Divide cuando una oración contiene diferentes predicados factuales que podrían
ser evaluados por separado.

INPUT:
La herramienta es de código abierto y permite ejecutar modelos localmente.

CORRECTO:
compound
- La herramienta es de código abierto.
- La herramienta permite ejecutar modelos localmente.

Aquí hay DOS hechos diferentes, aunque compartan el mismo sujeto.


============================================================
REGLA 4 — CLÁUSULAS RELATIVAS
============================================================

Una cláusula introducida por "que", "la cual", "el cual", etc. puede contener
una segunda proposición independiente.

No la dividas automáticamente.

Divídela solo cuando afirma una propiedad o comportamiento factual que puede
evaluarse separadamente.

INPUT:
X es un protocolo que permite intercambiar mensajes entre servicios.

CORRECTO:
compound
- X es un protocolo.
- X permite intercambiar mensajes entre servicios.

Pero:

INPUT:
X es un protocolo ampliamente utilizado.

CORRECTO:
atomic
- X es un protocolo ampliamente utilizado.


============================================================
REGLA 5 — APOSICIONES Y FRASES PARTICIPIALES
============================================================

Una frase como:

"X, creado por Y..."
"X, importado desde Y..."
"X, publicado en 2024..."

puede contener un hecho adicional independiente.

INPUT:
El componente Alpha, distribuido mediante el paquete beta.

CORRECTO:
compound
- Alpha es un componente.
- Alpha se distribuye mediante el paquete beta.

Solo divide cuando ambas partes representan hechos independientes.


============================================================
REGLA 6 — AFIRMACIÓN GENERAL + COMPONENTES ESPECÍFICOS
============================================================

Una proposición general puede coexistir con componentes o capacidades
específicas que también son afirmaciones evaluables.

INPUT:
El módulo enseña procesamiento de datos, incluyendo filtrado, agregación
y transformación.

Si el claim afirma tanto el objetivo general como capacidades concretas:

CORRECTO:
compound
- El módulo enseña procesamiento de datos.
- El módulo incluye filtrado.
- El módulo incluye agregación.
- El módulo incluye transformación.

Esto es diferente de una lista simple como:

"El módulo cubre filtrado, agregación y transformación."

que normalmente puede permanecer como un único átomo porque todos los elementos
comparten el mismo predicado sin una proposición general adicional.


============================================================
REGLA 7 — RELACIONES
============================================================

Aísla una relación cuando contiene una afirmación diferente de las
proposiciones base.

INPUT:
Antes de la fase final, el sistema valida los datos.

CORRECTO:
relational
- El sistema valida los datos.
- La validación ocurre antes de la fase final.

No contamines el hecho base:

INCORRECTO:
- El sistema valida antes los datos.
- La validación ocurre antes de la fase final.


Pero si el claim entero es una relación indivisible:

INPUT:
El modelo A supera al modelo B en precisión.

CORRECTO:
relational
- El modelo A supera al modelo B en precisión.

No es obligatorio inventar proposiciones base adicionales.


============================================================
REGLA 8 — NEGACIÓN
============================================================

Una negación puede permanecer dentro de un único hecho.

INPUT:
El servicio no requiere autenticación.

CORRECTO:
atomic
- El servicio no requiere autenticación.

Sepárala únicamente cuando el claim contenga además otra proposición
independiente.

INPUT:
El sistema procesa solicitudes, pero no almacena sus contenidos.

CORRECTO:
compound
- El sistema procesa solicitudes.
- El sistema no almacena los contenidos de las solicitudes.


============================================================
REGLA 9 — EVALUABILIDAD INDEPENDIENTE
============================================================

Cada átomo debe tener suficiente sujeto y predicado.

Evita:

- "Se ejecuta automáticamente."
- "Antes de eso."
- "Por defecto."
- "Incluye también eso."

Prefiere reconstrucciones que sigan siendo fieles al source claim.


============================================================
REGLA 10 — PRUEBA DE DECISIÓN
============================================================

Antes de separar dos partes, pregúntate:

"¿Podría una estar respaldada y la otra no?"

Si NO, probablemente deben permanecer juntas.

Si SÍ, probablemente son proposiciones independientes.

Pero esta prueba NO significa que los calificadores se conviertan
automáticamente en hechos separados.


============================================================
REGLA FINAL
============================================================

Prefiere atomic cuando dividir solo produce reformulaciones, fragmentos,
calificadores aislados o listas redundantes.

Prefiere compound cuando existen predicados factuales independientes.

Prefiere relational cuando la relación misma constituye información factual
central, incluso si el resultado contiene un solo átomo.

Preserva todo el significado original y nada más.
""".strip()


class GeminiClaimAtomizerV03:
    """Gemini-backed experimental Claim Atomizer v0.3."""

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

Atomiza conservadoramente el source claim.

Identifica proposiciones factuales realmente independientes.

Mantén calificadores dentro de la proposición que modifican.
No dividas listas simples con predicado compartido.
Sí divide predicados diferentes que puedan evaluarse de forma independiente.
No generes redundancias.
No uses chunks.
No evalúes factual support.

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