# Retrieval V2 - Evaluación

Esta carpeta contiene los resultados de evaluación del Retrieval V2 de Agentes.

## Ground Truth utilizado
- ground_truth_v2.csv

## Corpus
- chunks_v1.csv

## Retrieval V2
Incluye:
- filtros por metadata
- búsqueda vectorial
- BM25 lexical
- Reciprocal Rank Fusion (RRF)
- over-fetching de candidatos
- Cross-Encoder reranking

## Regla de reproducibilidad
Los resultados de Retrieval V1 no deben ser sobrescritos.

## Métricas a calcular
- Recall@3
- Recall@5
- Precision@3
- Precision@5

## Comparación principal
Retrieval V1 vs Retrieval V2 usando exactamente el mismo Ground Truth.
