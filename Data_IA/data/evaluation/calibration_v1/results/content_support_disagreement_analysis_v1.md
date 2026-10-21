# Content Support Disagreement Analysis v1

## Objetivo

Analizar los desacuerdos detectados entre el evaluador heurístico y el evaluador semántico en la dimensión `content_support`, con el fin de identificar posibles limitaciones sistemáticas del mecanismo heurístico actual y generar evidencia para futuras decisiones de calibración.

Este análisis no modifica todavía la lógica del evaluador ni el cálculo del `verdict`.

---

## Contexto

Actualmente, Evaluation V2 mantiene separadas las señales del evaluador heurístico y del evaluador semántico.

El evaluador heurístico sigue siendo el responsable del `verdict`, mientras que el evaluador semántico aporta una señal adicional mediante:

- scores semánticos;
- observaciones;
- recomendaciones;
- detección de información no respaldada.

Durante las pruebas de calibración y la validación en OCI se identificaron casos donde ambos evaluadores presentan diferencias importantes específicamente en `content_support`.

Para estudiar este comportamiento se analizaron tres casos representativos:

- `CAL-OCI-001`
- `CAL-V1-005`
- `CAL-V1-013`

---

## Regla heurística actual de `content_support`

El evaluador heurístico actual compara términos significativos extraídos del contenido generado con términos presentes en `chunks_used`.

De forma simplificada, el flujo es:

1. Extraer el contenido factual del formato generado.
2. Normalizar y filtrar palabras significativas.
3. Extraer términos de `chunks_used`.
4. Identificar palabras generadas que no aparecen literalmente en los chunks.
5. Calcular:

```text
ratio_alucinacion =
cantidad_terminos_no_respaldados /
cantidad_total_terminos_generados
```

6. Asignar `content_support` según los umbrales actuales.

Los umbrales observados son:

```text
ratio <= 0.15
→ content_support = 5

ratio <= 0.30
→ content_support = 4

0.30 < ratio < 0.40
→ content_support = 3

ratio >= 0.40
→ content_support = 1
→ informacion_no_respaldada = True
```

Cuando `informacion_no_respaldada = True`, la rúbrica heurística produce `rejected`.

---

# Caso 1 — CAL-OCI-001

## Descripción

Caso real ejecutado en OCI mediante `/evaluate/v2`.

Formato:

```text
tldr
```

Resultado heurístico:

```text
relevance = 5
coherence = 5
didactic_adaptation = 5
content_support = 1
verdict = rejected
```

Resultado semántico:

```text
relevance = 5
coherence = 5
didactic_adaptation = 5
content_support = 5
unsupported_information = 0
status = success
```

El resultado semántico fue repetido tres veces con el mismo payload.

Las tres ejecuciones produjeron exactamente:

```text
5 / 5 / 5 / 5
```

y:

```text
unsupported_information = 0
```

Por lo tanto, para este caso el resultado semántico fue estable en `3/3` ejecuciones.

---

## Diagnóstico heurístico

Términos generados evaluados:

```text
13
```

Términos considerados no respaldados:

```text
6
```

Términos detectados:

```text
sistemas
distribuidos
emplea
facilita
construccion
apis
```

Ratio calculado:

```text
6 / 13 = 0.4615
```

Umbral de rechazo:

```text
0.4
```

Por lo tanto:

```text
0.4615 > 0.4
```

y el heurístico asigna:

```text
content_support = 1
informacion_no_respaldada = True
verdict = rejected
```

---

## Observación

El contenido generado incluye expresiones que son semánticamente compatibles con el chunk, pero que no coinciden literalmente.

Ejemplo:

```text
Contenido generado:
"Emplea metodos HTTP"

Chunk:
"utiliza recursos y metodos HTTP"
```

Las palabras:

```text
emplea
utiliza
```

son semánticamente cercanas, pero el heurístico las trata como términos diferentes.

Esto contribuye al aumento artificial del `ratio_alucinacion`.

---

# Caso 2 — CAL-V1-005

## Descripción

Caso de calibración existente.

Formato:

```text
flashcards
```

Resultado registrado en:

```text
calibration_comparison_batch1.csv
```

Heurístico:

```text
content_support = 1
heuristic_unsupported_information = True
```

Semántico:

```text
content_support = 5
unsupported_information = 0
```

Clasificación existente:

```text
strong_disagreement
```

En el ground truth humano:

```text
expected_verdict = approved
```

y la evaluación semántica se encuentra dentro del rango esperado.

---

## Diagnóstico heurístico

Términos generados evaluados:

```text
14
```

