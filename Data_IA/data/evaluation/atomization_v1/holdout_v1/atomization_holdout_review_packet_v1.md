# Claim Atomization Holdout v1 — Manual Review Packet

## Objetivo

Definir manualmente el ground truth de atomización del holdout antes de ejecutar cualquier atomizador automático.

Este holdout no debe usarse para modificar prompts, reglas o modelos antes de su evaluación final.

## Reglas

- No usar outputs de Gemini.
- No usar resultados de v0.1, v0.2 o v0.3.
- No inventar información que no esté en el source claim.
- Preservar todos los calificadores factuales relevantes.
- No dividir por longitud ni puntuación solamente.
- Dividir únicamente proposiciones o relaciones evaluables por separado.
- Mantener listas simples con predicado compartido cuando corresponda.
- Cada átomo debe ser comprensible y evaluable de forma independiente.

## Clases permitidas

- `atomic`
- `compound`
- `relational`

## Tipos de átomo permitidos

- `factual_proposition`
- `temporal_relation`
- `causal_relation`
- `conditional_relation`
- `comparative_relation`
- `negation_or_absence`
- `scope_or_quantifier`

## Nota metodológica

`human_support_label` se conserva únicamente como metadata del claim original. No debe utilizarse para decidir cómo atomizar el texto.

---

## 1. HOLDOUT-V1-001 — CAL-V1-003

**source_claim_id:** `conclusion_claim_1`

**format:** `tldr`

**human_support_label:** `uncertain`

**annotation_priority:** `medium`

### Source claim

Por tanto, el objetivo es ese objetivo de solicitudes para LLM que el módulo espera considerar.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 2. HOLDOUT-V1-002 — CAL-V1-011

**source_claim_id:** `question_1_explanation_claim_4`

**format:** `quiz`

**human_support_label:** `uncertain`

**annotation_priority:** `medium`

### Source claim

La respuesta es agregación porque agregación es el concepto preguntado.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 3. HOLDOUT-V1-003 — CAL-V1-011

**source_claim_id:** `question_1_explanation_claim_2`

**format:** `quiz`

**human_support_label:** `uncertain`

**annotation_priority:** `medium`

### Source claim

El módulo la describe.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 4. HOLDOUT-V1-004 — CAL-V1-012

**source_claim_id:** `card_1_back_claim_1`

**format:** `flashcards`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Agregación de datos, agrupación de datos y visualizaciones de datos.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 5. HOLDOUT-V1-005 — CAL-V1-008

**source_claim_id:** `question_1_answer_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

La aplicación encapsula una funcionalidad web concreta; el proyecto actúa como agregado configuracional capaz de contener múltiples aplicaciones.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 6. HOLDOUT-V1-006 — CAL-V1-003

**source_claim_id:** `summary_claim_2`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

LLM.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 7. HOLDOUT-V1-007 — CAL-V1-007

**source_claim_id:** `scene_1_narration_claim_1`

**format:** `video_script`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Al crear proyectos Django conviene evitar nombres que coincidan con componentes integrados de Python o Django, como django o test, porque pueden producir conflictos.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 8. HOLDOUT-V1-008 — CAL-V1-015

**source_claim_id:** `card_1_back_claim_2`

**format:** `flashcards`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Esas estructuras, las cuatro, aparecen en el módulo.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 9. HOLDOUT-V1-009 — CAL-V1-011

**source_claim_id:** `question_1_explanation_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Agregación de datos.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 10. HOLDOUT-V1-010 — CAL-V1-006

**source_claim_id:** `key_point_2_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

La operación HTTP utilizada es GET.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 11. HOLDOUT-V1-011 — CAL-V1-013

**source_claim_id:** `scene_1_narration_claim_2`

**format:** `video_script`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Sus elementos permiten marcar distintas partes del contenido para que aparezcan o actúen de una manera determinada.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 12. HOLDOUT-V1-012 — CAL-V1-002

**source_claim_id:** `card_1_back_claim_1`

**format:** `flashcards`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Una representación conceptual previa del aprendizaje automático resulta instrumental, aunque su posesión no constituye una condición normativa de acceso al itinerario formativo.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 13. HOLDOUT-V1-013 — CAL-V1-014

**source_claim_id:** `question_1_explanation_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

Las etiquetas HTML pueden marcar diferentes partes del contenido para que aparezcan o actúen de cierta manera.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 14. HOLDOUT-V1-014 — CAL-V1-003

**source_claim_id:** `summary_claim_3`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Solicitudes.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 15. HOLDOUT-V1-015 — CAL-V1-020

**source_claim_id:** `scene_1_narration_claim_1`

**format:** `video_script`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

La serie incluye ejercicios prácticos para implementar primeros servicios y ofrece una visión general de servicios de Azure.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 16. HOLDOUT-V1-016 — CAL-V1-018

**source_claim_id:** `card_1_back_claim_1`

**format:** `flashcards`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

Como una plataforma de contenedores, una plataforma de microservicios o una plataforma portable de nube.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 17. HOLDOUT-V1-017 — CAL-V1-008

**source_claim_id:** `question_1_explanation_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

La relación se entiende como una separación entre unidad funcional reutilizable y contenedor configuracional del sitio.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 18. HOLDOUT-V1-018 — CAL-V1-003

**source_claim_id:** `key_point_3_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Solicitudes eficaces; módulo; LLM; solicitudes eficaces.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 19. HOLDOUT-V1-019 — CAL-V1-010

**source_claim_id:** `scene_1_narration_claim_1`

**format:** `video_script`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

El módulo aborda la persistencia simbólica y la mutabilidad de valores mediante variables, la operatoria aritmética y la coerción explícita entre representaciones tipadas usando funciones integradas de Python.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---

## 20. HOLDOUT-V1-020 — CAL-V1-015

**source_claim_id:** `card_2_back_claim_1`

**format:** `flashcards`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Eventos, funciones, después condicionales; bucles también.

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 5

**atom_text:** PENDING

**atom_type:** `PENDING`

#### Atom 6

**atom_text:** PENDING

**atom_type:** `PENDING`

**review_notes:** PENDING

---
