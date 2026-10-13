# Diagnóstico de casos sensibles al formato

## Objetivo

Determinar si los casos especiales de Controlled Format Retrieval v1
se explican por pérdida de evidencia durante extracción/limpieza/chunking
o por ranking del retrieval.

El diagnóstico reconstruye los chunks por formato, crea índices diagnósticos
separados y busca más allá del Top-5 para localizar la evidencia.

## Casos analizados

- `FE-ES-001-Q01` — ¿Qué es HTML según el documento?
- `FE-ES-001-Q05` — ¿Qué puede hacer una etiqueta HTML con el contenido?
- `CLD-ES-001-Q05` — Menciona dos formas de describir a Kubernetes según el documento.

## Resumen

| Caso | Formato | Coverage documento | Coverage Top-5 | Primer rank con evidencia | Primer rank que alcanza hit | Diagnóstico |
|---|---|---:|---:|---:|---:|---|
| FE-ES-001-Q01 | MD | 0.5000 | 0.5000 | 1 | 1 | `top5_contains_sufficient_evidence` |
| FE-ES-001-Q01 | TXT | 0.5000 | 0.0000 | 7 | 7 | `ranking_issue_evidence_below_top5` |
| FE-ES-001-Q01 | PDF | 0.5000 | 0.5000 | 1 | 1 | `top5_contains_sufficient_evidence` |
| FE-ES-001-Q05 | MD | 1.0000 | 0.8000 | 1 | 1 | `top5_contains_sufficient_evidence` |
| FE-ES-001-Q05 | TXT | 1.0000 | 0.6000 | 1 | 1 | `top5_contains_sufficient_evidence` |
| FE-ES-001-Q05 | PDF | 1.0000 | 0.8000 | 1 | 1 | `top5_contains_sufficient_evidence` |
| CLD-ES-001-Q05 | MD | 1.0000 | 0.3333 | 5 | 8 | `ranking_issue_evidence_below_top5` |
| CLD-ES-001-Q05 | TXT | 1.0000 | 0.3333 | 5 | 9 | `ranking_issue_evidence_below_top5` |
| CLD-ES-001-Q05 | PDF | 1.0000 | 0.3333 | 4 | 7 | `ranking_issue_evidence_below_top5` |

## Interpretación de diagnósticos

- `evidence_absent_after_extraction_cleaning_chunking`: la evidencia no está
  presente en los chunks reconstruidos; revisar extracción/normalización.
- `insufficient_evidence_present_in_document_chunks`: existe evidencia parcial,
  pero ni todo el documento alcanza el umbral definido.
- `ranking_issue_evidence_below_top5`: la evidencia existe y puede alcanzar el
  umbral, pero aparece después del Top-5.
- `evidence_present_but_not_retrieved_within_diagnostic_top_k`: la evidencia
  existe en los chunks pero no apareció en la ventana diagnóstica solicitada.
- `top5_contains_sufficient_evidence`: el Top-5 contiene evidencia suficiente.
- `top5_contains_partial_evidence_below_threshold`: el Top-5 recupera evidencia
  parcial, pero no alcanza el threshold.
- `reproduction_mismatch_check_pipeline_state`: la reconstrucción actual no
  reproduce exactamente la corrida guardada; revisar versiones/estado del pipeline.

## Regla de decisión

No se modifica el chunker ni el retrieval con este script. Su propósito es
aislar la causa del fallo antes de abrir un experimento v2.
