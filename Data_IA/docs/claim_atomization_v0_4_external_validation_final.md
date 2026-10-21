# Claim Atomization v0.4 — External Validation Final Report

**Proyecto:** NuevaMente — Data/IA  
**Componente:** Claim Atomization v1  
**Candidato evaluado:** `claim-atomizer-v0.4`  
**Modelo:** `gemini-3.5-flash-lite`  
**Estado final:** `STOP_V0_4_FOR_PRODUCTION_INTEGRATION`  
**Integración a producción:** No

---

## 1. Objetivo

El objetivo de esta fase fue determinar si `claim-atomizer-v0.4`, desarrollado inicialmente sobre el corpus interno de Claim Atomization v1, podía generalizar de manera suficientemente consistente a un corpus externo de documentación técnica.

La evaluación se diseñó para separar tres preguntas:

1. **Test A — External Structural Validation**  
   ¿La atomización mantiene calidad estructural al salir del corpus de desarrollo?

2. **Test B — Stability & Provider Reliability**  
   ¿El mismo input produce estructuras consistentes entre repeticiones y con qué confiabilidad responde el proveedor?

3. **Test C — Content-Support Impact A/B**  
   ¿La atomización mejora realmente la evaluación de `content_support` frente al análisis del claim completo?

El Test C quedó condicionado a que la calidad estructural del Test A fuera suficiente.

---

## 2. Guardrails metodológicos

Durante la validación externa se mantuvieron las siguientes restricciones:

- `claim-atomizer-v0.4` permaneció congelado.
- No se realizaron ajustes de prompt durante la evaluación externa.
- No se modificó el Ground Truth después de ejecutar las predicciones.
- El Ground Truth fue congelado antes de generar las predicciones externas.
- Las predicciones fueron congeladas antes de compararlas con el Ground Truth.
- No se utilizó conocimiento del resultado del modelo para modificar retrospectivamente el benchmark.
- No se integró Claim Atomization al flujo de producción.
- No se alteró el verdict final del evaluador de Data/IA.
- El experimento permaneció separado del Semantic Evaluator productivo.
- El análisis estructural no utilizó igualdad literal del texto de los átomos.
- El campo `format` heredado del dataset externo no se utilizó como formato educativo debido a su inconsistencia.
- Durante las llamadas al atomizer se utilizó el metadato constante:

```text
external_documentation
```

El benchmark externo fue construido deliberadamente de forma balanceada y **no representa prevalencia natural de producción**.

---

## 3. Dataset externo

### 3.1 Fuentes

Se utilizaron 15 documentos provenientes de documentación oficial, distribuidos en cinco dominios:

- AI
- Backend
- Cloud / DevOps
- Data Science
- Frontend

Las fuentes provinieron de documentación oficial de:

- Google AI
- FastAPI
- Kubernetes
- pandas
- scikit-learn
- MDN

No se reutilizaron claims del corpus histórico de 59 casos.

La auditoría de overlap obtuvo:

```text
Historical cases: 59
External cases: 80
Exact normalized overlap: 0
```

La auditoría verifica overlap textual normalizado exacto; no constituye una prueba formal de independencia semántica o ausencia de near-duplicates.

### 3.2 Benchmark final

El benchmark externo congelado contiene:

```text
80 casos
```

Distribución intencional:

| Bucket | Casos |
|---|---:|
| atomic | 20 |
| compound | 20 |
| relational | 20 |
| non_propositional | 20 |
| **Total** | **80** |

Esta estratificación fue deliberada para ejercer las fronteras estructurales del atomizer.

No debe interpretarse como distribución real de tráfico productivo.

---

## 4. Ground Truth externo

El Ground Truth fue construido antes de ejecutar `claim-atomizer-v0.4`.

Totales:

```text
80 casos
60 valid_claim
20 non_propositional
88 átomos esperados
```

Distribución de átomos por bucket:

| Bucket | Átomos GT |
|---|---:|
| atomic | 20 |
| compound | 48 |
| relational | 20 |
| non_propositional | 0 |
| **Total** | **88** |

Tipos de átomos:

