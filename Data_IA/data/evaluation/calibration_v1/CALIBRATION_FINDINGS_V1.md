# Calibration Findings V1

## Objetivo

Documentar los principales hallazgos obtenidos al comparar el **Ground Truth humano v1** con los resultados del **Semantic Evaluator** sobre el dataset controlado `calibration_v1`.

Este documento resume evidencia de calibración para apoyar:

- ajustes del prompt semántico;
- revisión humana de casos ambiguos;
- definición posterior de guardrails;
- diseño de la futura **Decision Layer**.

Este documento **no define todavía reglas productivas definitivas**.

---

## 1. Cobertura evaluada

Dataset total:

- **20 casos** de calibración.

Casos con evaluación semántica disponible:

- **19/20**.

Caso pendiente:

- `CAL-V1-017`
- variante: `clean_reference`
- categoría: `Cloud / DevOps`
- formato: `quiz`

---

## 2. Resultado principal

Sobre los **19 casos con evaluación semántica disponible**:

- la dimensión objetivo quedó dentro del rango humano esperado en **19/19 casos**;
- la detección de `unsupported_information` coincidió con el Ground Truth humano en **17/19 casos**;
- quedaron **2 falsos positivos probables** de `unsupported_information`.

Resumen:

```text
Casos totales: 20
Casos con evaluación semántica: 19
Target dimension dentro de rango: 19/19
Unsupported information alineado con GT humano: 17/19
Falsos positivos probables: 2
Caso pendiente: CAL-V1-017
```

Esto indica una buena alineación inicial del Semantic Evaluator con el Ground Truth humano para la dimensión principal de cada perturbación.

---

## 3. Hallazgo — CAL-V1-011

### Tipo

`low_coherence`

### Formato

`quiz`

### Dimensión objetivo

`coherence`

### Resultado

El Semantic Evaluator detectó correctamente el problema principal de coherencia.

Sin embargo, también produjo `unsupported_information`, mientras que el Ground Truth humano esperaba:

```text
expected_unsupported_information = False
```

### Revisión humana

Los elementos incluidos en el quiz:

- agregación de datos;
- agrupación de datos;
- visualizaciones de datos;
- conceptos básicos de informática;

están presentes en `chunks_used`.

Parte de esta información aparece como distractores dentro de las opciones del quiz.

### Interpretación

Se considera un **falso positivo probable de `content_support` / `unsupported_information`**.

El evaluador no debería interpretar automáticamente todos los distractores de un quiz como afirmaciones factuales emitidas por el contenido.

### Implicación para el prompt

Para `quiz`, el prompt debe indicar explícitamente que:

- los distractores no deben tratarse automáticamente como claims factuales;
- las opciones incorrectas pueden contener contenido diseñado deliberadamente para ser falso o no seleccionado;
- la evaluación factual debe centrarse principalmente en:
  - la respuesta correcta;
  - la explicación;
  - afirmaciones explícitamente presentadas como verdaderas.

---

## 4. Hallazgo — CAL-V1-012

### Tipo

`low_relevance`

### Formato

`flashcards`

### Dimensión objetivo

`relevance`

### Resultado

El Semantic Evaluator detectó correctamente la baja relevancia.

También produjo `unsupported_information`, mientras que el Ground Truth humano esperaba:

```text
expected_unsupported_information = False
```

### Revisión humana

El contenido de la flashcard:

```text
Agregación de datos, agrupación de datos y visualizaciones de datos.
```

está respaldado explícitamente por `chunks_used`.

El problema del caso es que el contenido no responde al objetivo específico del caso original.

### Interpretación

Se considera un **falso positivo probable de `content_support`**.

El evaluador parece mezclar parcialmente:

```text
relevance
```

con:

```text
content_support
```

### Implicación para el prompt

Debe reforzarse explícitamente que:

- un contenido puede estar factual y completamente respaldado por `chunks_used`;
- aun así puede ser poco relevante para el objetivo solicitado;
- la baja relevancia no debe convertirse automáticamente en `unsupported_information`.

Regla conceptual:

```text
low relevance != unsupported information
```

---

## 5. Hallazgo — CAL-V1-016

### Tipo

`poor_didactic_adaptation`

### Formato

