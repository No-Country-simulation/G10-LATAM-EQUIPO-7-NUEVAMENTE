# Calibration Extension v1

## 1. Objetivo

Este documento define una extensión controlada de la calibración para cubrir escenarios que todavía no están representados de forma suficiente en `calibration_v1`.

La extensión busca generar evidencia adicional para la futura **Decision Layer**, especialmente en:

- conflictos entre heurística y evaluación semántica;
- estados `failed` y `unavailable`;
- casos potencialmente candidatos a `rejected`;
- corrección seguida de reevaluación;
- degradación simultánea de múltiples dimensiones.

Esta extensión no reemplaza `calibration_v1`; la complementa.

---

## 2. Alcance propuesto

Se proponen **8 casos nuevos**:

| ID | Tipo | Objetivo principal |
|---|---|---|
| `CAL-EXT-V1-001` | heuristic_semantic_conflict | heurística alta vs soporte semántico bajo |
| `CAL-EXT-V1-002` | heuristic_semantic_conflict | heurística baja vs semántica alta |
| `CAL-EXT-V1-003` | semantic_failed | fallback ante `failed` |
| `CAL-EXT-V1-004` | semantic_unavailable | fallback ante `unavailable` |
| `CAL-EXT-V1-005` | severe_unsupported_claim | explorar candidato a `rejected` |
| `CAL-EXT-V1-006` | multi_dimension_failure | varias dimensiones degradadas |
| `CAL-EXT-V1-007` | revision_before | contenido defectuoso previo a corrección |
| `CAL-EXT-V1-008` | revision_after | contenido corregido y reevaluado |

---

## 3. Principios de diseño

Los casos deben:

- reutilizar documentos y chunks existentes cuando sea posible;
- modificar únicamente el contenido generado o el estado del evaluador;
- mantener trazabilidad con el caso fuente;
- definir Ground Truth humano explícito;
- evitar pesos arbitrarios;
- separar dimensión objetivo de verdict esperado;
- conservar `chunks_used` como única evidencia factual.

---

## 4. Caso CAL-EXT-V1-001

### Tipo

`heuristic_semantic_conflict`

### Objetivo

Crear un caso donde la heurística resulte favorable, pero exista una afirmación factual claramente no respaldada por `chunks_used`.

### Diseño esperado

- formato sugerido: `tldr` o `flashcards`;
- relevance: alta;
- coherence: alta;
- didactic_adaptation: alta;
- content_support semántico: bajo;
- `unsupported_information`: presente.

### Ground Truth esperado

```text
expected_verdict: requires_revision
```

### Pregunta de calibración

¿La Decision Layer evita aprobar el contenido cuando la señal heurística es favorable pero existe un problema factual confirmado?

---

## 5. Caso CAL-EXT-V1-002

### Tipo

`heuristic_semantic_conflict`

### Objetivo

Crear un caso donde la heurística sea conservadora o baja, pero la evaluación semántica confirme que el contenido está correctamente respaldado.

### Diseño esperado

- contenido factual correcto;
- soporte completo en `chunks_used`;
- posible penalización heurística por estructura o forma;
- semantic content_support alto;
- `unsupported_information`: ausente.

### Ground Truth esperado

```text
expected_verdict: requires_revision
```

si existe un defecto real de forma o adaptación;

o:

```text
expected_verdict: approved
```

si la degradación heurística resulta ser un falso positivo.

### Pregunta de calibración

¿La Decision Layer distingue correctamente un defecto estructural de un defecto factual?

---

## 6. Caso CAL-EXT-V1-003

### Tipo

`semantic_failed`

### Objetivo

Validar comportamiento de fallback cuando el Semantic Evaluator devuelve:

```text
status = failed
```

### Simulación sugerida

Representar un resultado como:

```text
semantic_status: failed
error_code: provider_error
```

sin modificar Backend ni proveedor productivo.

El caso debe probarse a nivel de Decision Layer con una entrada controlada.

### Ground Truth esperado

