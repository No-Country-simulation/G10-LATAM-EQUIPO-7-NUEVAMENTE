# Stability Protocol v1

## 1. Objetivo

Este documento define el protocolo inicial para validar la **estabilidad entre corridas** del Semantic Evaluator de Data/IA.

El objetivo es comprobar si, ante el mismo caso de calibración y bajo la misma configuración, el evaluador produce resultados suficientemente consistentes en:

- `relevance`
- `coherence`
- `didactic_adaptation`
- `content_support`
- `unsupported_information`
- `observations`
- `recommendations`

Este protocolo no define todavía umbrales productivos definitivos. Su propósito es generar evidencia reproducible antes de congelar reglas de Decision Layer.

---

## 2. Alcance

La validación de estabilidad v1 utilizará una muestra reducida y representativa del dataset `calibration_v1`.

La muestra propuesta contiene 6 casos:

| Caso | Variante | Dimensión principal | Formato | Motivo |
|---|---|---|---|---|
| `CAL-V1-001` | `clean_reference` | `all` | quiz | baseline limpio |
| `CAL-V1-011` | `low_coherence` | coherence | quiz | falso positivo probable de unsupported |
| `CAL-V1-012` | `low_relevance` | relevance | flashcards | separación relevance vs content_support |
| `CAL-V1-016` | `poor_didactic_adaptation` | didactic_adaptation | tldr | caso con extrapolación secundaria |
| `CAL-V1-017` | `clean_reference` | `all` | quiz | baseline limpio recientemente cerrado |
| `CAL-V1-020` | `low_coherence` | coherence | video_script | cobertura de formato y caso con corrida previa en otro modelo |

La muestra cubre:

- casos limpios;
- baja coherencia;
- baja relevancia;
- mala adaptación didáctica;
- quiz;
- flashcards;
- TLDR;
- video script.

---

## 3. Momento de ejecución

El protocolo debe ejecutarse **después** de integrar los ajustes del prompt derivados de `CAL-V1-011` y `CAL-V1-012`.

No debe utilizarse la versión anterior del prompt para declarar estabilidad de la versión nueva.

Antes de comenzar, registrar:

- commit SHA;
- versión del prompt;
- proveedor;
- modelo;
- fecha;
- configuración relevante.

---

## 4. Número de corridas

Para Stability v1 se realizarán:

- **3 corridas por caso**
- **6 casos**
- **18 evaluaciones semánticas en total**

Tres corridas son suficientes para detectar variaciones evidentes sin consumir una cantidad excesiva de cuota.

Si un caso muestra inestabilidad relevante, podrá ampliarse posteriormente a 5 corridas.

---

## 5. Condiciones controladas

Todas las corridas comparables deben utilizar:

- el mismo archivo de caso;
- el mismo prompt versionado;
- el mismo modelo;
- el mismo proveedor;
- los mismos `chunks_used`;
- el mismo `generation_context`;
- la misma estructura de request.

No se deben mezclar modelos dentro de una misma comparación de estabilidad.

Si una corrida necesita otro modelo por cuota o disponibilidad, debe quedar fuera del cálculo principal y registrarse como ejecución auxiliar.

---

## 6. Variables a registrar

Por cada corrida deben almacenarse como mínimo:

```text
calibration_id
run_id
semantic_status
semantic_relevance
semantic_coherence
semantic_didactic_adaptation
semantic_content_support
unsupported_information_count
observations_count
recommendations_count
model
prompt_version
latency_ms
error_code
```

Además, se recomienda conservar el contenido completo de:

- `unsupported_information`
- `observations`
- `recommendations`

para revisión cualitativa.

---

## 7. Métricas de estabilidad cuantitativa

Para cada dimensión se calculará por caso:

- mínimo;
- máximo;
- media;
- desviación estándar;
- rango absoluto `max - min`.

Dimensiones:

- relevance;
- coherence;
- didactic adaptation;
- content support.

---

## 8. Criterio candidato de estabilidad de scores

Para Stability v1 se propone un criterio exploratorio:

### Estable

La dimensión se considera estable cuando:

```text
max(score) - min(score) <= 0.5
```

### Variación moderada

```text
0.5 < rango <= 1.0
```

Debe revisarse, pero no implica fallo automático.

### Inestable

```text
rango > 1.0
```

Requiere investigación antes de congelar reglas basadas en esa señal.

Estos valores son criterios de trabajo y no umbrales productivos definitivos.

---

## 9. Estabilidad de la dimensión objetivo

La dimensión objetivo de cada caso debe permanecer dentro del rango definido por `human_ground_truth_v1.csv` en todas las corridas.

Criterio esperado:

```text
target_dimension_in_human_range = True
```

para cada una de las 3 corridas.

Si una corrida sale fuera del rango humano, el caso debe marcarse para revisión.

---

## 10. Estabilidad de unsupported_information

`unsupported_information` debe revisarse como señal categórica además de cuantitativa.

Para cada caso se registrará:

- presencia/ausencia;
- número de elementos;
- contenido textual de los hallazgos.

### Criterio candidato

Un caso se considera estable en esta señal cuando las 3 corridas coinciden en:

```text
unsupported_detected = True
```

o:

```text
unsupported_detected = False
```

Si cambia entre corridas, debe considerarse una inestabilidad importante.

Para `CAL-V1-011` y `CAL-V1-012`, después del ajuste de prompt se espera:

```text
unsupported_detected = False
```

en las tres corridas.

---

## 11. Estabilidad cualitativa

No basta con comparar scores.

También debe revisarse si las corridas mantienen consistencia en:

- causa principal detectada;
- observaciones;
- recomendaciones;
- severidad implícita;
- dimensión afectada.

