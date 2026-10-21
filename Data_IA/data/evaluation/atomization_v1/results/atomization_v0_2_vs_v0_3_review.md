# Claim Atomization — v0.2 vs v0.3 Review

## Objetivo

Comparar manualmente v0.2 y v0.3 contra el ground truth congelado, priorizando preservación semántica además de estructura.

### Etiquetas sugeridas

- `v0.2`
- `v0.3`
- `tie`
- `neither`

---

## ATOM-V1-001

### Source claim

También afirma que los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.

### Frozen GT

1. `[factual_proposition]` Los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` También afirma que los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` Los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-002

### Source claim

El decorador cifra automáticamente todas las respuestas GET.

### Frozen GT

1. `[factual_proposition]` El decorador cifra automáticamente todas las respuestas GET.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` El decorador cifra automáticamente todas las respuestas GET.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` El decorador cifra automáticamente todas las respuestas GET.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-003

### Source claim

Además, usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.

### Frozen GT

1. `[factual_proposition]` Usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` Usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.

### v0.3

**Class:** `atomic`

1. `[causal_relation]` Usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-004

### Source claim

Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

### Frozen GT

1. `[factual_proposition]` Los cuatro elementos mencionados son bloques fundamentales de JavaScript.
2. `[negation_or_absence]` Los cuatro bloques no tienen una secuencia clara.

### v0.2

**Class:** `compound`

1. `[factual_proposition]` Los elementos mencionados son bloques fundamentales, siendo los mismos cuatro.
2. `[negation_or_absence]` Los cuatro bloques no tienen una secuencia clara.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-005

### Source claim

El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### Frozen GT

1. `[factual_proposition]` El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-006

### Source claim

También cifra automáticamente todo el tráfico del clúster por defecto.

### Frozen GT

1. `[factual_proposition]` Kubernetes cifra automáticamente todo el tráfico del clúster por defecto.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` También cifra automáticamente todo el tráfico del clúster por defecto.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` También cifra automáticamente todo el tráfico del clúster por defecto.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-007

### Source claim

Antes de eso, la serie enseña conceptos básicos de la nube.

### Frozen GT

1. `[factual_proposition]` La serie enseña conceptos básicos de la nube.
2. `[temporal_relation]` La enseñanza de conceptos básicos de la nube ocurre antes del evento o contexto referido.

### v0.2

**Class:** `relational`

1. `[factual_proposition]` La serie enseña conceptos básicos de la nube.
2. `[temporal_relation]` La enseñanza de conceptos básicos de la nube ocurre antes de eso.

### v0.3

**Class:** `relational`

1. `[factual_proposition]` La serie enseña conceptos básicos de la nube.
2. `[temporal_relation]` La enseñanza de los conceptos básicos de la nube ocurre antes de eso.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-008

### Source claim

Después volvemos a los ejercicios y otra vez a los servicios de Azure.

### Frozen GT

1. `[factual_proposition]` La serie incluye ejercicios prácticos.
2. `[factual_proposition]` La serie presenta servicios de Azure.
3. `[temporal_relation]` Después se vuelve a los ejercicios y a los servicios de Azure.

### v0.2

**Class:** `relational`

1. `[factual_proposition]` Se vuelve a los ejercicios.
2. `[factual_proposition]` Se vuelve a los servicios de Azure.
3. `[temporal_relation]` El regreso a los ejercicios y a los servicios de Azure ocurre después.

### v0.3

**Class:** `relational`

1. `[temporal_relation]` Después volvemos a los ejercicios y otra vez a los servicios de Azure.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-009

### Source claim

El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible y considera prácticas de inteligencia artificial responsable.

### Frozen GT

1. `[factual_proposition]` El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible.
2. `[factual_proposition]` El módulo considera prácticas de inteligencia artificial responsable.

### v0.2

**Class:** `compound`

1. `[factual_proposition]` El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible.
2. `[factual_proposition]` El módulo considera prácticas de inteligencia artificial responsable.

### v0.3

**Class:** `compound`

1. `[factual_proposition]` El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible.
2. `[factual_proposition]` El módulo considera prácticas de inteligencia artificial responsable.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-010

### Source claim

Crear solicitudes eficaces para LLM.

### Frozen GT

1. `[factual_proposition]` Crear solicitudes eficaces para LLM.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` Crear solicitudes eficaces para LLM.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` Crear solicitudes eficaces para LLM.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-011

### Source claim

La clase FastAPI, importada desde el paquete fastapi mediante: from fastapi import FastAPI.

### Frozen GT

1. `[factual_proposition]` FastAPI es una clase.
2. `[factual_proposition]` FastAPI se importa desde el paquete fastapi mediante 'from fastapi import FastAPI'.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` La clase FastAPI se importa desde el paquete fastapi mediante la instrucción from fastapi import FastAPI.

