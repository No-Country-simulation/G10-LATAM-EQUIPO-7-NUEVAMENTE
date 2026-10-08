# Controlled Format Retrieval v2

## Objetivo

Evaluar el corpus controlado Markdown/TXT/PDF con el pipeline híbrido
de Retrieval V2 ya validado para NuevaMente.

Pipeline:

```text
document_id filter
→ Vector Search
+ BM25
→ RRF 50/50
→ candidate overfetch (Top-K × 3)
→ Cross-Encoder
→ Top-5
```

## Configuración

- Queries: 50
- Formatos: MD, TXT, PDF
- Top-K final: 5
- Candidate-K: 15
- RRF k: 60
- Cross-Encoder: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Evidence hit threshold: 0.50

## Resultados V2

| Formato | Hits | Hit rate | Evidence coverage | Reference token recall |
|---|---:|---:|---:|---:|
| MD | 49/50 | 98.00% | 0.8677 | 0.9893 |
| TXT | 48/50 | 96.00% | 0.8537 | 0.9591 |
| PDF | 49/50 | 98.00% | 0.8677 | 0.9776 |

## Cambios frente a Vector-only v1

- Casos/formato que pasan de NO HIT a HIT: **0**.
- Regresiones de HIT a NO HIT: **0**.
- Filas marcadas para revisión por hit/coverage: **0**.

## Casos foco

| Caso | Formato | V1 hit | V2 hit | V1 coverage | V2 coverage | Cambio |
|---|---|---|---|---:|---:|---|
| FE-ES-001-Q01 | MD | True | True | 0.5000 | 0.5000 | `unchanged_hit_coverage` |
| FE-ES-001-Q05 | MD | True | True | 0.8000 | 0.8000 | `unchanged_hit_coverage` |
| CLD-ES-001-Q05 | MD | False | False | 0.3333 | 0.3333 | `unchanged_hit_coverage` |
| FE-ES-001-Q01 | TXT | False | False | 0.0000 | 0.0000 | `unchanged_hit_coverage` |
| FE-ES-001-Q05 | TXT | True | True | 0.6000 | 0.6000 | `unchanged_hit_coverage` |
| CLD-ES-001-Q05 | TXT | False | False | 0.3333 | 0.3333 | `unchanged_hit_coverage` |
| FE-ES-001-Q01 | PDF | True | True | 0.5000 | 0.5000 | `unchanged_hit_coverage` |
| FE-ES-001-Q05 | PDF | True | True | 0.8000 | 0.8000 | `unchanged_hit_coverage` |
| CLD-ES-001-Q05 | PDF | False | False | 0.3333 | 0.3333 | `unchanged_hit_coverage` |

## Artefactos

- `retrieval_v2_md.csv`
- `retrieval_v2_txt.csv`
- `retrieval_v2_pdf.csv`
- `retrieval_v2_format_comparison.csv`
- `retrieval_v2_summary.csv`
- `retrieval_v1_vs_v2.csv`
- `retrieval_v2_regressions.csv`
- `retrieval_v2_focus_cases.csv`
- `run_manifest.json`

## Nota metodológica

Esta evaluación no usa `relevant_chunk_ids` como métrica primaria
porque el corpus controlado se vuelve a extraer y chunkear por formato.
La comparación se basa en evidencia textual equivalente y
`reference_token_recall`.

El benchmark histórico Retrieval V1/V2 permanece sin modificaciones.
