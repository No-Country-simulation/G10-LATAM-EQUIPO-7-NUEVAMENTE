# Multiformat End-to-End Validation — Sprint Closure

## Objective

Validate the NuevaMente generation and evaluation flow across controlled
source formats and all currently supported generated educational formats.

### Source formats

- Markdown (`md`)
- Plain text (`txt`)
- PDF (`pdf`)

### Generated formats

- Quiz
- Flashcards
- TL;DR
- Video Script

This produces a 3 x 4 validation matrix: **12 combinations**.

---

## Technical integration result

All 12 source/generated-format combinations completed the technical
integration flow successfully.

| Metric | Result |
|---|---:|
| Source formats | 3 |
| Generated formats | 4 |
| Total combinations | 12 |
| Technical passes | 12/12 |
| Data/IA `/evaluate` HTTP 200 | 12/12 |

The three source-format executions were run independently to avoid
accumulated model-memory pressure on Windows.

The validation uses the real retrieval/generation components and the
Data/IA FastAPI application through `TestClient`.

---

## Agent architecture adjustment

During the initial multiformat validation, Windows raised:

`os error 1455 - paging file is too small`

The root cause was duplicated heavy-model initialization caused by
`AgentV1` importing generated-content schemas from `agentes.api`, whose
module initialization also instantiated retrieval/model components.

Generated-content schemas were therefore extracted to:

`agentes/generated_schemas.py`

Both `agent_v1.py` and `api.py` now import the lightweight shared schemas,
avoiding the unnecessary initialization cycle.

---

## Quality Evaluator V1.0 baseline

Evaluation of the 12 generated artifacts produced:

| Status | Cases |
|---|---:|
| aprobado | 0 |
| requiere_revision | 7 |
| rechazado | 5 |

Diagnostics showed that several rejections were caused by lexical false
positives rather than unsupported factual content.

Important causes included:

- accent/Unicode variants;
- vocabulary explicitly provided by `generation_context`;
- presentation language in `video_script.visual_description`;
- paraphrasing in TL;DR outputs.

---

## Quality Evaluator V1.1

Evaluator V1.1 introduces conservative changes while keeping the existing
rubric and hallucination thresholds unchanged.

Changes:

- Unicode/accent normalization for lexical comparison;
- factual support is evaluated exclusively against `chunks_used`;
- TL;DR titles are excluded from factual-support scoring;
- Video Script factual support is evaluated from narration rather than
  presentation/visual instructions;
- naive handcrafted singularization was intentionally not promoted to
  production.

`generation_context` remains available for relevance and didactic-adaptation
evaluation, but it is not treated as factual evidence.

Evaluator version:

`1.1.0`

Rubric version remains:

`1.0.0`

---

## Regression tests

Data/IA complete test suite:

`64 passed`

This includes:

- API contract tests;
- schema validation;
- quality evaluator regression tests;
- V1.1-specific evaluator tests;
- retrieval evaluator tests;
- retrieval metrics/reporting;
- rubric tests.

---

## V1.0 vs V1.1 reevaluation

The same 12 existing generated artifacts were reevaluated without
regenerating content.

| Status | V1.0 | V1.1 |
|---|---:|---:|
| aprobado | 0 | 0 |
| requiere_revision | 7 | 11 |
| rechazado | 5 | 1 |

Additional validation:

- HTTP 200: **12/12**
- Evaluator version returned: **1.1.0**

Notable transitions:

- MD / TLDR: `rechazado -> requiere_revision`
- MD / Video Script: `rechazado -> requiere_revision`
- PDF / TLDR: `rechazado -> requiere_revision`
- PDF / Video Script: `rechazado -> requiere_revision`
- TXT / TLDR: remains `rechazado`

The remaining TXT/TLDR rejection is intentionally retained as an
adversarial case for future semantic-evaluator work.

---

## Sprint conclusion

The sprint validates:

- controlled-format retrieval across MD/TXT/PDF;
- all four currently supported generated formats;
- technical multiformat integration;
- Data/IA evaluation API compatibility;
- regression-safe Quality Evaluator V1.1;
- reproducible diagnostics for evaluator behavior.

Potential next-iteration work:

- semantic support/relevance evaluation;
- robust Spanish morphology/lemmatization;
- TXT/TLDR adversarial-case analysis;
- CrossEncoder reranking improvements.

Raw per-run payloads and generated responses remain local because they are
reproducible execution artifacts. Consolidated diagnostic results are kept
as sprint evidence.
