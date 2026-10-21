# Claim Atomization v0.4 — External Structural Validation v1

## Estado

**Tipo de evaluación:** External Structural Validation  
**Componente evaluado:** `claim-atomizer-v0.4`  
**Área:** Data/IA  
**Estado del modelo:** Frozen  
**Prompt tuning durante esta evaluación:** No  
**Impacto en producción:** Ninguno

---

## 1. Objetivo

Evaluar la capacidad de generalización de `claim-atomizer-v0.4` sobre un conjunto nuevo de claims que no haya participado en:

- development;
- calibration;
- validation;
- final evaluation previa;
- selección de ejemplos del prompt;
- ajuste de reglas del atomizador.

La evaluación busca determinar si el comportamiento observado anteriormente se mantiene fuera del corpus original utilizado para desarrollar Claim Atomization v1.

---

## 2. Preguntas de investigación

La evaluación debe responder:

1. ¿v0.4 distingue correctamente entre `valid_claim` y `non_propositional`?
2. ¿clasifica correctamente claims `atomic`, `compound` y `relational`?
3. ¿predice correctamente el número de átomos?
4. ¿preserva relaciones explícitas?
5. ¿evita over-atomization?
6. ¿evita under-atomization?
7. ¿generaliza a claims que no participaron en su desarrollo?
8. ¿mantiene el rendimiento observado en Final Eval v1?

---

## 3. Componente congelado

Durante esta evaluación no se permite modificar:

- `gemini_claim_atomizer_v0_4.py`;
- el prompt `claim-atomizer-v0.4`;
- schemas;
- reglas de atomización;
- ejemplos del prompt;
- parámetros del modelo con intención de mejorar métricas.

Cualquier cambio posterior deberá corresponder a una nueva versión del atomizador.

---

## 4. Dataset objetivo

Tamaño objetivo:

**80 claims**

Distribución objetivo:

| Clase | Cantidad |
|---|---:|
| Atomic | 20 |
| Compound | 20 |
| Relational | 20 |
| Non-propositional | 20 |
| Total | 80 |

Esta distribución es deliberada y se utiliza para garantizar cobertura estructural suficiente.

No representa necesariamente la distribución natural de producción.

---

## 5. Cobertura requerida

El conjunto debe incluir variedad de:

### Atomic

Claims con una sola proposición factual completa.

### Compound

Claims con dos o más proposiciones que puedan evaluarse independientemente.

### Relational

Debe intentarse incluir:

- `temporal_relation`
- `causal_relation`
- `conditional_relation`
- `comparative_relation`
- `negation_or_absence`
- `scope_or_quantifier`

### Non-propositional

Debe incluir:

- frases infinitivas;
- listas nominales;
- títulos;
- fragmentos;
- términos aislados;
- respuestas dependientes de contexto externo.

---

## 6. Formatos

Cuando sea posible, se buscará cobertura de:

- `quiz`
- `flashcards`
- `tldr`
- `video_script`

La clasificación estructural será independiente del formato.

---

## 7. Independencia del corpus anterior

No se permitirá reutilizar ninguno de los 59 claims del corpus original de Claim Atomization v1.

Antes de congelar el nuevo dataset se debe verificar overlap contra:

- development set;
- validation set;
- final eval v1.

Overlap permitido:

**0**

---

## 8. Orden experimental

El procedimiento debe ejecutarse en este orden:

1. congelar protocolo;
2. construir dataset externo;
3. verificar overlap;
4. congelar dataset;
5. crear ground truth humano;
6. validar ground truth;
7. congelar ground truth;
8. ejecutar `claim-atomizer-v0.4`;
9. congelar predicciones;
10. comparar predicciones contra ground truth;
11. documentar resultados.

El ground truth debe existir antes de consultar las predicciones del modelo.

---

## 9. Ground truth

Cada item deberá contener al menos:

- `source_claim_id`
- `claim_text`
- `format`
- `review_status`
- `atomization_class`
- número esperado de átomos
- átomos esperados
- `atom_type`

Valores permitidos de `review_status`:

- `valid_claim`
- `non_propositional`

Clases permitidas para claims válidos:

- `atomic`
- `compound`
- `relational`

---

## 10. Métricas

### Propositional detection

Clase positiva:

`non_propositional`

Se medirán:

- TP
- FP
- FN
- TN
- precision
- recall
- specificity
- accuracy
- coverage

### Structural atomization

Sobre claims humanos `valid_claim`:

- class accuracy
- count accuracy
- type sequence accuracy
- exact structure accuracy
- expected atom count
- predicted atom count
- atom delta
- inflation rate
- over-atomized cases
- under-atomized cases
- structural coverage

---

## 11. Criterios de factibilidad

Estos criterios se definen antes de ejecutar v0.4.

Objetivos experimentales:

- exact structure accuracy >= 0.90
- count accuracy >= 0.95
- non-propositional recall >= 0.85
- non-propositional precision >= 0.90
- ausencia de over-atomization sistemática
- ausencia de under-atomization sistemática
- coverage >= 0.95

Estos valores son criterios internos de decisión experimental y no representan estándares universales.

---

## 12. Interpretación

Superar estos criterios no implica integración automática en producción.

Esta prueba evalúa únicamente:

**generalización estructural del atomizador.**

La utilidad real para `content_support` deberá evaluarse posteriormente mediante una comparación A/B:

- evaluación del claim completo;
- evaluación del claim atomizado.

---

## 13. Reglas metodológicas

Durante la evaluación:

- no modificar GT después de consultar predicciones;
- no modificar v0.4;
- no hacer prompt tuning;
- no eliminar casos difíciles;
- no sustituir errores del modelo por anotaciones manuales;
- conservar fallos del proveedor;
- documentar retries por separado;
- no interpretar fallos genéricos como quota/rate limit sin evidencia.

---

## 14. Condición de cierre

Al finalizar la evaluación se deberá tomar una de tres decisiones:

### Continue

Existe evidencia suficiente para realizar el Test B y posteriormente el Test C.

### Investigate

Existe una señal positiva, pero se identificaron fallos concretos que requieren investigación adicional.

### Stop

La generalización estructural no justifica aumentar la complejidad del pipeline.

Ninguna decisión implica modificar automáticamente producción.