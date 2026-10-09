# Controlled Format Retrieval Evaluation v1

## Objetivo

Evaluar si el formato de entrada modifica el comportamiento del retrieval
cuando el contenido semántico se mantiene controlado entre Markdown, TXT y PDF.

Cada formato se indexa en un índice vectorial separado.

## Configuración

- Corpus: `format_corpus_v1`
- Documentos: 10
- Queries: 50 (`ground_truth_v2.csv`)
- Formatos: Markdown, TXT y PDF
- Top-K: 5
- Filtro: `document_id`
- Criterio de hit: cobertura de evidencia >= 0.50
- Métricas auxiliares: evidence coverage y reference token recall

## Resultados globales

| Formato | Hits | Hit rate | Mean evidence coverage | Mean reference token recall |
|---|---:|---:|---:|---:|
| MD | 49/50 | 98.00% | 0.8677 | 0.9893 |
| TXT | 48/50 | 96.00% | 0.8537 | 0.9591 |
| PDF | 49/50 | 98.00% | 0.8677 | 0.9781 |

## Hallazgos principales

- Casos con desacuerdo de hit entre formatos: **1**.
- Casos con diferencia de coverage sin cambiar el hit: **1**.
- Fallos comunes a los tres formatos: **1**.

### FE-ES-001-Q01 — format-sensitive hit disagreement

- Documento: `FE-ES-001`
- Categoría: Frontend
- Query: ¿Qué es HTML según el documento?
- Coverage MD/TXT/PDF: 0.5000 / 0.0000 / 0.5000
- Hit MD/TXT/PDF: True / False / True

Interpretación: el caso es sensible al formato porque cambia el resultado
binario de evidencia. Debe conservarse como caso de diagnóstico.

### FE-ES-001-Q05 — format-sensitive coverage difference

- Documento: `FE-ES-001`
- Query: ¿Qué puede hacer una etiqueta HTML con el contenido?
- Coverage MD/TXT/PDF: 0.8000 / 0.6000 / 0.8000
- El resultado sigue siendo hit en los tres formatos.

### CLD-ES-001-Q05 — format-independent retrieval failure

- Documento: `CLD-ES-001`
- Query: Menciona dos formas de describir a Kubernetes según el documento.
- Coverage MD/TXT/PDF: 0.3333 / 0.3333 / 0.3333

Interpretación: el fallo aparece en los tres formatos, por lo que no debe
atribuirse al tipo de archivo. Requiere análisis separado de query, evidencia,
chunking o retrieval.

## Resumen por categoría

| Categoría | MD coverage | TXT coverage | PDF coverage | MD token recall | TXT token recall | PDF token recall |
|---|---:|---:|---:|---:|---:|---:|
| Backend | 0.9250 | 0.9250 | 0.9250 | 0.9908 | 0.9057 | 0.9304 |
| Cloud / DevOps | 0.9000 | 0.9000 | 0.9000 | 0.9558 | 0.9500 | 0.9615 |
| Data Science | 0.9167 | 0.9167 | 0.9167 | 1.0000 | 1.0000 | 1.0000 |
| Frontend | 0.8967 | 0.8267 | 0.8967 | 1.0000 | 0.9400 | 0.9988 |
| IA | 0.7000 | 0.7000 | 0.7000 | 1.0000 | 1.0000 | 1.0000 |

## Conclusión

El retrieval es altamente robusto entre Markdown, TXT y PDF cuando el
contenido semántico es equivalente. Markdown obtiene el mayor reference token
recall global; PDF mantiene el mismo hit rate y evidence coverage que Markdown;
TXT presenta una degradación pequeña y localizada.

No se modifica el chunker ni el corpus en esta fase. Esta corrida se conserva
como baseline experimental antes de cualquier optimización.

## Archivos

- `retrieval_md.csv`
- `retrieval_txt.csv`
- `retrieval_pdf.csv`
- `retrieval_format_comparison.csv`
- `retrieval_format_summary.csv`
- `controlled_format_category_summary.csv`
- `controlled_format_case_analysis.csv`
- `run_manifest.json`
