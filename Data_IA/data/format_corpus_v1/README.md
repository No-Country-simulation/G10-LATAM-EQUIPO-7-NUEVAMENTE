# Controlled Format Corpus v1

## Objetivo

Este corpus se creó para evaluar el comportamiento del pipeline de NuevaMente
frente a distintos formatos de entrada:

- Markdown (`.md`)
- Texto plano (`.txt`)
- PDF (`.pdf`)

Cada documento parte de la misma fuente ubicada en:

`Data_IA/data/processed/`

El contenido del benchmark original ubicado en:

`Data_IA/data/evaluation/`

no se modifica.

## Principio experimental

La variable controlada es el formato del archivo.

Cada `document_id` tiene tres representaciones equivalentes:

- `md/<document_id>.md`
- `txt/<document_id>.txt`
- `pdf/<document_id>.pdf`

Esto permite comparar extracción, chunking, retrieval y generación
manteniendo constante el contenido semántico.

## Documentos

El corpus contiene 10 documentos y 30 archivos en total:

- 10 Markdown
- 10 TXT
- 10 PDF

## Reproducibilidad

`manifest.csv` registra:

- `document_id`
- categoría
- archivo fuente
- archivos generados
- hashes SHA-256
- versión del corpus

El corpus puede regenerarse ejecutando:

```bash
python Data_IA/scripts/build_controlled_format_corpus.py
```

## Importante

Este corpus es independiente del benchmark congelado.

No deben modificarse como parte de estas pruebas:

- `ground_truth_v2.csv`
- `chunks_v1.csv`
- manifests históricos del benchmark
- resultados oficiales de Retrieval V1/V2