| Tipo | Cantidad |
|---|---:|
| factual_proposition | 57 |
| conditional_relation | 8 |
| negation_or_absence | 7 |
| causal_relation | 7 |
| comparative_relation | 5 |
| temporal_relation | 4 |
| scope_or_quantifier | 0 |

### Limitación

`scope_or_quantifier` no quedó representado en el benchmark final.

No se agregaron casos post hoc después de observar las predicciones.

---

## 5. Ejecución inicial de v0.4

La primera ejecución procesó los 80 casos externos.

Resultado del intento inicial:

```text
Successful: 34/80
Failed:     46/80
Completion: 42.50%
```

Los 46 fallos fueron reportados como errores de petición al proveedor.

No se atribuyó una causa específica como rate limit, quota o red porque el error disponible no permitía demostrarla.

Se ejecutó posteriormente un retry dirigido exclusivamente sobre los 46 casos fallidos.

Resultado:

```text
Retry successful: 46/46
Retry failed:      0
Final completed:   80/80
```

Por lo tanto, las métricas estructurales del Test A se calcularon con cobertura final completa.

---

## 6. Test A — External Structural Validation

### 6.1 Detección de `non_propositional`

Clase positiva:

```text
non_propositional
```

Matriz de confusión:

| Métrica | Resultado |
|---|---:|
| TP | 15 |
| FP | 1 |
| FN | 5 |
| TN | 59 |

Métricas:

| Métrica | Resultado |
|---|---:|
| Precision | 0.9375 |
| Recall | 0.7500 |
| Specificity | 0.9833 |
| Accuracy | 0.9250 |
| Coverage | 1.0000 |

Interpretación:

- La precisión fue alta.
- La cobertura fue completa.
- Sin embargo, el modelo no detectó 5 de los 20 casos humanos clasificados como `non_propositional`.
- El recall de `0.7500` quedó por debajo del criterio interno de `0.8500`.

### 6.2 Calidad estructural

Claims humanos válidos:

```text
60
```

Claims estructuralmente evaluables:

```text
59
```

Cobertura estructural:

```text
0.9833
```

Átomos:

```text
Esperados por GT: 88
Predichos:        109
Delta:            +21
Inflation rate:   +0.2386
```

Métricas:

| Métrica | Resultado |
|---|---:|
| Class accuracy | 0.6000 |
| Count accuracy | 0.5167 |
| Type-sequence accuracy | 0.4167 |
| Exact-structure accuracy | 0.3833 |
| Over-atomized cases | 22 |
| Under-atomized cases | 7 |

La estructura exacta se definió como coincidencia conjunta de:

```text
class
+ atom count
+ atom-type sequence
```

No se exigió igualdad textual literal entre átomos.

---

## 7. Test A por bucket

### Atomic

```text
Cases:            20
Class accuracy:   0.5500
Count accuracy:   0.5500
Type accuracy:    0.5500
Exact structure:  0.5500
Over / Under:     8 / 1
```

El patrón dominante fue sobre-atomización.

### Compound

```text
Cases:            20
Class accuracy:   0.7500
Count accuracy:   0.6500
Type accuracy:    0.5000
Exact structure:  0.4500
Over / Under:     1 / 6
```

Aquí apareció el patrón contrario: varios claims fueron sub-atomizados.

### Relational

```text
Cases:            20
Class accuracy:   0.5000
Count accuracy:   0.3500
Type accuracy:    0.2000
Exact structure:  0.1500
Over / Under:     13 / 0
```

Este fue el bloque más débil del experimento.

La sobre-atomización relacional fue uno de los patrones más claros del benchmark externo.

---

## 8. Criterios internos de Test A

Los criterios fueron definidos antes de interpretar el resultado:

| Métrica | Umbral | Observado | Resultado |
|---|---:|---:|---|
| Exact structure | >= 0.90 | 0.3833 | FAIL |
| Count accuracy | >= 0.95 | 0.5167 | FAIL |
| Non-propositional recall | >= 0.85 | 0.7500 | FAIL |
| Non-propositional precision | >= 0.90 | 0.9375 | PASS |
| Detection coverage | >= 0.95 | 1.0000 | PASS |