```text
expected_behavior: heuristic_fallback
```

### Regla esperada

El estado `failed` no debe convertirse automáticamente en `rejected`.

---

## 7. Caso CAL-EXT-V1-004

### Tipo

`semantic_unavailable`

### Objetivo

Validar comportamiento cuando:

```text
semantic_status: unavailable
error_code: not_configured
```

### Ground Truth esperado

```text
expected_behavior: heuristic_fallback
```

### Regla esperada

La ausencia de señal semántica debe quedar registrada y no debe interpretarse como baja calidad del contenido.

---

## 8. Caso CAL-EXT-V1-005

### Tipo

`severe_unsupported_claim`

### Objetivo

Construir un caso con una afirmación factual central, explícita y claramente incompatible o ausente de `chunks_used`.

Debe ser más grave que los casos actuales de `unsupported_claim`.

### Ejemplo conceptual

El chunk describe una tecnología o concepto A, mientras que el contenido generado atribuye una capacidad crítica B que no aparece en la evidencia y cambia el significado principal.

### Ground Truth inicial

```text
expected_verdict: human_review_required
```

No se fija todavía `rejected` automáticamente.

### Motivo

La calibración actual no contiene evidencia suficiente para congelar criterios de rechazo.

### Pregunta de calibración

¿Qué gravedad y combinación de señales justificarían pasar de `requires_revision` a `rejected`?

---

## 9. Caso CAL-EXT-V1-006

### Tipo

`multi_dimension_failure`

### Objetivo

Crear un caso con degradación simultánea en varias dimensiones.

### Diseño esperado

Ejemplo:

```text
relevance: baja
coherence: baja
didactic_adaptation: baja
content_support: correcto
```

o:

```text
relevance: media
coherence: baja
didactic_adaptation: baja
content_support: bajo
```

### Ground Truth esperado

```text
expected_verdict: requires_revision
```

### Pregunta de calibración

¿La Decision Layer puede explicar qué reglas se activaron sin reducir todo a un promedio?

---

## 10. Caso CAL-EXT-V1-007

### Tipo

`revision_before`

### Objetivo

Representar el estado previo a una corrección automática.

### Diseño esperado

El contenido debe incluir un defecto claro y corregible, por ejemplo:

- baja relevancia;
- baja coherencia;
- adaptación didáctica deficiente;
- unsupported information confirmado.

### Ground Truth esperado

```text
expected_verdict: requires_revision
```

### Trazabilidad

Debe enlazarse explícitamente con `CAL-EXT-V1-008`.

---

## 11. Caso CAL-EXT-V1-008

### Tipo

`revision_after`

### Objetivo

Representar el contenido después de una corrección exitosa del caso anterior.

### Diseño esperado

Debe conservar:

- mismo documento;
- mismos `chunks_used`;
- mismo objetivo de generación;
- mismo formato.

Solo debe cambiar el contenido generado.

### Ground Truth esperado

```text
expected_verdict: approved
```

si la corrección elimina el defecto sin introducir uno nuevo.

### Pregunta de calibración

¿La reevaluación refleja una mejora real y trazable?

---

## 12. Ground Truth propuesto

Cada caso debe registrar como mínimo:

```text
calibration_id
source_case_id
scenario_type
format
target_dimension
expected_relevance_min
expected_relevance_max
expected_coherence_min
expected_coherence_max
expected_didactic_adaptation_min
expected_didactic_adaptation_max
expected_content_support_min
expected_content_support_max
expected_unsupported_information
expected_semantic_status
expected_verdict
expected_decision_behavior
review_notes
```

---

## 13. Nuevos valores de expected_decision_behavior

Se propone utilizar valores descriptivos para separar la evidencia del verdict final:

```text
normal_decision
heuristic_fallback
conflict_resolution
human_review_required
revision_expected
approval_after_revision
```

Estos valores son artefactos de calibración y no implican cambios automáticos en el schema productivo.

---

## 14. Reglas que estos casos deben validar

### DL-01

Aprobación cuando señales completas no muestran defectos relevantes.

