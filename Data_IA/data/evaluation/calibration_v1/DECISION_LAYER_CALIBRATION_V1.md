# Decision Layer Calibration v1

## 1. Objetivo

Este documento define una primera especificación de calibración para la futura **Decision Layer** de Data/IA.

Su objetivo es transformar las señales producidas por los evaluadores en una decisión final reproducible, explicable y trazable, sin introducir promedios simples, pesos arbitrarios ni reglas no respaldadas por evidencia.

Esta versión no representa todavía una política productiva definitiva. Funciona como especificación de trabajo para validar reglas candidatas antes de integrarlas en el flujo completo del sistema.

---

## 2. Alcance

La Decision Layer recibe señales independientes provenientes de:

- evaluación heurística;
- evaluación semántica;
- estado operativo del evaluador semántico;
- evidencia de `unsupported_information`.

La Decision Layer debe producir un resultado compatible con:

- `approved`
- `requires_revision`
- `rejected`

La decisión final debe permanecer separada de la generación de scores individuales.

---

## 3. Principios de diseño

### 3.1 Separación de dimensiones

Las dimensiones deben interpretarse de forma independiente:

- `relevance`
- `coherence`
- `didactic_adaptation`
- `content_support`

Una puntuación baja en una dimensión no debe arrastrar automáticamente a otra.

Ejemplo:

Un contenido puede estar completamente respaldado por los chunks y, al mismo tiempo, tener baja relevancia respecto del objetivo de generación.

Esto fue observado durante la calibración humana en `CAL-V1-012`.

### 3.2 Sin promedio simple

No se debe calcular un promedio simple de scores para decidir el verdict.

Un promedio puede ocultar defectos críticos.

Ejemplo conceptual:

```text
relevance: 5.0
coherence: 5.0
didactic_adaptation: 5.0
content_support: 1.5
```

El promedio sería relativamente alto, pero el bajo `content_support` puede indicar un problema factual relevante.

### 3.3 Sin pesos arbitrarios

No deben utilizarse fórmulas como:

`0.3 * relevance + 0.2 * coherence + ...`

hasta contar con evidencia de calibración suficiente que justifique esos pesos.

### 3.4 Explicabilidad

Toda decisión debe poder explicarse mediante:

- señales recibidas;
- dimensión o condición activada;
- regla aplicada;
- resultado final.

### 3.5 Trazabilidad

Cada evaluación debe conservar:

- scores heurísticos;
- resultado semántico;
- `unsupported_information`;
- versión del evaluador;
- versión del prompt;
- versión de las reglas de Decision Layer.

---

## 4. Evidencia de calibración utilizada

La calibración v1 contiene 20 casos controlados.

Resultados consolidados:

```text
Casos con evaluación semántica: 20/20
Dimensión objetivo dentro del rango humano: 20/20
Unsupported information alineado con Ground Truth humano: 18/20
```

Los dos desacuerdos restantes son:

- `CAL-V1-011`
- `CAL-V1-012`

Ambos se consideran falsos positivos probables de `unsupported_information`.

Por esta razón, la presencia de `unsupported_information` no debe utilizarse todavía como regla binaria absoluta.

---

## 5. Interpretación de señales

### 5.1 Heuristic Scores

Los heuristic scores representan señales estructuradas y deterministas del evaluador actual.

Actualmente el verdict V2 existente continúa dependiendo del flujo heurístico legado.

La Decision Layer futura no debe reemplazar esta señal sin una etapa de calibración explícita.

### 5.2 Semantic Evaluation

El evaluador semántico proporciona:

- scores por dimensión;
- observaciones;
- recomendaciones;
- `unsupported_information`;
- estado de ejecución;
- metadatos del proveedor.

El evaluador semántico no debe producir por sí solo el verdict final.

### 5.3 Unsupported Information

`unsupported_information` representa afirmaciones potencialmente no respaldadas por `chunks_used`.

Regla de evidencia:

`chunks_used` es la única fuente válida para evaluar soporte factual.

`generation_context` puede apoyar la interpretación de relevancia o adaptación didáctica, pero no debe utilizarse como evidencia factual.

---

## 6. Estados operativos del Semantic Evaluator

La Decision Layer debe distinguir entre:

### `success`

La evaluación semántica es válida y puede utilizarse como señal.

### `failed`

El proveedor fue invocado, pero la evaluación no pudo completarse correctamente.

Ejemplos:

- `provider_error`
- `timeout`
- `invalid_output`

### `unavailable`