Resultado:

```text
Thresholds passed: 2/5
TEST A: INVESTIGATE
```

---

## 9. Failure Analysis

Se analizaron offline los errores del Test A.

No se realizaron nuevas llamadas a Gemini y no se modificaron:

- candidato;
- Ground Truth;
- predicciones.

### 9.1 Detection failures

```text
Total: 6
FP:    1
FN:    5
Provider failed: 0
```

### 9.2 Structural failures

Claims estructuralmente incorrectos:

```text
37
```

Distribución:

| Patrón | Casos |
|---|---:|
| over_atomized | 22 |
| under_atomized | 7 |
| count_equal_structure_wrong | 8 |

### 9.3 Fallos por bucket humano

```text
atomic:      9
compound:   11
relational: 17
```

El mayor número de fallos se concentró en `relational`.

### 9.4 Fallos relacionales por subtipo

```text
causal_relation:       3
comparative_relation:  2
conditional_relation:  7
negation_or_absence:   1
temporal_relation:     4
```

No hubo casos de `scope_or_quantifier` en el benchmark.

### 9.5 Patrones dominantes

```text
Relational over-atomization: 13/20
Compound under-atomization:   6/20
Atomic over-atomization:      8/20
```

El problema no puede describirse únicamente como “el modelo divide demasiado”.

El comportamiento depende de la clase estructural:

- `atomic` tiende a dividirse de más;
- `compound` presenta varios casos de división insuficiente;
- `relational` presenta una fuerte tendencia a sobre-atomización y errores de clasificación/tipado.

### 9.6 Confusión de clases

Principales confusiones observadas:

```text
relational -> relational:       7 fallos estructurales
relational -> compound:         7
atomic -> compound:             6
compound -> compound:           6 fallos estructurales
compound -> relational:         3
relational -> atomic:           3
atomic -> relational:           2
compound -> atomic:             2
atomic -> non_propositional:    1
```

Una predicción puede conservar la clase correcta y aun así ser un fallo estructural debido a:

- atom count incorrecto;
- atom types incorrectos;
- secuencia estructural incorrecta.

### 9.7 Fallos por dominio

```text
AI:            7
Backend:       5
Cloud/DevOps:  6
Data Science:  7
Frontend:     12
```

Los fallos aparecen en todos los dominios.

Por lo tanto, la pérdida de generalización externa no parece limitarse a una sola fuente o dominio.

---

## 10. Test B — Stability & Provider Reliability

Después del Test A se realizó una prueba independiente de repetibilidad.

Diseño:

```text
16 casos
4 atomic
4 compound
4 relational
4 non_propositional

3 repeticiones por caso
48 llamadas
```

La muestra fue seleccionada determinísticamente desde el benchmark externo congelado.

No se realizaron retries durante Test B porque los fallos del proveedor formaban parte de la medición.

La firma de estabilidad incluyó únicamente:

```text
review_status
atomization_class
atom_count
atom_type_sequence
```

El texto literal de los átomos no se utilizó.

---

## 11. Test B — Provider reliability

Resultado:

```text
Successful calls: 47/48
Failed calls:       1
Success rate:       0.9792
```

El único fallo observado correspondió a una respuesta que no pudo validarse contra el schema de Claim Atomization v0.4.

La causa registrada fue una inconsistencia estructural:

```text
compound must contain at least two atoms
```

Esto es diferente de los errores genéricos de petición observados durante la primera corrida del Test A.

---

## 12. Test B — Stability

Resultados:

```text
Cases:                         16
All 3 repetitions successful: 15/16
Fully stable cases:           11/16
Fully stable rate:             0.6875
```

Entre los casos con al menos dos respuestas exitosas:

```text
Stable cases: 11/16
Stability:    0.6875
```

### 12.1 Estabilidad por bucket

| Bucket | Fully stable |
|---|---:|
| atomic | 2/4 |
| compound | 3/4 |
| relational | 3/4 |
| non_propositional | 3/4 |

La inestabilidad apareció en todos los buckets.

### 12.2 Ejemplos de inestabilidad estructural