Términos considerados no respaldados:

```text
7
```

Términos detectados:

```text
clase
importa
aplicacion
clase
importada
paquete
mediante
```

Ratio calculado:

```text
7 / 14 = 0.5
```

Umbral de rechazo:

```text
0.4
```

Por lo tanto:

```text
0.5 > 0.4
```

y el heurístico termina asignando:

```text
content_support = 1
informacion_no_respaldada = True
```

---

## Observación

El contenido evaluado era:

```text
¿Qué clase se importa para crear una aplicación FastAPI?
La clase FastAPI, importada desde el paquete fastapi mediante:
from fastapi import FastAPI.
```

El chunk sí contiene términos centrales como:

```text
fastapi
from
import
```

Sin embargo, palabras explicativas como:

```text
clase
aplicacion
importada
paquete
mediante
```

son contabilizadas como no respaldadas.

Estas palabras no necesariamente representan afirmaciones factuales nuevas o alucinadas, sino formulaciones pedagógicas y lingüísticas alrededor de una afirmación respaldada.

---

# Caso 3 — CAL-V1-013

## Descripción

Caso de calibración existente.

Formato:

```text
video_script
```

Resultado registrado en:

```text
calibration_comparison_batch1.csv
```

Heurístico:

```text
content_support = 3
```

Semántico:

```text
content_support = 5
```

Clasificación existente:

```text
moderate_disagreement
```

---

## Diagnóstico heurístico

Términos generados evaluados:

```text
18
```

Términos considerados no respaldados:

```text
6
```

Términos detectados:

```text
visitamos
permiten
distintas
aparezcan
actuen
determinada
```

Ratio calculado:

```text
6 / 18 = 0.3333
```

Como:

```text
0.3333 > 0.30
```

pero:

```text
0.3333 < 0.40
```

el heurístico asigna:

```text
content_support = 3
```

---

## Observación

En este caso aparecen varias equivalencias léxicas o semánticas claras:

```text
visita         ↔ visitamos
pueden         ↔ permiten
diferentes     ↔ distintas
aparezca       ↔ aparezcan
actue          ↔ actuen
cierta manera  ↔ manera determinada
```

El significado global se mantiene, pero la comparación heurística penaliza las diferencias de forma superficial.

---

# Comparación de casos

| Caso | Formato | Ratio léxico | Heurístico `content_support` | Semántico `content_support` | Tipo de desacuerdo |
|---|---|---:|---:|---:|---|
| CAL-OCI-001 | tldr | 0.4615 | 1 | 5 | strong disagreement |
| CAL-V1-005 | flashcards | 0.5000 | 1 | 5 | strong disagreement |
| CAL-V1-013 | video_script | 0.3333 | 3 | 5 | moderate disagreement |

---

# Patrón observado

Los tres casos muestran un patrón común:

```text
contenido semánticamente respaldado
↓
uso de paráfrasis, flexiones o vocabulario equivalente
↓
baja coincidencia léxica literal
↓
aumento del ratio_alucinacion
↓
penalización de content_support
```

El evaluador heurístico actual presenta una limitación sistemática al evaluar respaldo factual mediante coincidencia léxica de términos.

Esta limitación afecta especialmente casos donde existen:

- paráfrasis;
- sinónimos;
- flexiones verbales;
- cambios morfológicos;
- reformulaciones pedagógicas;
- expresiones equivalentes;
- palabras funcionales añadidas para mejorar claridad.

---

# Hipótesis principal

El evaluador heurístico de `content_support` puede generar falsos positivos cuando el contenido generado expresa correctamente información respaldada por los chunks, pero utiliza una formulación lingüística distinta.

La principal limitación observada es:

```text
coincidencia léxica != equivalencia semántica
```

El mecanismo actual detecta diferencias de palabras, pero no determina si esas diferencias introducen realmente información nueva o falsa.

---

# Comparación con el evaluador semántico

En los casos analizados, el evaluador semántico muestra mayor capacidad para reconocer equivalencia de significado.

Ejemplos:

```text
emplea ↔ utiliza
distintas ↔ diferentes
aparezcan ↔ aparezca
actuen ↔ actue
```

Además, en `CAL-OCI-001`, el resultado semántico fue completamente estable en tres ejecuciones consecutivas.

Esto sugiere que la señal semántica puede ser útil para detectar falsos positivos producidos por el heurístico.

Sin embargo, este análisis no implica que el evaluador semántico deba reemplazar directamente al heurístico.

---

# Riesgo de modificar el heurístico sin calibración

