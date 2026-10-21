# Calibration Summary V1 — Heurístico vs Semántico

## 1. Objetivo

Esta calibración compara el comportamiento del evaluador heurístico y del
Semantic Evaluator de Data/IA ante perturbaciones controladas de contenido.

El objetivo no es definir todavía pesos ni un `final_score`, sino observar:

- qué tipos de problemas detecta cada evaluador;
- en qué dimensiones existen divergencias;
- qué señales podrían utilizarse posteriormente en una Decision Layer;
- qué limitaciones deben considerarse antes de automatizar un verdict combinado.

---

## 2. Alcance analizado

El manifest completo de `calibration_v1` contiene 20 casos.

Este análisis se concentra en los 15 casos perturbados:

- `low_relevance`: 3 casos;
- `low_coherence`: 4 casos;
- `poor_didactic_adaptation`: 4 casos;
- `unsupported_claim`: 4 casos.

Los casos `clean_reference` pertenecen al baseline y no forman parte de
esta comparación de detección de perturbaciones.

---

## 3. Modelos utilizados

La corrida principal del evaluador semántico utilizó:

`gemini-3.8-flash`

Resultados válidos obtenidos con este modelo:

14 de 15 casos.

El caso:

`CAL-V1-020`

no pudo completarse con Gemini 3.8 Flash porque se agotó la cuota disponible
del proveedor:

`HTTP 429 RESOURCE_EXHAUSTED`

Para completar el análisis exploratorio, dicho caso se evaluó de forma
auxiliar con:

`gemini-3.6-flash`

Por lo tanto, el dataset consolidado contiene:

- 14 casos con `gemini-3.8-flash`;
- 1 caso con `gemini-3.6-flash`.

Esta diferencia debe conservarse explícitamente para trazabilidad.

---

## 4. Criterio exploratorio de detección

Para las dimensiones objetivo:

- relevance;
- coherence;
- didactic_adaptation;

se consideró detección cuando:

`score objetivo <= 3.0`

Para `unsupported_claim`, se consideró detección cuando existía alguna de
estas señales:

- `content_support <= 3.0`;
- información marcada como no respaldada.

Este criterio se utiliza únicamente para análisis de calibración y no
representa todavía una regla productiva de verdict.

---

## 5. Resultados por dimensión

### Relevance

Casos evaluados: 3

- Heurístico: 0/3 detectados.
- Semántico: 3/3 detectados.

En los tres casos el evaluador heurístico mantuvo:

`relevance = 5`

mientras que el evaluador semántico produjo valores entre:

`1.5 y 2.0`

---

### Coherence

Casos evaluados: 4

- Heurístico: 0/4 detectados.
- Semántico: 4/4 detectados.

El heurístico mantuvo:

`coherence = 5`

en todos los casos.

El semántico produjo valores entre:

`1.5 y 2.5`

El caso `CAL-V1-020` mostró además que el evaluador semántico puede
diferenciar una secuencia narrativa incoherente de un problema factual:

- coherence: 1.5;
- content_support: 5.0.

---

### Didactic Adaptation

Casos evaluados: 4

- Heurístico: 0/4 detectados.
- Semántico: 4/4 detectados.

El heurístico mantuvo:

`didactic_adaptation = 5`

en todos los casos.

El semántico produjo valores entre:

`1.5 y 2.0`

y generó observaciones relacionadas con vocabulario, complejidad y
progresión pedagógica.

---

### Unsupported Claim / Content Support

Casos evaluados: 4

- Heurístico: 4/4 detectados.
- Semántico: 4/4 detectados.

En esta dimensión ambos mecanismos mostraron capacidad de detección.

El Semantic Evaluator además identificó explícitamente:

`unsupported_information`

en los cuatro casos.

---

## 6. Resumen de detección

| Tipo de perturbación | Casos | Heurístico | Semántico |
|---|---:|---:|---:|
| Low relevance | 3 | 0/3 | 3/3 |
| Low coherence | 4 | 0/4 | 4/4 |
| Poor didactic adaptation | 4 | 0/4 | 4/4 |
| Unsupported claim | 4 | 4/4 | 4/4 |
| **Total** | **15** | **4/15** | **15/15** |