Se observaron inputs idénticos capaces de producir diferentes estructuras entre repeticiones.

Ejemplo observado:

```text
repetition 1 -> relational / 3 atoms
repetition 2 -> compound / 2 atoms
repetition 3 -> compound / 2 atoms
```

En otro caso se observaron tres clasificaciones diferentes para el mismo input:

```text
atomic
relational
non_propositional
```

Esto demuestra que el problema no es únicamente precisión frente al Ground Truth; también existe variabilidad estructural entre ejecuciones del mismo candidato.

---

## 13. Latencia de Test B

Sobre las llamadas exitosas:

```text
Mean: 1099.83 ms
Min:   679 ms
Max:  3904 ms
```

Estas cifras corresponden únicamente al Test B y no deben extrapolarse como SLA productivo.

---

## 14. Interpretación conjunta

Los resultados externos muestran dos problemas distintos.

### 14.1 Generalización estructural

El principal problema es la calidad estructural externa.

```text
Exact structure accuracy: 0.3833
Count accuracy:           0.5167
Type sequence accuracy:   0.4167
Atom inflation:          +23.86%
```

Estas métricas están muy por debajo de los criterios internos definidos para continuar.

### 14.2 Estabilidad

Incluso cuando el proveedor devuelve una respuesta válida, la estructura no siempre es reproducible.

```text
Fully stable rate: 68.75%
```

Por lo tanto, una respuesta incorrecta o correcta en una sola corrida no necesariamente representa un comportamiento estable del candidato.

### 14.3 Provider reliability

El proveedor presentó comportamientos diferentes en las dos etapas.

#### Test A — primera ejecución

```text
34/80 successful
42.50%
```

#### Test A — retry dirigido

```text
46/46 recovered
Final coverage: 80/80
```

#### Test B

```text
47/48 successful
97.92%
```

No se determinó una causa única para esta diferencia.

Los errores genéricos de request de la primera ejecución no deben atribuirse retroactivamente a quota, rate limiting u otra causa no demostrada.

---

## 15. Test C — Content-Support Impact A/B

Estado:

```text
SKIPPED
```

Razón:

El objetivo del Test C era comparar:

```text
content support sobre claim completo
vs
content support sobre claim atomizado
```

Sin embargo, realizar esta prueba después de observar:

```text
Exact structure accuracy = 0.3833
Count accuracy = 0.5167
```

haría difícil distinguir si una mejora o degradación en `content_support` proviene realmente de la atomización como concepto o de errores estructurales del candidato v0.4.

Por esta razón, Test C se omite deliberadamente.

Esto evita consumir más llamadas y evita generar conclusiones difíciles de interpretar.

---

## 16. Decisión final

Resultado formal:

```text
Test A: INVESTIGATE
Test B: COMPLETED
Test C: SKIPPED

Final decision:
STOP_V0_4_FOR_PRODUCTION_INTEGRATION

Production integration:
NO
```

`claim-atomizer-v0.4` permanece como artefacto experimental útil, pero no demostró suficiente generalización estructural externa ni estabilidad para integrarse al pipeline productivo de Data/IA.

---

## 17. Implicación para NuevaMente

La decisión no modifica la arquitectura productiva actual.

Data/IA mantiene:

- evaluación semántica;
- evaluación heurística;
- contratos existentes;
- separación entre Semantic Evaluator y experimentos de Claim Atomization.

Claim Atomization v0.4:

```text
NO cambia verdict
NO entra al Semantic Evaluator productivo
NO modifica content_support
NO cambia contratos Backend/Data-IA
NO modifica Agents
NO modifica Frontend
```

---

## 18. Trabajo futuro

No se recomienda continuar ajustando `v0.4`.

Una eventual `v0.5` debería tratarse como un **nuevo candidato experimental**.

Las hipótesis para una futura versión pueden derivarse de los patrones observados:

1. reducir sobre-atomización de claims relacionales;
2. mejorar la frontera `atomic ↔ compound ↔ relational`;
3. mejorar la detección de `non_propositional`;
4. reducir variabilidad estructural entre repeticiones;
5. revisar específicamente relaciones condicionales y temporales;
6. definir mejor cuándo una relación debe permanecer como un único átomo relacional;
7. volver a evaluar sobre un benchmark protegido nuevo.

