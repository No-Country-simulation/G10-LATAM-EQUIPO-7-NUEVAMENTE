# Claim Atomization v1 — Semantic Preservation Review

## Objetivo

Evaluar manualmente si las predicciones de ClaimAtomizer v0.1 preservan el significado factual completo del source claim.

Esta revisión es independiente de la evaluación de factual support.

## Criterios

- `meaning_preserved`: la suma de los átomos conserva todo el significado factual del claim.
- `qualifiers_preserved`: no se pierden ni debilitan calificadores como automáticamente, todos, antes, después, sin, por defecto, etc.
- `no_invented_information`: ningún átomo introduce información que no estaba en el source claim.
- `relations_isolated`: las relaciones factuales relevantes quedan separadas cuando deben evaluarse independientemente.
- `atoms_independently_evaluable`: cada átomo puede evaluarse sin depender de otro átomo para entender su proposición.
- `redundancy`: indica si el modelo produjo átomos semánticamente redundantes.

Resultado manual sugerido:

- `good`: atomización utilizable sin cambios importantes.
- `acceptable`: significado preservado pero con sobre-atomización o redundancia.
- `bad`: pérdida, invención, contaminación o descomposición semánticamente incorrecta.

---

## ATOM-V1-001

**Calibration:** `CAL-V1-004`

**Source claim ID:** `scene_1_narration_claim_2`

**Format:** `video_script`

**Human source support:** `unsupported`

### Source claim

También afirma que los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.

### Structural result

- expected class: `atomic`
- predicted class: `relational`
- expected atoms: `1`
- predicted atoms: `2`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` Los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[factual_proposition]` Los agentes de IA pueden desplegar modelos en producción.
2. `[negation_or_absence]` El despliegue de modelos en producción por agentes de IA ocurre de forma autónoma sin supervisión humana.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-002

**Calibration:** `CAL-V1-006`

**Source claim ID:** `key_point_3_claim_1`

**Format:** `tldr`

**Human source support:** `unsupported`

### Source claim

El decorador cifra automáticamente todas las respuestas GET.

### Structural result

- expected class: `atomic`
- predicted class: `relational`
- expected atoms: `1`
- predicted atoms: `2`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` El decorador cifra automáticamente todas las respuestas GET.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[factual_proposition]` El decorador cifra todas las respuestas GET.
2. `[scope_or_quantifier]` El cifrado de las respuestas GET ocurre automáticamente.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-003

**Calibration:** `CAL-V1-014`

**Source claim ID:** `question_1_explanation_claim_2`

**Format:** `quiz`

**Human source support:** `unsupported`

### Source claim

Además, usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.

### Structural result

- expected class: `atomic`
- predicted class: `relational`
- expected atoms: `1`
- predicted atoms: `2`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` Usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[causal_relation]` Usar etiquetas HTML mejora el posicionamiento SEO de una página.
2. `[scope_or_quantifier]` La mejora en el posicionamiento SEO ocurre automáticamente al usar etiquetas HTML.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-004

**Calibration:** `CAL-V1-015`

**Source claim ID:** `card_2_back_claim_2`

**Format:** `flashcards`

**Human source support:** `unsupported`

### Source claim

Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

### Structural result

- expected class: `compound`
- predicted class: `compound`
- expected atoms: `2`
- predicted atoms: `2`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` Los cuatro elementos mencionados son bloques fundamentales de JavaScript.
   - expected support: `supported`
2. `[negation_or_absence]` Los cuatro bloques no tienen una secuencia clara.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[factual_proposition]` Los cuatro elementos mencionados son bloques fundamentales.
2. `[negation_or_absence]` Los bloques no tienen una secuencia clara.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-005

**Calibration:** `CAL-V1-016`

**Source claim ID:** `conclusion_claim_1`

**Format:** `tldr`

**Human source support:** `unsupported`

### Source claim

El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### Structural result