Estos resultados corresponden exclusivamente al dataset controlado
`calibration_v1` y no deben interpretarse todavía como métricas generales
de producción.

---

## 7. Hallazgo principal

La calibración muestra una especialización distinta entre ambos mecanismos.

El evaluador heurístico responde adecuadamente ante señales determinísticas
de respaldo factual presentes en esta muestra.

Sin embargo, no reaccionó a las perturbaciones controladas de:

- relevancia;
- coherencia;
- adaptación didáctica.

El evaluador semántico detectó las perturbaciones objetivo en los 15 casos
analizados.

Esto sugiere que el Semantic Evaluator aporta información complementaria
material y no debería considerarse únicamente metadata descriptiva.

---

## 8. Implicación sobre el verdict actual

Actualmente Evaluation V2 mantiene el `verdict` derivado exclusivamente
del evaluador heurístico.

El Semantic Evaluator permanece como una señal independiente.

Los resultados de esta calibración muestran casos en los que el heurístico
podría conservar scores altos en la dimensión objetivo mientras el
evaluador semántico identifica un problema claro.

Por tanto, un `verdict` exclusivamente heurístico puede no representar
todos los problemas de calidad observables por el sistema.

---

## 9. Candidate Decision Layer

No se recomienda introducir todavía un promedio simple entre scores.

Una primera estrategia candidata para experimentación posterior es:

1. Mantener las señales heurística y semántica separadas.
2. Utilizar el heurístico como señal determinística de respaldo factual.
3. Permitir que señales semánticas críticas intervengan en el proceso de
   decisión.
4. Tratar `unsupported_information` como una señal explícita de riesgo.
5. Validar las reglas contra más casos antes de utilizarlas para producir
   automáticamente el verdict final.

Ejemplo conceptual, aún NO implementado:

- score semántico crítico `<= 2` → candidato a `requires_revision`;
- información factual no respaldada → candidato a revisión;
- señales satisfactorias en ambos evaluadores → candidato a `approved`;
- divergencias fuertes → mantener revisión o solicitar nueva evaluación.

Estas reglas son hipótesis derivadas de la calibración y no forman todavía
parte del contrato productivo.

---

## 10. Limitaciones

Esta primera calibración tiene varias limitaciones:

- muestra controlada pequeña;
- perturbaciones construidas intencionalmente;
- 14 casos evaluados con Gemini 3.8 Flash y 1 con Gemini 3.6 Flash;
- aún no existe validación humana independiente de todos los scores;
- no se evaluaron todavía tasas de falsos positivos sobre una muestra amplia;
- no se ha calibrado un umbral productivo definitivo;
- no se han definido pesos entre señales.

Por estas razones no se propone todavía modificar automáticamente el
`verdict` de producción.

---

## 11. Archivos de evidencia

Resultados heurísticos:

- `results/heuristic_perturbations_batch1.csv`
- `results/heuristic_unsupported_claim_batch1.csv`

Resultados semánticos:

- `results/semantic_perturbations_gemini_3_8_flash_run1.csv`
- `results/semantic_perturbations_gemini_3_8_flash_retry_failed.csv`
- `results/semantic_CAL-V1-020_gemini_3_6_flash.csv`
- `results/semantic_perturbations_calibration_v1_consolidated.csv`

Comparaciones:

- `results/heuristic_vs_semantic_target_dimension_v1.csv`
- `results/heuristic_vs_semantic_unsupported_claim_v1.csv`

---

## 12. Próximo paso recomendado

El siguiente experimento debe incorporar:

- casos limpios adicionales;
- más ejemplos por dimensión;
- revisión humana de referencia;
- análisis de falsos positivos y falsos negativos;
- estabilidad entre múltiples corridas del modelo;
- comparación de divergencias heurístico-semántico.

Con evidencia adicional podrá definirse una Decision Layer versionada y
reproducible para determinar cuándo una señal semántica debe modificar o
bloquear el verdict heurístico.

Hasta entonces:

`heuristic_scores`

y:

`semantic_evaluation`

deben continuar expuestos como señales separadas.