El benchmark externo v1 no debería convertirse directamente en dataset de tuning y evaluación de una futura v0.5.

Si se utiliza para generar hipótesis, una versión futura requerirá un nuevo conjunto protegido para validación final.

---

## 19. Limitaciones

Esta evaluación debe interpretarse considerando:

- el benchmark es pequeño;
- la distribución fue deliberadamente balanceada;
- no representa prevalencia de producción;
- el Ground Truth fue construido mediante revisión humana asistida;
- no se utilizaron múltiples anotadores expertos independientes;
- `scope_or_quantifier` no quedó representado en el benchmark final;
- la auditoría de overlap fue textual normalizada y no una medición exhaustiva de similitud semántica;
- el dominio principal corresponde a documentación técnica oficial;
- el metadato `external_documentation` fue utilizado debido a que el campo `format` heredado no era confiable;
- Test B utilizó una muestra de 16 casos y no todo el benchmark;
- las métricas de latencia observadas no constituyen un SLA;
- los errores del proveedor no permiten inferir retrospectivamente una causa técnica única.

---

## 20. Artefactos generados

### External validation

```text
data/evaluation/atomization_external_v1/
```

### Predicciones

```text
results/atomization_external_predictions_attempt1_v0_4.csv
results/atomization_external_predictions_v0_4.csv
results/atomization_external_retry_log_v0_4.csv
```

### Evaluación Test A

```text
results/atomization_external_evaluation_cases_v0_4.csv
results/atomization_external_evaluation_metrics_v0_4.csv
results/atomization_external_evaluation_summary_v0_4.json
```

### Failure analysis

```text
results/atomization_external_detection_failures_v0_4.csv
results/atomization_external_structural_failures_v0_4.csv
results/atomization_external_failure_summary_v0_4.json
```

### Test B

```text
results/atomization_external_stability_sample_v0_4.csv
results/atomization_external_stability_runs_v0_4.csv
results/atomization_external_stability_cases_v0_4.csv
results/atomization_external_stability_summary_v0_4.json
results/atomization_external_experiment_conclusion_v0_4.json
```

### Scripts

```text
scripts/run_atomization_external_v0_4.py
scripts/resume_atomization_external_v0_4.py
scripts/evaluate_atomization_external_v0_4.py
scripts/analyze_atomization_external_failures_v0_4.py
scripts/run_atomization_external_stability_v0_4.py
```

---

## 21. Commits relevantes

```text
d6d22ea  docs(data): freeze claim atomization external validation protocol v1
4925acc  feat(data): freeze external atomization review pool v1
5fd5db9  feat(data): freeze external atomization benchmark v1
7072912  feat(data): freeze external atomization ground truth v1
c691082  exp(data): freeze external atomization v0.4 predictions
0f4327d  exp(data): evaluate claim atomizer v0.4 on external validation v1
de6ba6e  exp(data): analyze external atomization v0.4 failures
```

El commit de cierre de Test B y de este documento deberá agregarse después de congelar los artefactos finales.

---

## 22. Estado final del experimento

**Claim Atomization v1 / candidate v0.4 queda cerrado.**

```text
External validation: COMPLETED
Failure analysis:    COMPLETED
Stability test:      COMPLETED
Content-support A/B: SKIPPED
Production use:      NO
Final decision:      STOP_V0_4_FOR_PRODUCTION_INTEGRATION
```

La evidencia obtenida es suficiente para concluir que `claim-atomizer-v0.4` no debe incorporarse al flujo productivo actual.

El experimento sí produjo valor técnico al identificar:

- limitaciones de generalización externa;
- patrones de sobre y sub-atomización;
- dificultad particular en relaciones;
- debilidad de recall en `non_propositional`;
- variabilidad estructural entre ejecuciones;
- necesidad de separar calidad del modelo y confiabilidad del proveedor.

Estos resultados pueden utilizarse como base para formular hipótesis de una futura línea de investigación sin modificar ni reabrir el candidato v0.4.