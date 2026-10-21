# Claim Atomization v1 — Experimental Evaluation

## Estado

**Estado actual:** Experimental  
**Integración en producción:** No  
**Versión evaluada más reciente:** `claim-atomizer-v0.4`  
**Área responsable:** Data/IA  
**Sprint:** Sprint 4

Este documento resume la evolución, evaluación y conclusiones del experimento de atomización de claims utilizado para estudiar posibles mejoras en la evaluación de `content_support`.

La atomización todavía **no forma parte del flujo productivo de evaluación**.

Su objetivo experimental es dividir un claim generado en unidades mínimas que puedan ser evaluadas de manera independiente respecto a la evidencia disponible.

---

## 1. Motivación

Durante la calibración de `content_support` se identificó que algunos claims contienen varias afirmaciones dentro de una misma unidad textual.

Esto puede producir problemas como:

- evidencia parcial;
- relaciones temporales o causales mezcladas con hechos base;
- afirmaciones parcialmente soportadas;
- errores difíciles de detectar mediante comparación léxica;
- falsos negativos cuando una parte del claim sí está soportada y otra no.

Ejemplo conceptual:

> El módulo explica Kubernetes y después vuelve a revisar los servicios de Azure.

Ese texto contiene al menos dos componentes:

1. una afirmación factual sobre Kubernetes;
2. una relación temporal sobre lo que ocurre después.

Evaluar ambos componentes como una sola unidad puede ocultar un error parcial.

Por esta razón se investigó la hipótesis:

> Atomizar claims antes de evaluar `content_support` puede mejorar la detección de soporte parcial y reducir falsos negativos.

## 2. Definición de Claim Atomization

Claim Atomization es el proceso de transformar un claim fuente en una o más unidades semánticas evaluables.

La entrada mínima del atomizador es:

- `source_claim_id`
- `claim_text`
- `format`

El atomizador **no recibe chunks ni evidencia documental**.

La evaluación de soporte ocurre en una etapa posterior.

---

## 3. Estados de revisión

Cada entrada puede clasificarse como:

### `valid_claim`

El texto contiene una proposición suficientemente completa para ser evaluada.

### `non_propositional`

El texto no contiene una proposición factual completa.

Ejemplos típicos:

- títulos;
- términos aislados;
- listas nominales;
- frases fragmentarias;
- expresiones infinitivas sin predicado factual completo;
- respuestas breves cuyo significado depende totalmente de una pregunta externa.

El atomizador no debe inventar:

- sujeto;
- predicado;
- objeto;
- contexto;
- relaciones no explícitas.

---

## 4. Clases de atomización

Para claims válidos se utilizan tres clases.

### `atomic`

El claim contiene una sola unidad evaluable.

Ejemplo:

> El módulo incluye conceptos básicos de agentes de IA.

Resultado:

- 1 átomo

### `compound`

El texto contiene al menos dos unidades diferentes que pueden evaluarse de forma independiente.

Ejemplo:

> El módulo incluye ejercicios prácticos y ofrece una visión general de los servicios de Azure.

Resultado:

1. El módulo incluye ejercicios prácticos.
2. El módulo ofrece una visión general de los servicios de Azure.

### `relational`

El claim expresa una relación explícita entre proposiciones o eventos.

Puede incluir:

- relaciones temporales;
- relaciones causales;
- condiciones;
- comparaciones;
- negación;
- alcance o cuantificadores.

Ejemplo:

> Después de completar el ejercicio, el estudiante vuelve al módulo anterior.

La relación temporal debe conservarse explícitamente.

## 5. Tipos de átomo

Los tipos definidos en v1 son:

- `factual_proposition`
- `temporal_relation`
- `causal_relation`
- `conditional_relation`
- `comparative_relation`
- `negation_or_absence`
- `scope_or_quantifier`

### Regla principal

La atomización debe preservar el significado original.

No se debe:

- eliminar calificadores importantes;
- convertir posibilidades en certezas;
- transformar relaciones en hechos independientes;
- introducir conocimiento externo;
- duplicar el mismo significado;
- fragmentar calificadores innecesariamente.

Cada átomo debe ser:

- trazable al claim original;
- semánticamente fiel;
- suficientemente independiente para evaluación posterior.

## 6. Development Set v1

El primer conjunto experimental fue construido a partir del corpus de calibración de `content_support`.

Se seleccionaron:

- 16 claims;
- todos los formatos disponibles;
- casos soportados y no soportados;
- ejemplos atómicos;
- ejemplos compuestos;
- relaciones explícitas.

El ground truth manual quedó congelado en:

`data/evaluation/atomization_v1/atomization_ground_truth_v1.csv`