### DL-02

`requires_revision` para defectos corregibles.

### DL-03

Tratamiento de `unsupported_information` como señal fuerte, no como regla binaria absoluta.

### DL-04

Fallback ante `failed` y `unavailable`.

### DL-05

Resolución explícita de conflictos heurístico-semánticos.

### DL-06

Exploración de criterios para `rejected` sin congelarlos prematuramente.

---

## 15. Orden recomendado de construcción

### Fase A

Construir primero:

- `CAL-EXT-V1-001`
- `CAL-EXT-V1-002`
- `CAL-EXT-V1-006`

Estos casos no dependen de fallos operativos ni de Agents.

### Fase B

Construir:

- `CAL-EXT-V1-003`
- `CAL-EXT-V1-004`

como entradas controladas para validar fallback.

### Fase C

Construir:

- `CAL-EXT-V1-005`

y realizar revisión humana antes de asignar un verdict definitivo.

### Fase D

Construir el par:

- `CAL-EXT-V1-007`
- `CAL-EXT-V1-008`

para validar corrección → reevaluación.

---

## 16. Archivos propuestos

Directorio:

```text
Data_IA/data/evaluation/calibration_extension_v1/
```

Estructura:

```text
calibration_extension_v1/
├── cases/
│   ├── CAL-EXT-V1-001.json
│   ├── CAL-EXT-V1-002.json
│   ├── CAL-EXT-V1-003.json
│   ├── CAL-EXT-V1-004.json
│   ├── CAL-EXT-V1-005.json
│   ├── CAL-EXT-V1-006.json
│   ├── CAL-EXT-V1-007.json
│   └── CAL-EXT-V1-008.json
├── human_ground_truth_extension_v1.csv
├── calibration_extension_manifest_v1.json
├── CALIBRATION_EXTENSION_V1.md
└── results/
```

---

## 17. Manifest propuesto

El manifest debe incluir:

```text
version
created_at
source_calibration_version
case_count
scenario_distribution
formats
ground_truth_file
decision_layer_spec
notes
```

Distribución inicial:

```text
heuristic_semantic_conflict: 2
semantic_failed: 1
semantic_unavailable: 1
severe_unsupported_claim: 1
multi_dimension_failure: 1
revision_before: 1
revision_after: 1
```

Total:

```text
8 casos
```

---

## 18. Criterios de aceptación de la extensión

Calibration Extension v1 estará lista para ejecutarse cuando:

1. Existan los 8 casos.
2. Todos tengan Ground Truth humano.
3. Los casos de conflicto tengan señales deliberadamente opuestas.
4. Los casos `failed` y `unavailable` tengan comportamiento esperado documentado.
5. El caso grave tenga revisión humana explícita.
6. El par before/after sea comparable.
7. El manifest valide conteos y tipos.
8. No se modifique código de Backend, Agents o Frontend.

---

## 19. Qué no debe hacerse todavía

No se debe:

- asignar pesos a las dimensiones;
- convertir `unsupported_information` en una regla automática de rechazo;
- definir `rejected` solo a partir de un score;
- cambiar el schema productivo por estos casos;
- alterar Backend para simular estados;
- alterar Agents para crear artificialmente la corrección;
- mezclar esta extensión con Stability v1.

Stability v1 y Calibration Extension v1 responden preguntas distintas:

```text
Stability v1:
¿el evaluador produce resultados consistentes?

Calibration Extension v1:
¿las reglas candidatas de decisión cubren escenarios que faltaban?
```

---

## 20. Próximos pasos

1. Seleccionar casos fuente de `calibration_v1`.
2. Construir `CAL-EXT-V1-001`.
3. Revisar Ground Truth humano.
4. Construir `CAL-EXT-V1-002`.
5. Construir `CAL-EXT-V1-006`.
6. Validar estructura JSON común.
7. Construir casos de fallback.
8. Diseñar el caso grave.
9. Construir el par before/after.
10. Validar manifest y Ground Truth completo.
