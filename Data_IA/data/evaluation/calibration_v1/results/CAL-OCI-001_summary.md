# CAL-OCI-001 — Resumen de estabilidad y divergencia

## Objetivo

Validar la estabilidad del evaluador semántico en OCI y analizar la divergencia entre la evaluación heurística y semántica para la dimensión `content_support`.

## Resultado observado

El evaluador heurístico produjo:

- relevance: 5
- coherence: 5
- didactic_adaptation: 5
- content_support: 1
- verdict: `rejected`

El evaluador semántico con Gemini produjo, en 3 ejecuciones consecutivas:

- relevance: 5
- coherence: 5
- didactic_adaptation: 5
- content_support: 5
- unsupported_information: 0
- status: `success`

## Estabilidad semántica

Las tres ejecuciones devolvieron exactamente los mismos scores.

- Runs consistentes: 3/3
- Rango de variación en `content_support`: 0
- Unsupported information detectada: 0/3
- Modelo: `gemini-3.5-flash-lite`
- Prompt: `semantic-evaluator-v0.1`

Latencias registradas:

- Run 1: 5841 ms
- Run 2: 6079 ms
- Run 3: 2790 ms
- Latencia promedio aproximada: 4903 ms

## Divergencia principal

Existe una divergencia fuerte en `content_support`:

- Heurístico: 1
- Semántico: 5

Esto provoca que el heurístico produzca `verdict = rejected`, mientras que el evaluador semántico no detecta problemas de respaldo factual.

## Interpretación preliminar

El caso debe considerarse un caso de desacuerdo heurístico-semántico y utilizarse para calibración.

No se modifica todavía la lógica del veredicto.

El siguiente paso es diagnosticar por qué el evaluador heurístico penaliza este caso y determinar si se trata de una limitación de coincidencia léxica frente a equivalencia semántica.

## Diagnóstico del heurístico

Se reprodujo manualmente la lógica de `content_support` del evaluador heurístico.

Resultados:

- términos generados evaluados: 13
- términos considerados no respaldados: 6
- ratio de alucinación: `0.4615`
- umbral de rechazo: `0.4`

Términos considerados no respaldados:

- `sistemas`
- `distribuidos`
- `emplea`
- `facilita`
- `construccion`
- `apis`

Como `0.4615 > 0.4`, el heurístico establece:

- `informacion_no_respaldada = True`
- `content_support = 1`
- `verdict = rejected`

Este comportamiento muestra una limitación del mecanismo actual de respaldo factual: utiliza coincidencia léxica de términos significativos y puede penalizar paráfrasis o equivalencias semánticas.

Un ejemplo directo es:

- contenido generado: `emplea metodos HTTP`
- chunk: `utiliza recursos y metodos HTTP`

Aunque ambas expresiones son semánticamente compatibles, el término `emplea` no aparece literalmente en el chunk y es contabilizado como no respaldado.

El evaluador semántico, en cambio, otorgó `content_support = 5` en 3/3 ejecuciones consecutivas y no detectó información no respaldada.

Esto confirma que `CAL-OCI-001` es un caso útil para estudiar la calibración entre señales heurísticas y semánticas.

## Comparación con caso previo de calibración

El patrón observado en `CAL-OCI-001` también aparece en `CAL-V1-005`.

En `CAL-V1-005`:

- términos generados evaluados: 14
- términos considerados no respaldados: 7
- ratio de alucinación: `0.5`
- umbral de rechazo: `0.4`
- heuristic content_support: `1`
- semantic content_support: `5`

Esto refuerza la hipótesis de que el evaluador heurístico de `content_support` puede generar falsos positivos cuando el contenido utiliza paráfrasis, palabras funcionales explicativas o expresiones semánticamente compatibles que no aparecen literalmente en `chunks_used`.

El patrón ya se observa en al menos dos casos independientes.

## Estado

`strong_heuristic_semantic_disagreement`