### v0.3

**Class:** `compound`

1. `[factual_proposition]` La clase FastAPI se importa desde el paquete fastapi.
2. `[factual_proposition]` La importación de la clase FastAPI se realiza mediante: from fastapi import FastAPI.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-012

### Source claim

El módulo enseña a almacenar y manipular datos en Python, incluyendo el uso de variables, operaciones numéricas y conversión de tipos.

### Frozen GT

1. `[factual_proposition]` El módulo enseña a almacenar y manipular datos en Python.
2. `[factual_proposition]` El módulo incluye el uso de variables.
3. `[factual_proposition]` El módulo incluye operaciones numéricas.
4. `[factual_proposition]` El módulo incluye conversión de tipos.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` El módulo enseña a almacenar y manipular datos en Python, incluyendo el uso de variables, operaciones numéricas y conversión de tipos.

### v0.3

**Class:** `compound`

1. `[factual_proposition]` El módulo enseña a almacenar y manipular datos en Python.
2. `[factual_proposition]` El módulo incluye el uso de variables, operaciones numéricas y conversión de tipos.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-013

### Source claim

HTML es un lenguaje de marcado que indica a los navegadores web cómo estructurar las páginas que visitamos.

### Frozen GT

1. `[factual_proposition]` HTML es un lenguaje de marcado.
2. `[factual_proposition]` HTML indica a los navegadores web cómo estructurar las páginas que visitamos.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` HTML es un lenguaje de marcado que indica a los navegadores web cómo estructurar las páginas que visitamos.

### v0.3

**Class:** `compound`

1. `[factual_proposition]` HTML es un lenguaje de marcado.
2. `[factual_proposition]` HTML indica a los navegadores web cómo estructurar las páginas que visitamos.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-014

### Source claim

Funciones y eventos; y bucles; condicionales.

### Frozen GT

1. `[factual_proposition]` El contenido abarca funciones, eventos, bucles y condicionales.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` El contenido abarca funciones, eventos, bucles y condicionales.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` Funciones, eventos, bucles y condicionales.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-015

### Source claim

El documento define Kubernetes como una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios.

### Frozen GT

1. `[factual_proposition]` El documento define Kubernetes como una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` El documento define Kubernetes como una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` El documento define Kubernetes como una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---

## ATOM-V1-016

### Source claim

La sección también presenta opciones para comenzar con Azure.

### Frozen GT

1. `[factual_proposition]` La sección presenta opciones para comenzar con Azure.

### v0.2

**Class:** `atomic`

1. `[factual_proposition]` La sección también presenta opciones para comenzar con Azure.

### v0.3

**Class:** `atomic`

1. `[factual_proposition]` La sección también presenta opciones para comenzar con Azure.

### Manual comparison

**preferred_version:** `PENDING`

**meaning_preservation:** `PENDING`

**qualifier_preservation:** `PENDING`

**relation_isolation:** `PENDING`

**independent_evaluability:** `PENDING`

**redundancy:** `PENDING`

**review_notes:** PENDING

---