- expected class: `relational`
- predicted class: `relational`
- expected atoms: `1`
- predicted atoms: `2`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[factual_proposition]` El paradigma dirigido por eventos procesa una ocurrencia notificable mediante lógica reactiva.
2. `[causal_relation]` El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-006

**Calibration:** `CAL-V1-018`

**Source claim ID:** `card_1_back_claim_2`

**Format:** `flashcards`

**Human source support:** `unsupported`

### Source claim

También cifra automáticamente todo el tráfico del clúster por defecto.

### Structural result

- expected class: `atomic`
- predicted class: `relational`
- expected atoms: `1`
- predicted atoms: `3`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` Kubernetes cifra automáticamente todo el tráfico del clúster por defecto.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[factual_proposition]` Cifra todo el tráfico del clúster.
2. `[scope_or_quantifier]` El cifrado del tráfico del clúster ocurre automáticamente.
3. `[scope_or_quantifier]` El cifrado del tráfico del clúster se aplica por defecto.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-007

**Calibration:** `CAL-V1-020`

**Source claim ID:** `scene_2_narration_claim_1`

**Format:** `video_script`

**Human source support:** `unsupported`

### Source claim

Antes de eso, la serie enseña conceptos básicos de la nube.

### Structural result

- expected class: `relational`
- predicted class: `relational`
- expected atoms: `2`
- predicted atoms: `2`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` La serie enseña conceptos básicos de la nube.
   - expected support: `supported`
2. `[temporal_relation]` La enseñanza de conceptos básicos de la nube ocurre antes del evento o contexto referido.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[factual_proposition]` La serie enseña conceptos básicos de la nube.
2. `[temporal_relation]` La enseñanza de conceptos básicos de la nube ocurre antes de eso.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-008

**Calibration:** `CAL-V1-020`

**Source claim ID:** `scene_2_narration_claim_2`

**Format:** `video_script`

**Human source support:** `unsupported`

### Source claim

Después volvemos a los ejercicios y otra vez a los servicios de Azure.

### Structural result

- expected class: `relational`
- predicted class: `relational`
- expected atoms: `3`
- predicted atoms: `3`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` La serie incluye ejercicios prácticos.
   - expected support: `supported`
2. `[factual_proposition]` La serie presenta servicios de Azure.
   - expected support: `supported`
3. `[temporal_relation]` Después se vuelve a los ejercicios y a los servicios de Azure.
   - expected support: `unsupported`

### Gemini v0.1 prediction

1. `[factual_proposition]` Se vuelve a los ejercicios.
2. `[factual_proposition]` Se vuelve otra vez a los servicios de Azure.
3. `[temporal_relation]` El regreso a los ejercicios y a los servicios de Azure ocurre después de otro evento.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-009

**Calibration:** `CAL-V1-001`

**Source claim ID:** `question_1_explanation_claim_1`

**Format:** `quiz`

**Human source support:** `supported`

### Source claim

El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible y considera prácticas de inteligencia artificial responsable.

### Structural result

- expected class: `compound`
- predicted class: `compound`
- expected atoms: `2`
- predicted atoms: `2`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible.
   - expected support: `supported`
2. `[factual_proposition]` El módulo considera prácticas de inteligencia artificial responsable.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible.
2. `[factual_proposition]` El módulo considera prácticas de inteligencia artificial responsable.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-010

**Calibration:** `CAL-V1-003`

**Source claim ID:** `key_point_1_claim_1`

**Format:** `tldr`

**Human source support:** `supported`

### Source claim

Crear solicitudes eficaces para LLM.

### Structural result

- expected class: `atomic`
- predicted class: `atomic`
- expected atoms: `1`
- predicted atoms: `1`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` Crear solicitudes eficaces para LLM.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` Crear solicitudes eficaces para LLM.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-011

**Calibration:** `CAL-V1-005`

**Source claim ID:** `card_1_back_claim_1`

**Format:** `flashcards`

**Human source support:** `supported`

### Source claim

La clase FastAPI, importada desde el paquete fastapi mediante: from fastapi import FastAPI.

### Structural result

- expected class: `compound`
- predicted class: `compound`
- expected atoms: `2`
- predicted atoms: `3`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` FastAPI es una clase.
   - expected support: `uncertain`
2. `[factual_proposition]` FastAPI se importa desde el paquete fastapi mediante 'from fastapi import FastAPI'.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` La clase se llama FastAPI.
2. `[factual_proposition]` La clase FastAPI es importada desde el paquete fastapi.
3. `[factual_proposition]` La importación de la clase FastAPI se realiza mediante la sentencia: from fastapi import FastAPI.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-012