Resumen del GT:

- source claims: 16
- átomos esperados: 26
- atomic: 8
- compound: 5
- relational: 3

Distribución de soporte:

- supported: 17
- unsupported: 8
- uncertain: 1

Este conjunto se utilizó como **development set**.

Por tanto, sus métricas no deben interpretarse como validación independiente.

## 7. Evolución del Claim Atomizer

### 7.1 v0.1

La primera versión priorizó la separación explícita de relaciones y proposiciones.

Resultado estructural:

- expected atoms: 26
- predicted atoms: 37
- atom delta: +11
- inflation rate: 0.4231
- class accuracy: 0.6250
- count accuracy: 0.5000
- type sequence accuracy: 0.5000
- exact structure accuracy: 0.5000

Problema principal:

**sobre-atomización**.

El modelo tendía a separar:

- calificadores;
- adverbios;
- relaciones implícitas;
- fragmentos redundantes.

---

### 7.2 v0.2

v0.2 fue diseñada para ser más conservadora.

Resultado:

- expected atoms: 26
- predicted atoms: 21
- atom delta: -5
- inflation rate: -0.1923
- class accuracy: 0.7500
- count accuracy: 0.8125
- type sequence accuracy: 0.8125
- exact structure accuracy: 0.7500

La sobre-atomización se redujo considerablemente.

Sin embargo, aparecieron casos de sub-atomización.

---

### 7.3 v0.3

v0.3 intentó mejorar la detección de estructuras compuestas y relaciones.

Resultado:

- expected atoms: 26
- predicted atoms: 21
- atom delta: -5
- inflation rate: -0.1923
- class accuracy: 0.8750
- count accuracy: 0.8125
- type sequence accuracy: 0.7500
- exact structure accuracy: 0.6875

v0.3 mejoró la clasificación general de clase, pero empeoró ligeramente la coincidencia estructural exacta respecto a v0.2.

La comparación manual v0.2 vs v0.3 mostró:

- preferencia v0.3: 4 casos
- preferencia v0.2: 3 casos
- empate: 8 casos
- ninguna versión adecuada: 1 caso

## 8. Claim Atomizer v0.4

v0.4 fue definida como candidato experimental congelado.

Commit:

`500100e`

Objetivos principales:

- reducir over-splitting;
- conservar predicados compartidos;
- separar predicados realmente independientes;
- preservar relaciones explícitas;
- introducir detección de `non_propositional`;
- evitar reconstrucción de fragmentos;
- evitar invención de contexto.

La salida de v0.4 incluye:

- `review_status`
- `atomization_class`
- `atoms`
- `atom_type`
- `model`
- `prompt_version`

Reglas importantes:

- `non_propositional` → `atomization_class = None`
- `non_propositional` → `atoms = []`
- `atomic` → exactamente 1 átomo
- `compound` → mínimo 2 átomos
- `valid_claim` → al menos 1 átomo

## 9. Validation Set v1

Se construyó un segundo conjunto de 20 items.

Distribución humana final:

- valid claims: 13
- non-propositional: 7
- expected atoms: 19
- atomic: 8
- compound: 5
- relational: 0

Resultados v0.4:

### Detección proposicional

- TP: 7
- FP: 0
- FN: 0
- TN: 13
- precision: 1.0000
- recall: 1.0000
- specificity: 1.0000
- accuracy: 1.0000

### Atomización estructural

- class accuracy: 0.7692
- count accuracy: 0.8462
- type sequence accuracy: 0.8462
- exact structure accuracy: 0.7692
- atom delta: +2
- inflation rate: 0.1053
- over-atomized cases: 2
- under-atomized cases: 0

### Limitación metodológica

Este conjunto **no debe considerarse una validación completamente independiente**.

Durante su revisión humana se detectó la existencia de múltiples entradas no proposicionales.

Esa observación influyó en el diseño de v0.4, especialmente en la incorporación explícita de:

`valid_claim`

vs

`non_propositional`

Por tanto, esta evaluación se considera una **validation/development evaluation**, no una prueba final completamente ciega.

## 10. Final Eval v1

Para obtener una evaluación más independiente se utilizaron los 23 claims restantes del corpus original.

Partición completa:

- corpus original: 59
- development: 16
- validation: 20
- final eval: 23

Se verificó:

- development/validation overlap: 0
- development/final overlap: 0
- validation/final overlap: 0
- complete partition: true

Commit del dataset final:

`8929c9b`

---

## 11. Protocolo Final Eval

El protocolo utilizado fue:

1. congelar v0.4;
2. congelar `final_eval_v1`;
3. ejecutar v0.4;
4. congelar predicciones;
5. construir review packet humano sin predicciones;
6. crear GT humano ciego;
7. congelar GT;
8. comparar por primera vez GT vs predicciones.

