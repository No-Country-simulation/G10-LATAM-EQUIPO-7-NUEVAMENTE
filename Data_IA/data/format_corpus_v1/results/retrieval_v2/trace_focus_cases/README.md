# Controlled Format Retrieval V2 — Focus Case Trace

## Objetivo

Trazar los casos foco del experimento controlado por formato a través de:

```text
Vector Search
→ BM25
→ RRF 50/50
→ Cross-Encoder
→ Top-5
```

La traza usa `palabras_clave_evidencia` porque los chunk IDs cambian
al volver a extraer y chunkear cada formato.

## Resumen

| Caso | Formato | Vector rank | BM25 rank | RRF rank | Cross rank | Final coverage | Hit | Diagnóstico |
|---|---|---:|---:|---:|---:|---:|---|---|
| FE-ES-001-Q01 | MD | 1 | 5 | 2 | 1 | 0.50 | True | `retrieved_in_final_top5` |
| CLD-ES-001-Q05 | MD | 1 | 2 | 1 | 8 | 0.33 | False | `cross_encoder_reranking_failure` |
| FE-ES-001-Q01 | TXT | 1 | 7 | 3 | 6 | 0.00 | False | `cross_encoder_reranking_failure` |
| CLD-ES-001-Q05 | TXT | 1 | 2 | 1 | 9 | 0.33 | False | `cross_encoder_reranking_failure` |
| FE-ES-001-Q01 | PDF | 1 | 6 | 2 | 1 | 0.50 | True | `retrieved_in_final_top5` |
| CLD-ES-001-Q05 | PDF | 1 | 2 | 1 | 7 | 0.33 | False | `cross_encoder_reranking_failure` |

## Archivos por caso/formato

- `01_vector_search.csv`
- `02_bm25.csv`
- `03_rrf_candidates.csv`
- `04_cross_encoder.csv`
- `05_final_top5.csv`

Cada archivo incluye evidencia encontrada por chunk, cobertura acumulada
y el rank donde se alcanza por primera vez el threshold 0.50.