`tldr`

### Dimensión objetivo

`didactic_adaptation`

### Resultado

El Semantic Evaluator detectó correctamente la mala adaptación didáctica.

También detectó una extrapolación factual secundaria.

### Revisión humana

El contenido afirma:

```text
El paradigma dirigido por eventos desacopla la ocurrencia notificable
de la lógica reactiva que procesa dicha señal.
```

El chunk describe:

- eventos como acciones u ocurrencias;
- su notificación por el sistema;
- la posibilidad de responder a ellos.

Sin embargo, el chunk no establece explícitamente:

```text
desacoplamiento
```

ni formula esa afirmación arquitectónica.

### Interpretación

En este caso, la detección de `unsupported_information` se considera razonable.

El Ground Truth humano fue corregido a:

```text
expected_unsupported_information = True
```

### Implicación

Este caso demuestra que la calibración humana también puede revelar etiquetas iniciales incompletas.

La comparación no debe asumir que el Ground Truth inicial es infalible; debe permitir revisión y corrección documentada cuando la evidencia lo justifique.

---

## 6. Separación entre dimensiones

Los resultados muestran que es importante mantener separadas las dimensiones:

```text
relevance
coherence
didactic_adaptation
content_support
```

En particular:

```text
low relevance != unsupported information
```

y:

```text
unsupported information != low relevance
```

También:

```text
poor didactic adaptation != unsupported information
```

aunque un mismo caso puede presentar problemas válidos en más de una dimensión.

La Decision Layer no debería inferir automáticamente una dimensión a partir de otra.

---

## 7. Implicación para `unsupported_information`

No se recomienda utilizar todavía una regla absoluta del tipo:

```text
unsupported_information_count > 0
→ requires_revision
```

sin considerar adicionalmente:

- severidad;
- dimensión afectada;
- formato;
- tipo de afirmación;
- posible falso positivo;
- score de `content_support`;
- relación entre el claim detectado y el contenido principal.

La señal debe tratarse como un indicador fuerte, pero no necesariamente como un guardrail aislado definitivo.

---

## 8. Recomendaciones para ajuste del prompt semántico

### 8.1 Quiz

No considerar automáticamente como afirmaciones factuales:

- distractores;
- opciones incorrectas;
- texto diseñado intencionalmente para evaluación.

La evaluación factual debe priorizar:

- `correct_answer`;
- `explanation`;
- afirmaciones presentadas explícitamente como verdaderas.

### 8.2 Flashcards

Separar claramente:

- alineación con el objetivo;
- respaldo factual.

Una tarjeta puede ser correcta y estar totalmente respaldada, pero no responder al objetivo solicitado.

Eso debe reducir:

```text
relevance
```

sin degradar automáticamente:

```text
content_support
```

### 8.3 TLDR

Distinguir entre:

- framing;
- estilo;
- síntesis;
- lenguaje pedagógico;
- afirmaciones factuales nuevas.

Las reformulaciones conceptuales que introduzcan nuevas relaciones o propiedades no explícitas en `chunks_used` deben revisarse como posibles extrapolaciones.

### 8.4 Video Script

No interpretar automáticamente:

```text
visual_description
```

como afirmación factual.

La evaluación factual debe centrarse principalmente en:

```text
narration
```

salvo que `visual_description` presente explícitamente contenido factual que se afirme como verdadero.

### 8.5 Relevance vs Content Support

Reforzar en el prompt:

```text
Relevance:
¿El contenido responde al objetivo y contexto solicitado?

Content Support:
¿Las afirmaciones factuales están respaldadas por chunks_used?
```

Una dimensión baja no debe arrastrar automáticamente a la otra.

---

## 9. Implicaciones para la Decision Layer

Estos hallazgos sugieren que la Decision Layer no debería basarse en:

- promedio simple;
- una sola dimensión;
- presencia binaria de `unsupported_information`;
- compensación matemática entre dimensiones críticas.

Debe priorizar reglas calibradas y explicables.

Ejemplos conceptuales a validar:

```text
content_support muy bajo
+
unsupported_information relevante
→ impedir approved
```

```text
relevance muy baja
→ requires_revision
```

```text
didactic_adaptation muy baja
→ requires_revision
```