No se exige redacción idéntica.

Se busca equivalencia semántica.

Ejemplo aceptable:

```text
Run 1:
"La respuesta no se centra en el objetivo solicitado."

Run 2:
"El contenido se desvía del objetivo principal."

Run 3:
"La información presentada es poco relevante para la solicitud."
```

Aunque el texto cambia, la causa raíz es la misma.

---

## 12. Calidad de observations

Las `observations` deben cumplir:

- ser específicas;
- estar relacionadas con el contenido evaluado;
- identificar la dimensión afectada;
- no inventar evidencia externa;
- distinguir relevancia de soporte factual;
- evitar observaciones contradictorias entre corridas.

Se marcarán como:

```text
consistent
partially_consistent
inconsistent
```

---

## 13. Calidad de recommendations

Las `recommendations` deben ser:

- accionables;
- específicas;
- coherentes con la observación;
- posibles de aplicar en una corrección automática;
- estables en intención entre corridas.

No es necesario que utilicen exactamente las mismas palabras.

---

## 14. Manejo de errores

Si una corrida devuelve:

- `failed`
- `unavailable`
- `timeout`
- `provider_error`
- `invalid_output`

no debe sustituirse silenciosamente.

Debe registrarse.

La corrida puede repetirse únicamente para completar la muestra, manteniendo trazabilidad del intento fallido.

Los fallos operativos deben analizarse por separado de la estabilidad semántica.

---

## 15. Archivos de salida propuestos

Directorio:

```text
Data_IA/data/evaluation/calibration_v1/stability_v1/
```

Archivos:

```text
stability_runs_v1.csv
stability_summary_v1.csv
stability_qualitative_review_v1.csv
STABILITY_FINDINGS_V1.md
run_manifest.json
```

### `stability_runs_v1.csv`

Una fila por corrida.

### `stability_summary_v1.csv`

Una fila por caso con métricas agregadas.

### `stability_qualitative_review_v1.csv`

Revisión humana de:

- observations;
- recommendations;
- unsupported_information;
- consistencia de causa raíz.

### `STABILITY_FINDINGS_V1.md`

Conclusiones y limitaciones.

### `run_manifest.json`

Trazabilidad de:

- commit;
- modelo;
- prompt;
- proveedor;
- fecha;
- número de corridas;
- casos incluidos.

---

## 16. Estructura propuesta de stability_runs_v1.csv

```text
calibration_id
run_id
variant
format
target_dimension
semantic_status
semantic_relevance
semantic_coherence
semantic_didactic_adaptation
semantic_content_support
unsupported_information_count
unsupported_detected
observations_count
recommendations_count
model
prompt_version
latency_ms
error_code
```

---

## 17. Estructura propuesta de stability_summary_v1.csv

```text
calibration_id
runs_successful
relevance_min
relevance_max
relevance_mean
relevance_std
relevance_range
coherence_min
coherence_max
coherence_mean
coherence_std
coherence_range
didactic_min
didactic_max
didactic_mean
didactic_std
didactic_range
content_support_min
content_support_max
content_support_mean
content_support_std
content_support_range
unsupported_consistent
target_dimension_all_runs_in_range
stability_status
```

---

## 18. Clasificación final por caso

Cada caso podrá clasificarse como:

### `stable`

Cuando:

- las 3 corridas son exitosas;
- la dimensión objetivo permanece dentro del rango humano;
- ningún score tiene rango > 0.5;
- `unsupported_information` es consistente;
- observations y recommendations son semánticamente consistentes.

### `review`

Cuando:

- existe variación moderada;
- alguna señal cualitativa cambia;
- hay una diferencia que no invalida el comportamiento general.

### `unstable`

Cuando:

- algún score tiene rango > 1.0;
- la dimensión objetivo sale del rango humano;
- cambia la presencia de unsupported information entre corridas;
- cambia materialmente la causa raíz;
- las recomendaciones se contradicen.

---

## 19. Criterio global candidato para Stability v1

La versión del Semantic Evaluator podrá considerarse suficientemente estable para avanzar a la siguiente etapa cuando:

- todos los casos tengan 3 corridas exitosas;
- ninguna dimensión objetivo salga del rango humano;
- no existan casos clasificados como `unstable`;
- `CAL-V1-011` y `CAL-V1-012` mantengan el comportamiento esperado después del ajuste de prompt;
- los casos clean no generen falsos positivos de unsupported information;
- observations y recommendations sean consistentes y accionables.

Este criterio sigue siendo exploratorio.

---

## 20. Dependencias

Antes de ejecutar:

1. El PR de ajuste de prompt debe estar listo para probarse.
2. Debe identificarse el commit exacto utilizado.
3. Debe mantenerse el mismo modelo durante todas las corridas comparables.
4. Debe existir suficiente cuota para completar las 18 evaluaciones.

---

## 21. Qué no valida este protocolo

Stability v1 no valida por sí sola:

- precisión global del evaluador;
- reglas productivas definitivas;
- Decision Layer completa;
- comportamiento del Backend;
- comportamiento de Agents;
- flujo E2E;
- calidad de la corrección automática.

Solo evalúa consistencia del Semantic Evaluator bajo condiciones controladas.

---

## 22. Próximos pasos después de Stability v1

1. Documentar hallazgos.
2. Ajustar prompt si existe inestabilidad relevante.
3. Repetir únicamente casos problemáticos.
4. Diseñar casos de conflicto heurístico-semántico.
5. Diseñar casos humanos para `rejected`.
6. Validar corrección → reevaluación.
7. Actualizar `DECISION_LAYER_CALIBRATION_V1.md` con evidencia nueva.