Reducir directamente el umbral de rechazo o relajar las reglas podría disminuir falsos positivos, pero también podría aumentar falsos negativos.

Por ejemplo:

```text
contenido realmente no respaldado
↓
ratio léxico moderado
↓
regla demasiado permisiva
↓
contenido incorrecto podría aprobarse
```

Por lo tanto, no se recomienda modificar los umbrales únicamente a partir de estos tres casos.

---

# Conclusión

El análisis de `CAL-OCI-001`, `CAL-V1-005` y `CAL-V1-013` muestra evidencia consistente de que el evaluador heurístico de `content_support` puede penalizar contenido correctamente respaldado cuando existe variación lingüística respecto de los chunks originales.

La causa principal identificada es el uso de coincidencia léxica como aproximación al respaldo factual.

Los casos analizados muestran:

```text
CAL-OCI-001
heurístico = 1
semántico = 5

CAL-V1-005
heurístico = 1
semántico = 5

CAL-V1-013
heurístico = 3
semántico = 5
```

En los tres casos se identificaron paráfrasis o equivalencias lingüísticas como parte importante de la diferencia.

Por lo tanto, el desacuerdo observado no parece ser un caso aislado, sino una limitación reproducible del mecanismo heurístico actual.

---

# Recomendación

No modificar todavía el `verdict` ni reemplazar el evaluador heurístico.

Los siguientes pasos recomendados son:

1. Ampliar el conjunto de casos con desacuerdo en `content_support`.
2. Comparar resultados contra ground truth humano.
3. Identificar falsos positivos y falsos negativos del heurístico.
4. Evaluar mejoras de normalización léxica y equivalencia semántica.
5. Medir el impacto de cualquier modificación sobre todo el dataset.
6. Mantener heurístico y semántico como señales separadas durante la calibración.
7. Utilizar estos resultados para definir posteriormente una Decision Layer calibrada.

---

# Estado del análisis

```text
status = confirmed_pattern
dimension = content_support
cases_analyzed = 3
main_issue = lexical_matching_false_positives
heuristic_change = pending_calibration
decision_layer = not_implemented
```

# Caso 4 — CAL-V1-014

## Descripción

Caso diseñado con una afirmación factual no respaldada.

Formato:

```text
quiz
```

El contenido incluye la afirmación:

```text
"Además, usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página."
```

Esta afirmación no aparece respaldada en `chunks_used`.

El evaluador semántico detectó correctamente información no respaldada:

```text
semantic_content_support = 3
semantic_unsupported_information_count = 1
```

El evaluador heurístico produjo:

```text
heuristic_content_support = 3
heuristic_unsupported_information = False
```

---

## Diagnóstico heurístico

Términos generados evaluados:

```text
31
```

Términos considerados respaldados:

```text
20
```

Términos considerados no respaldados:

```text
11
```

Entre los términos no respaldados aparecen:

```text
mejora
automaticamente
posicionamiento
```

Estos términos corresponden directamente a la afirmación problemática relacionada con SEO.

El ratio calculado fue:

```text
11 / 31 = 0.3548
```

Como:

```text
0.3548 < 0.4
```

no se activa el umbral de rechazo.

Por lo tanto, el heurístico devuelve:

```text
content_support = 3
informacion_no_respaldada = False
```

---

## Problema identificado

Este caso muestra un comportamiento distinto a los falsos positivos observados anteriormente.

La afirmación no respaldada sí genera términos que el heurístico identifica como ausentes de los chunks, pero dichos términos quedan diluidos dentro de una cantidad mayor de contenido correctamente respaldado.

El flujo observado es:

```text
contenido mayormente respaldado
+
una afirmación factual no respaldada
↓
los términos problemáticos representan una fracción limitada del total
↓
ratio_alucinacion < 0.4
↓
informacion_no_respaldada = False
```

Esto representa un posible falso negativo del mecanismo heurístico.

---

## Implicación

El análisis indica que modificar únicamente el umbral de `ratio_alucinacion` no resolvería completamente el problema.

Un umbral más bajo podría detectar mejor casos como `CAL-V1-014`, pero al mismo tiempo podría aumentar los falsos positivos observados en:

- `CAL-OCI-001`
- `CAL-V1-005`
- `CAL-V1-013`

Por lo tanto, la limitación parece estar relacionada con el método global de comparación y no únicamente con los valores de los umbrales.

El evaluador actual calcula respaldo factual a nivel agregado de palabras, pero no identifica afirmaciones o unidades semánticas individuales.

Una posible línea de mejora será evaluar respaldo por afirmación, oración o unidad semántica antes de agregar el resultado global.