Commits principales:

- `500100e` — freeze claim atomizer v0.4 candidate
- `8929c9b` — freeze untouched atomization final eval v1
- `f2e3212` — freeze v0.4 final eval predictions
- `5a12745` — freeze blind atomization final eval ground truth v1
- `30da15c` — evaluate claim atomizer v0.4 on final eval v1

La anotación humana final no consultó las predicciones de v0.4.

## 12. Ground Truth Final

Final Eval v1 contiene:

- items: 23
- valid claims: 14
- non-propositional: 9
- expected atoms: 15

Clases:

- atomic: 13
- compound: 1
- relational: 0

Tipos:

- factual_proposition: 15
- temporal_relation: 0
- causal_relation: 0
- conditional_relation: 0
- comparative_relation: 0
- negation_or_absence: 0
- scope_or_quantifier: 0

Esta distribución es naturalmente desbalanceada.

No se modificó artificialmente para aumentar diversidad.

## 13. Resultados Final Eval v1

### 13.1 Detección proposicional

Clase positiva:

`non_propositional`

Resultados:

- TP: 5
- FP: 0
- FN: 4
- TN: 14
- precision: 1.0000
- recall: 0.5556
- specificity: 1.0000
- accuracy: 0.8261
- coverage: 1.0000

Interpretación:

v0.4 es muy preciso cuando decide que una entrada no es proposicional.

No produjo falsos positivos.

Sin embargo, dejó pasar 4 de los 9 casos no proposicionales.

Los cuatro falsos negativos corresponden principalmente a frases infinitivas:

- almacenar y actualizar valores;
- realizar operaciones aritméticas;
- convertir entre tipos de datos;
- marcar partes del contenido.

Esto revela un failure mode concreto:

> v0.4 reconoce bien fragmentos nominales y listas, pero todavía puede interpretar frases infinitivas como claims válidos.

## 14. Resultados de Atomización Estructural

Sobre los 14 claims humanos válidos:

- structural coverage: 1.0000
- expected atoms: 15
- predicted atoms: 15
- atom delta: 0
- inflation rate: 0.0000
- class accuracy: 0.9286
- count accuracy: 1.0000
- type sequence accuracy: 0.9286
- exact structure accuracy: 0.9286
- over-atomized cases: 0
- under-atomized cases: 0

Esto significa:

- 14/14 claims válidos fueron aceptados;
- el número total de átomos fue exactamente correcto;
- no hubo over-splitting;
- no hubo under-splitting;
- 13/14 casos coincidieron exactamente en estructura.

La discrepancia restante corresponde a una diferencia de taxonomía de clase/tipo, no a una diferencia en el número de átomos.

## 15. Comportamiento del proveedor

En la primera ejecución del final eval:

- success: 16/23
- failed: 7/23

Completion rate inicial:

0.6957

Los 7 fallos fueron reintentados de forma dirigida.

Resultado del retry:

- recovered: 7/7
- final completion: 23/23

No se modificó:

- v0.4;
- prompt;
- dataset;
- GT.

La causa exacta de los fallos iniciales no quedó determinada.

El wrapper devolvió:

`Gemini claim atomization request failed.`

Por tanto, no debe afirmarse que los fallos fueron causados específicamente por quota o rate limiting.

### Implicación

Una futura integración debería incluir:

- retry;
- backoff;
- timeout;
- logging;
- observabilidad;
- clasificación de errores del proveedor.

## 16. Comparación resumida

| Versión | Dataset | Exact Structure | Count Accuracy | Atom Delta | Inflation |
|---|---|---:|---:|---:|---:|
| v0.1 | development | 0.5000 | 0.5000 | +11 | +0.4231 |
| v0.2 | development | 0.7500 | 0.8125 | -5 | -0.1923 |
| v0.3 | development | 0.6875 | 0.8125 | -5 | -0.1923 |
| v0.4 | validation | 0.7692 | 0.8462 | +2 | +0.1053 |
| v0.4 | final_eval | 0.9286 | 1.0000 | 0 | 0.0000 |

No se deben comparar estas cifras como si provinieran del mismo conjunto.

Development, validation y final eval tienen composiciones diferentes.

La tabla se utiliza únicamente para mostrar la evolución general del experimento.

## 17. Limitaciones

### 17.1 Corpus interno

Todos los casos provienen del mismo corpus original de 59 claims.

Final Eval es más independiente respecto al diseño de v0.4, pero sigue siendo una evaluación interna.

No representa una validación externa.

### 17.2 Dataset final desbalanceado

Final Eval contiene:

