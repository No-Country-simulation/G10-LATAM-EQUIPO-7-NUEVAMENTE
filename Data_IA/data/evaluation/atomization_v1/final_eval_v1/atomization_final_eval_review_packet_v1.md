# Claim Atomization Final Eval v1 — Blind Human Review

## Objetivo

Crear el ground truth humano del conjunto final de evaluación después de congelar las predicciones de v0.4.

Este paquete fue generado únicamente desde el dataset fuente. No contiene predicciones del atomizador.

## Reglas de anotación

- No consultar las predicciones de v0.4.
- No consultar resultados de v0.1, v0.2 o v0.3.
- No inventar sujeto, predicado, objeto ni contexto ausente.
- Preservar calificadores factuales relevantes.
- No dividir por longitud o puntuación solamente.
- Separar solo hechos o relaciones evaluables por separado.
- Mantener listas simples con predicado compartido cuando corresponda.
- Cada átomo debe ser comprensible y evaluable de forma independiente.
- Si el texto no expresa una proposición factual suficiente, usar `non_propositional`.

## review_status permitido

- `valid_claim`
- `non_propositional`

## atomization_class permitido

- `atomic`
- `compound`
- `relational`

## atom_type permitido

- `factual_proposition`
- `temporal_relation`
- `causal_relation`
- `conditional_relation`
- `comparative_relation`
- `negation_or_absence`
- `scope_or_quantifier`

## Nota metodológica

`human_support_label` se muestra únicamente como metadata del dataset original. No debe utilizarse para decidir la estructura de atomización.

---

## 1. FINAL-V1-001 — CAL-V1-001

**source_claim_id:** `question_1_answer_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Los tipos de soluciones que la IA puede hacer posible y las prácticas de IA responsable

### Human annotation

**review_status:** `PENDING`

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

## 2. FINAL-V1-002 — CAL-V1-003

**source_claim_id:** `key_point_2_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Los LLM forman parte del módulo.

### Human annotation

**review_status:** `PENDING`

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

## 3. FINAL-V1-003 — CAL-V1-003

**source_claim_id:** `summary_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

El módulo espera considerar cómo crear solicitudes eficaces para los LLM.

### Human annotation

**review_status:** `PENDING`

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

## 4. FINAL-V1-004 — CAL-V1-003

**source_claim_id:** `summary_claim_4`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Crear solicitudes.

### Human annotation

**review_status:** `PENDING`

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

## 5. FINAL-V1-005 — CAL-V1-003

**source_claim_id:** `summary_claim_5`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

El objetivo aparece como una habilidad del módulo.

### Human annotation

**review_status:** `PENDING`

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

## 6. FINAL-V1-006 — CAL-V1-004

**source_claim_id:** `scene_1_narration_claim_1`

**format:** `video_script`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

El módulo incluye conceptos básicos de agentes de IA y soluciones de inteligencia artificial agéntica.

### Human annotation

**review_status:** `PENDING`

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

## 7. FINAL-V1-007 — CAL-V1-006

**source_claim_id:** `conclusion_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

@app.get('/') vincula una función con solicitudes GET dirigidas al path raíz.

### Human annotation

**review_status:** `PENDING`

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

## 8. FINAL-V1-008 — CAL-V1-006

**source_claim_id:** `key_point_1_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

El path configurado es '/'.

### Human annotation

**review_status:** `PENDING`

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

## 9. FINAL-V1-009 — CAL-V1-006

**source_claim_id:** `summary_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

El decorador @app.get('/') indica que la función situada debajo manejará solicitudes GET dirigidas al path raíz '/'.

### Human annotation

**review_status:** `PENDING`

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

## 10. FINAL-V1-010 — CAL-V1-009

**source_claim_id:** `conclusion_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Una habilidad central del módulo es almacenar y actualizar valores mediante variables.

### Human annotation

**review_status:** `PENDING`

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

## 11. FINAL-V1-011 — CAL-V1-009

**source_claim_id:** `key_point_1_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Almacenar y actualizar valores mediante variables.

### Human annotation

**review_status:** `PENDING`

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

## 12. FINAL-V1-012 — CAL-V1-009

**source_claim_id:** `key_point_2_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Realizar operaciones aritméticas con números.

### Human annotation

**review_status:** `PENDING`

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

## 13. FINAL-V1-013 — CAL-V1-009

**source_claim_id:** `key_point_3_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Convertir entre tipos de datos mediante funciones integradas.

### Human annotation

**review_status:** `PENDING`

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

## 14. FINAL-V1-014 — CAL-V1-011

**source_claim_id:** `question_1_answer_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

La agregación de datos.

### Human annotation

**review_status:** `PENDING`

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

## 15. FINAL-V1-015 — CAL-V1-011

**source_claim_id:** `question_1_explanation_claim_3`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Datos agregados, agregación; también agrupa y visualiza.

### Human annotation

**review_status:** `PENDING`

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

## 16. FINAL-V1-016 — CAL-V1-014

**source_claim_id:** `question_1_answer_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

Marcar partes del contenido para que aparezcan o actúen de cierta manera

### Human annotation

**review_status:** `PENDING`

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

## 17. FINAL-V1-017 — CAL-V1-016

**source_claim_id:** `key_point_1_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

Una interacción de click sobre un botón puede actuar como disparador de una rutina de respuesta.

### Human annotation

**review_status:** `PENDING`

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

## 18. FINAL-V1-018 — CAL-V1-016

**source_claim_id:** `key_point_2_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

La reacción asociada puede materializar información en un elemento de interfaz.

### Human annotation

**review_status:** `PENDING`

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

## 19. FINAL-V1-019 — CAL-V1-016

**source_claim_id:** `summary_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `high`

### Source claim

Los eventos constituyen ocurrencias observables del runtime cuya notificación habilita mecanismos reactivos de respuesta.

### Human annotation

**review_status:** `PENDING`

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

## 20. FINAL-V1-020 — CAL-V1-017

**source_claim_id:** `question_1_answer_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**annotation_priority:** `low`

### Source claim

Una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios

### Human annotation

**review_status:** `PENDING`

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

## 21. FINAL-V1-021 — CAL-V1-019

**source_claim_id:** `conclusion_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

El foco aquí está en la preparación previa del estudiante antes de avanzar en la ruta.

### Human annotation

**review_status:** `PENDING`

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

## 22. FINAL-V1-022 — CAL-V1-019

**source_claim_id:** `key_point_1_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

Se mencionan conocimientos básicos de TI como requisito previo.

### Human annotation

**review_status:** `PENDING`

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

## 23. FINAL-V1-023 — CAL-V1-019

**source_claim_id:** `summary_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**annotation_priority:** `medium`

### Source claim

La ruta indica como requisito previo contar con conocimientos básicos de términos y conceptos de TI.

### Human annotation

**review_status:** `PENDING`

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
