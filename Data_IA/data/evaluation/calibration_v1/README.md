# Calibration Manifest v1 — Heurístico vs Semántico

Primera muestra controlada de 20 casos.

- 5 categorías.
- 4 formatos, 5 casos por formato.
- 5 variantes, 4 casos por variante.
- Sin pesos ni `final_score`.
- `chunks_used` es la única evidencia factual para `content_support`.

Variantes:
- `clean_reference`
- `low_relevance`
- `low_coherence`
- `poor_didactic_adaptation`
- `unsupported_claim`

Siguiente paso: construir `generated_content` y `chunks_used` para cada caso, manteniendo la perturbación principal lo más aislada posible.