- 13 atomic
- 1 compound
- 0 relational

Por tanto, no permite estimar bien el rendimiento sobre relaciones complejas.

### 17.3 Atom types limitados

Los 15 átomos del GT final son:

`factual_proposition`

No existe cobertura final para:

- temporal_relation
- causal_relation
- conditional_relation
- comparative_relation
- negation_or_absence
- scope_or_quantifier

### 17.4 Non-propositional recall

Recall final:

0.5556

Esto es insuficiente para utilizar v0.4 como filtro autónomo de entrada.

### 17.5 Provider reliability

La primera ejecución tuvo 7 fallos sobre 23 llamadas.

Aunque todos fueron recuperados, una integración productiva necesitaría manejo explícito de fallos.

## 18. Decisión de Sprint 4

Claim Atomization v0.4 se considera:

**Experimental candidate exitoso**

pero:

**No production integration**

### Razones para continuar investigándolo

- exact structure final: 0.9286
- count accuracy: 1.0000
- atom inflation: 0
- over-atomization: 0
- under-atomization: 0
- preservación consistente de claims válidos

### Razones para no integrarlo todavía

- non-propositional recall: 0.5556
- failure mode con frases infinitivas
- cobertura limitada de atom types
- final dataset pequeño
- dependencia del proveedor LLM
- fallos de proveedor en primera ejecución

Por tanto, Claim Atomization permanece fuera del flujo productivo de `content_support`.

## 19. Arquitectura futura propuesta

Si el enfoque se valida posteriormente, una posible arquitectura sería:

Generated content  
→ Claim extraction  
→ Propositional validation  
→ Claim atomization  
→ Evidence retrieval  
→ Atom-level content support  
→ Claim-level aggregation  
→ Evaluation result

La agregación experimental propuesta es:

- si cualquier átomo es `unsupported` → claim `unsupported`
- si ninguno es unsupported y alguno es `uncertain` → claim `uncertain`
- si todos son supported → claim `supported`

Esta regla todavía no forma parte de producción.

## 20. Próximos pasos recomendados

No crear inmediatamente `v0.5`.

Antes de continuar con tuning conviene:

1. conseguir un dataset externo nuevo;
2. incluir más claims relacionales;
3. incluir más atom types;
4. incluir explícitamente frases infinitivas;
5. evaluar múltiples dominios;
6. medir estabilidad entre corridas;
7. separar propositional detection de atomization;
8. mejorar clasificación de errores del proveedor.

La próxima evaluación debería utilizar claims que no hayan participado en:

- diseño;
- calibración;
- selección de ejemplos;
- anotación previa del prompt.

---

## 21. Estado de producción

```text
Claim Atomization v0.4

Status: experimental

Production integration: NO

Content-support decision impact: NONE

Allowed use:
- research
- diagnostics
- calibration
- offline evaluation
- failure analysis

Not allowed yet:
- automatic production gating
- automatic content rejection
- automatic support verdict changes
```

---

## 22. Archivos principales

### Implementación

- `data_ai/evaluation/claim_atomizer.py`
- `data_ai/evaluation/gemini_claim_atomizer.py`
- `data_ai/evaluation/gemini_claim_atomizer_v0_2.py`
- `data_ai/evaluation/gemini_claim_atomizer_v0_3.py`
- `data_ai/evaluation/gemini_claim_atomizer_v0_4.py`

### Development

- `data/evaluation/atomization_v1/atomization_dataset_v1.csv`
- `data/evaluation/atomization_v1/atomization_ground_truth_v1.csv`

### Validation

- `data/evaluation/atomization_v1/holdout_v1/`

### Final Eval

- `data/evaluation/atomization_v1/final_eval_v1/`

### Documentación

- `docs/content_support_claim_atomization_v1.md`

---

## 23. Conclusión

Claim Atomization mostró una mejora clara a lo largo de las iteraciones.

El principal problema inicial de `v0.1` fue la sobre-atomización.

`v0.4` logró eliminar ese comportamiento en Final Eval:

- atom delta = `0`
- over-atomization = `0`
- under-atomization = `0`
- exact structure accuracy = `0.9286`

Sin embargo, la detección de entradas no proposicionales todavía presenta una debilidad importante:

- recall = `0.5556`

El failure mode principal observado corresponde a frases infinitivas que el modelo interpreta como proposiciones válidas.

Por esta razón, la evidencia actual apoya continuar investigando Claim Atomization, pero todavía no justifica integrarlo como componente automático del pipeline productivo de evaluación.

**Decisión final de Sprint 4:** mantener Claim Atomization `v0.4` como componente experimental y reproducible, sin impacto sobre los verdicts de producción.