sin asumir automáticamente que existe un problema factual.

La diferencia entre:

```text
requires_revision
```

y:

```text
rejected
```

todavía debe calibrarse con más evidencia.

---

## 10. Ground Truth humano

El Ground Truth humano v1 utiliza:

- rangos esperados por dimensión;
- observación esperada;
- expectativa de `unsupported_information`;
- `expected_verdict`;
- notas de revisión.

Se evita imponer un único score exacto porque la evaluación semántica admite variación razonable.

El objetivo no es exigir concordancia decimal exacta, sino comprobar:

- detección de la dimensión problemática;
- dirección correcta del score;
- consistencia con la evidencia;
- utilidad de observaciones;
- utilidad de recomendaciones;
- estabilidad entre ejecuciones.

---

## 11. Resultados consolidados actuales

```text
Casos totales: 20

Casos con evaluación semántica:
19/20

Dimensión objetivo dentro del rango humano:
19/19

Unsupported information alineado con Ground Truth:
17/19

Falsos positivos probables:
2

Casos con falsos positivos probables:
CAL-V1-011
CAL-V1-012

Caso pendiente:
CAL-V1-017
```

---

## 12. Casos relevantes para seguimiento

### CAL-V1-011

Problema principal:

```text
coherence
```

Riesgo detectado:

```text
quiz distractors
→ falso unsupported_information
```

### CAL-V1-012

Problema principal:

```text
relevance
```

Riesgo detectado:

```text
low relevance
→ falso content_support issue
```

### CAL-V1-016

Problema principal:

```text
didactic_adaptation
```

Hallazgo adicional válido:

```text
secondary unsupported extrapolation
```

### CAL-V1-017

Estado:

```text
semantic evaluation pending
```

Debe evaluarse antes de cerrar completamente la cobertura del dataset.

---

## 13. Limitaciones

Esta calibración corresponde a un dataset controlado pequeño.

Por lo tanto:

- no debe generalizarse todavía a todos los contenidos posibles;
- no prueba robustez total en producción;
- no mide aún estabilidad suficiente entre múltiples corridas;
- no valida por sí sola todos los formatos en todos los escenarios;
- no justifica pesos matemáticos arbitrarios;
- no justifica todavía una regla definitiva de Decision Layer.

Además, el conjunto consolidado incluye:

- resultados principalmente con `gemini-3.8-flash`;
- un caso (`CAL-V1-020`) evaluado con `gemini-3.6-flash` por limitación de cuota durante la corrida original.

Esto debe mantenerse documentado para reproducibilidad.

---

## 14. Próximos pasos

1. Ajustar el prompt semántico por formato.
2. Repetir `CAL-V1-011` después del ajuste.
3. Repetir `CAL-V1-012` después del ajuste.
4. Evaluar `CAL-V1-017`.
5. Validar estabilidad mediante múltiples ejecuciones.
6. Revisar calidad y accionabilidad de `observations`.
7. Revisar calidad y accionabilidad de `recommendations`.
8. Validar que las correcciones producidas por el Agente Revisor mejoren la reevaluación.
9. Definir reglas candidatas de Decision Layer a partir de evidencia calibrada.
10. Versionar prompt, Ground Truth y reglas antes de integración productiva.

---

## 15. Conclusión

El Semantic Evaluator muestra una alineación inicial fuerte con el Ground Truth humano en la dimensión objetivo de los casos controlados.

El resultado actual más importante es:

```text
19/19 casos evaluados
con dimensión objetivo dentro del rango humano esperado.
```

La principal área de mejora detectada es la separación estricta entre:

```text
relevance
```

y:

```text
content_support
```

además del tratamiento específico de estructuras por formato, especialmente en `quiz`.

Los casos `CAL-V1-011` y `CAL-V1-012` proporcionan evidencia concreta para mejorar el prompt semántico.

El caso `CAL-V1-016` muestra que la calibración también permite detectar y corregir supuestos incompletos del Ground Truth humano.

Estos hallazgos deben utilizarse como evidencia para:

- ajustar el Semantic Evaluator;
- mejorar la calidad del feedback;
- validar estabilidad;
- diseñar guardrails reproducibles;
- definir posteriormente una Decision Layer calibrada y explicable.