**Calibration:** `CAL-V1-009`

**Source claim ID:** `summary_claim_1`

**Format:** `tldr`

**Human source support:** `supported`

### Source claim

El módulo enseña a almacenar y manipular datos en Python, incluyendo el uso de variables, operaciones numéricas y conversión de tipos.

### Structural result

- expected class: `compound`
- predicted class: `compound`
- expected atoms: `4`
- predicted atoms: `4`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` El módulo enseña a almacenar y manipular datos en Python.
   - expected support: `supported`
2. `[factual_proposition]` El módulo incluye el uso de variables.
   - expected support: `supported`
3. `[factual_proposition]` El módulo incluye operaciones numéricas.
   - expected support: `supported`
4. `[factual_proposition]` El módulo incluye conversión de tipos.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` El módulo enseña a almacenar y manipular datos en Python.
2. `[factual_proposition]` El módulo incluye el uso de variables.
3. `[factual_proposition]` El módulo incluye operaciones numéricas.
4. `[factual_proposition]` El módulo incluye conversión de tipos.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-013

**Calibration:** `CAL-V1-013`

**Source claim ID:** `scene_1_narration_claim_1`

**Format:** `video_script`

**Human source support:** `supported`

### Source claim

HTML es un lenguaje de marcado que indica a los navegadores web cómo estructurar las páginas que visitamos.

### Structural result

- expected class: `compound`
- predicted class: `compound`
- expected atoms: `2`
- predicted atoms: `2`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` HTML es un lenguaje de marcado.
   - expected support: `supported`
2. `[factual_proposition]` HTML indica a los navegadores web cómo estructurar las páginas que visitamos.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` HTML es un lenguaje de marcado.
2. `[factual_proposition]` HTML indica a los navegadores web cómo estructurar las páginas que visitamos.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-014

**Calibration:** `CAL-V1-015`

**Source claim ID:** `card_1_back_claim_1`

**Format:** `flashcards`

**Human source support:** `supported`

### Source claim

Funciones y eventos; y bucles; condicionales.

### Structural result

- expected class: `atomic`
- predicted class: `compound`
- expected atoms: `1`
- predicted atoms: `4`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` El contenido abarca funciones, eventos, bucles y condicionales.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` Se incluyen funciones.
2. `[factual_proposition]` Se incluyen eventos.
3. `[factual_proposition]` Se incluyen bucles.
4. `[factual_proposition]` Se incluyen condicionales.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-015

**Calibration:** `CAL-V1-017`

**Source claim ID:** `question_1_explanation_claim_1`

**Format:** `quiz`

**Human source support:** `supported`

### Source claim

El documento define Kubernetes como una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios.

### Structural result

- expected class: `atomic`
- predicted class: `compound`
- expected atoms: `1`
- predicted atoms: `2`
- exact structure: `False`
- structural error: `over_atomized`

### Frozen ground truth

1. `[factual_proposition]` El documento define Kubernetes como una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` El documento define Kubernetes como una plataforma portable y extensible de código abierto.
2. `[factual_proposition]` Kubernetes sirve para administrar cargas de trabajo y servicios.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-016

**Calibration:** `CAL-V1-019`

**Source claim ID:** `key_point_2_claim_1`

**Format:** `tldr`

**Human source support:** `supported`

### Source claim

La sección también presenta opciones para comenzar con Azure.

### Structural result

- expected class: `atomic`
- predicted class: `atomic`
- expected atoms: `1`
- predicted atoms: `1`
- exact structure: `True`
- structural error: `count_exact`

### Frozen ground truth

1. `[factual_proposition]` La sección presenta opciones para comenzar con Azure.
   - expected support: `supported`

### Gemini v0.1 prediction

1. `[factual_proposition]` La sección también presenta opciones para comenzar con Azure.

### Manual semantic review

**meaning_preserved:** `PENDING`

**qualifiers_preserved:** `PENDING`

**no_invented_information:** `PENDING`

**relations_isolated:** `PENDING`

**atoms_independently_evaluable:** `PENDING`

**redundancy:** `PENDING`

**semantic_quality:** `PENDING`

**review_notes:** PENDING

---