El evaluador semántico no estaba configurado o disponible.

Ejemplo:

- `not_configured`

Un estado `failed` o `unavailable` no debe convertirse automáticamente en `rejected`.

La Decision Layer debe aplicar un fallback explícito y trazable.

---

## 7. Reglas candidatas v1

Estas reglas son candidatas y deben validarse antes de declararse productivas.

### Regla DL-01 — Señales completas y sin defectos relevantes

Condición candidata:

- evaluación semántica `success`;
- señales heurísticas disponibles;
- scores compatibles con el rango esperado;
- sin defectos críticos detectados.

Resultado candidato:

`approved`

### Regla DL-02 — Defecto corregible

Condición candidata:

Existe evidencia clara de un problema relevante en una o más dimensiones, pero el contenido puede corregirse mediante una nueva generación o revisión.

Ejemplos:

- baja relevancia;
- baja coherencia;
- adaptación didáctica deficiente;
- soporte factual insuficiente corregible.

Resultado candidato:

`requires_revision`

### Regla DL-03 — Unsupported Information

La presencia de `unsupported_information` debe tratarse como una señal fuerte, pero no como un verdict automático.

Antes de utilizar esta señal debe comprobarse:

- que el elemento sea realmente una afirmación factual;
- que no sea un distractor deliberado de un quiz;
- que no sea framing o texto creativo sin pretensión factual;
- que no exista soporte semánticamente equivalente en `chunks_used`.

Resultado candidato:

`requires_revision` cuando el hallazgo sea confirmado.

No se define todavía una transición automática a `rejected`.

### Regla DL-04 — Semantic Evaluator no disponible

Condición:

`semantic_status` es `failed` o `unavailable`.

La Decision Layer no debe inferir calidad semántica inexistente.

Resultado candidato:

usar fallback heurístico y registrar explícitamente que la decisión se tomó sin señal semántica.

La política exacta de fallback debe validarse en integración.

### Regla DL-05 — Conflicto entre señales

Cuando heurística y semántica discrepen de forma material, la Decision Layer no debe promediar automáticamente.

Debe registrarse el conflicto y aplicar una regla específica según la dimensión afectada.

Ejemplo conceptual:

```text
heuristic content_support: alto
semantic content_support: bajo
```

Este tipo de caso debe utilizarse para ampliar la calibración antes de congelar reglas definitivas.

### Regla DL-06 — Rejected

La calibración v1 no contiene suficientes casos humanos etiquetados como `rejected`.

Por lo tanto, esta versión no define todavía un criterio productivo definitivo para `rejected`.

Cualquier regla futura de rechazo deberá contar con casos de Ground Truth específicos y evidencia suficiente.

---

## 8. Reglas por dimensión

### Relevance

Baja relevancia debe afectar `relevance`, no `content_support`, salvo que además exista evidencia factual no respaldada.

Hallazgo relacionado:

`CAL-V1-012`.

### Coherence

Baja coherencia puede justificar `requires_revision` cuando afecta significativamente la comprensión o estructura del contenido.

No implica automáticamente falta de soporte factual.

### Didactic Adaptation

Una adaptación didáctica deficiente puede justificar revisión aunque el contenido sea factual y relevante.

No debe confundirse con alucinación.

### Content Support

Debe evaluarse exclusivamente contra `chunks_used`.

Una puntuación baja puede justificar `requires_revision` cuando existen afirmaciones factuales no respaldadas.

---

## 9. Reglas por formato derivadas de calibración

### Quiz

Los distractores incorrectos no deben interpretarse automáticamente como afirmaciones factuales no respaldadas.

El soporte factual debe concentrarse principalmente en:

- pregunta;
- respuesta correcta;
- explicación.

Hallazgo relacionado:

`CAL-V1-011`.

### Flashcards

Debe mantenerse una separación estricta entre relevancia y soporte factual.

Una tarjeta puede estar respaldada por el chunk pero ser poco relevante respecto del objetivo.

Hallazgo relacionado:

`CAL-V1-012`.

### TLDR

Título y framing no deben penalizarse automáticamente como unsupported.

Si contienen afirmaciones factuales verificables, sí deben evaluarse contra `chunks_used`.

### Video Script

Las descripciones visuales y de escena no deben considerarse automáticamente afirmaciones factuales.

Cuando incluyan información factual explícita, dicha información sí debe validarse.

La narración continúa siendo la principal superficie de evaluación factual.

---

## 10. Flujo lógico candidato

```text
Evaluation Request
        |
        v
Heuristic Evaluation
        |
        +------------------+
        |                  |
        v                  v
Semantic Evaluation     Semantic unavailable/failed
        |                  |
        v                  v
Signal Validation      Heuristic fallback
        |                  |
        +--------+---------+
                 |
                 v
          Decision Layer
                 |
        +--------+---------+
        |        |         |
        v        v         v
    approved  requires   rejected
              revision
```

La Decision Layer debe ser stateless respecto del ciclo completo de corrección.

El control de reintentos, terminación del ciclo, persistencia y `evaluation_id` corresponde al Backend.

---

## 11. Contrato conceptual de entrada

Ejemplo conceptual:

```json
{
  "heuristic_scores": {
    "relevance": 4.5,
    "coherence": 4.0,
    "didactic_adaptation": 4.5,
    "content_support": 4.0
  },
  "semantic_evaluation": {
    "status": "success",
    "scores": {
      "relevance": 4.5,
      "coherence": 4.5,
      "didactic_adaptation": 4.0,
      "content_support": 4.5
    },
    "unsupported_information": []
  }
}
```

La estructura final deberá alinearse con los schemas productivos existentes.

---

## 12. Contrato conceptual de salida

Ejemplo:

```json
{
  "verdict": "requires_revision",
  "decision_reason": {
    "rule_id": "DL-03",
    "dimension": "content_support",
    "summary": "Se detectó una afirmación factual no respaldada por chunks_used."
  },
  "decision_layer_version": "decision-layer-calibration-v1"
}
```

`decision_reason` es una propuesta conceptual y no implica todavía un cambio obligatorio en el schema V2.

---

## 13. Casos que deben añadirse a calibración

Antes de congelar reglas productivas se recomienda incorporar casos humanos que cubran:

- conflictos entre heurística y semántica;
- múltiples dimensiones degradadas simultáneamente;
- `semantic_status=failed`;
- `semantic_status=unavailable`;
- unsupported information grave;
- contenido que requiera `rejected`;
- corrección seguida de reevaluación;
- estabilidad entre múltiples ejecuciones.

---

## 14. Criterios para congelar Decision Layer v1

La Decision Layer no debería declararse estable hasta cumplir al menos:

1. Prompt semántico ajustado por formato.
2. `CAL-V1-011` y `CAL-V1-012` reevaluados.
3. Estabilidad validada en múltiples corridas.
4. Ground Truth ampliado con casos de conflicto y rechazo.
5. Reglas candidatas verificadas contra el dataset.
6. Fallback de `failed` y `unavailable` validado.
7. Flujo corrección → reevaluación probado.
8. Contrato Backend ↔ Data/IA validado en E2E.
9. Versionado explícito de reglas y artefactos.

---

## 15. Decisiones explícitamente fuera de alcance en v1

Esta versión no define:

- pesos matemáticos entre dimensiones;
- promedio global de scores;
- umbrales productivos definitivos;
- regla definitiva para `rejected`;
- número de reintentos;
- persistencia;
- terminación del ciclo;
- lógica de Backend;
- lógica de Agents;
- lógica de Frontend.

---

## 16. Ownership

Data/IA es responsable de:

- scores y señales de evaluación;
- calibración;
- definición de reglas candidatas;
- versionado de la Decision Layer;
- documentación de evidencia y limitaciones.

Backend es responsable de:

- orquestación;
- aplicación del ciclo;
- reintentos;
- persistencia;
- historial;
- terminación;
- `evaluation_id`.

Agents es responsable de:

- generación;
- revisión/corrección del contenido.

Frontend consume los resultados expuestos por Backend.

---

## 17. Estado actual

Estado de esta especificación:

`draft-calibration`

No debe considerarse todavía una regla productiva congelada.

La evidencia actual permite definir guardrails candidatos, pero todavía no justifica pesos arbitrarios ni políticas definitivas de rechazo.

---

## 18. Próximos pasos

1. Incorporar los ajustes del Semantic Evaluator derivados de `CAL-V1-011` y `CAL-V1-012`.
2. Reevaluar ambos casos.
3. Validar estabilidad entre corridas.
4. Revisar calidad de `observations` y `recommendations`.
5. Diseñar casos humanos específicos para `rejected`.
6. Validar casos de conflicto heurístico-semántico.
7. Definir fallback formal para `failed` y `unavailable`.
8. Probar corrección → reevaluación.
9. Versionar la primera regla candidata lista para integración.
