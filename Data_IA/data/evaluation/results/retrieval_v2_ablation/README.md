# Retrieval V2 — Evaluación y Ablation Study

## 1. Objetivo

Este documento resume la evaluación experimental de Retrieval V2 del proyecto **NuevaMente**.

El objetivo fue determinar qué componentes del pipeline de recuperación aportan realmente al desempeño y validar si la configuración actual debe mantenerse o modificarse.

La evaluación se realizó utilizando:

- Ground Truth v2 congelado.
- 50 queries de evaluación.
- Corpus congelado `chunks_v1.csv`.
- 121 chunks.
- `top_k = 5`.
- Metadata filter por `document_id` cuando corresponde.
- Métricas: Recall@3, Recall@5, Precision@3 y Precision@5.

El análisis incluye:

1. Comparación V1 vs Retrieval V2.
2. Ablación del metadata prefilter.
3. Ablación del Cross-Encoder.
4. Fusión RRF + Cross-Encoder.
5. Ablación de señales Vector / BM25.
6. Weighted RRF.
7. Weighted RRF + Cross-Encoder.
8. Análisis de fallos restantes.

---

## 2. Configuración final recomendada

La configuración recomendada para Retrieval V2 es:

```text
Query
  ↓
Metadata filter: document_id
  ↓
Vector Search
+
BM25
  ↓
Reciprocal Rank Fusion (RRF 50/50)
  ↓
Cross-Encoder reranking
  ↓
Top-5
```

### Metadata filter

```text
document_id
```

### Embeddings

```text
paraphrase-multilingual-mpnet-base-v2
```

### Retrieval híbrido

```text
Vector Search + BM25
```

### Fusion

```text
Reciprocal Rank Fusion
RRF k = 60
```

Las señales Vector y BM25 mantienen el mismo peso.

### Candidate overfetch

```text
candidate_k = top_k * 3
```

Para `top_k = 5`:

```text
candidate_k = 15
```

### Reranker

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

---

## 3. Benchmark principal

Comparación entre el baseline V1 y Retrieval V2 completo.

| Métrica | V1 baseline | Retrieval V2 | Delta |
|---|---:|---:|---:|
| Recall@3 | 0.5733 | **0.9333** | **+0.3600** |
| Recall@5 | 0.7533 | **0.9533** | **+0.2000** |
| Precision@3 | 0.2133 | **0.3400** | **+0.1267** |
| Precision@5 | 0.1640 | **0.2080** | **+0.0440** |

Retrieval V2 mejora todas las métricas respecto al baseline.

Además:

```text
50 / 50 casos ejecutados correctamente
```

y no se detectaron errores técnicos durante el benchmark.

---

## 4. Ablación del metadata filter

Se compararon:

```text
V1 baseline
V2 sin filtro
V2 con document_id
```

### Resultados

| Métrica | V1 | V2 unfiltered | V2 filtered |
|---|---:|---:|---:|
| Recall@3 | 0.5733 | 0.8133 | **0.9333** |
| Recall@5 | 0.7533 | 0.8533 | **0.9533** |
| Precision@3 | 0.2133 | 0.3000 | **0.3400** |
| Precision@5 | 0.1640 | 0.1880 | **0.2080** |

### Aporte de Retrieval V2 sin metadata filter

Respecto a V1:

| Métrica | Delta |
|---|---:|
| Recall@3 | +0.2400 |
| Recall@5 | +0.1000 |
| Precision@3 | +0.0867 |
| Precision@5 | +0.0240 |

### Aporte adicional del filtro `document_id`

| Métrica | Delta |
|---|---:|
| Recall@3 | +0.1200 |
| Recall@5 | +0.1000 |
| Precision@3 | +0.0400 |
| Precision@5 | +0.0200 |

Los casos con `Recall@5 = 0` se redujeron de:

```text
V2 unfiltered: 7
V2 filtered:   2
```

### Conclusión

La mejora de Retrieval V2 no depende exclusivamente del metadata filter.

El motor híbrido mejora significativamente al baseline incluso sin filtros, mientras que `document_id` aporta una mejora adicional importante al reducir competencia entre documentos.

---

## 5. Ablación del reranker

Se compararon:

```text
RRF-only
Cross-Encoder
```

manteniendo constantes corpus, queries, metadata filtering, búsqueda vectorial, BM25, RRF y candidate pool.

### Resultados

| Métrica | RRF-only | Cross-Encoder |
|---|---:|---:|
| Recall@3 | 0.8833 | **0.9333** |
| Recall@5 | **0.9533** | **0.9533** |
| Precision@3 | 0.3200 | **0.3400** |
| Precision@5 | **0.2080** | **0.2080** |

El Cross-Encoder no modifica el Recall@5 global, pero mejora:

```text
Recall@3     +0.0500
Precision@3 +0.0200
```

### Casos donde cambia Recall@5

#### BE-ES-001-Q02

```text
RRF-only:      fallo
Cross-Encoder: acierto
```

#### BE-ES-002-Q03

```text
RRF-only:      acierto
Cross-Encoder: fallo
```

### Conclusión

El Cross-Encoder mejora el ranking temprano, aunque introduce una regresión puntual.

Se mantiene porque mejora Recall@3 y Precision@3 sin degradar las métricas globales @5.

---

## 6. Fusión RRF + Cross-Encoder

También se evaluó una fusión lineal entre los scores normalizados de RRF y Cross-Encoder.

Fórmula:

```text
final_score =
alpha * cross_normalized
+
(1 - alpha) * rrf_normalized
```

Se probaron:

```text
alpha = 0.25
alpha = 0.50
alpha = 0.75
```

### Resultados

| Variante | Recall@3 | Recall@5 | Precision@3 | Precision@5 |
|---|---:|---:|---:|---:|
| RRF-only | 0.8833 | 0.9533 | 0.3200 | 0.2080 |
| Cross-Encoder | **0.9333** | **0.9533** | **0.3400** | **0.2080** |
| Fusion 0.25 | 0.8933 | 0.9533 | 0.3267 | 0.2080 |
| Fusion 0.50 | 0.9133 | 0.9533 | 0.3333 | 0.2080 |
| Fusion 0.75 | 0.8933 | 0.9533 | 0.3267 | 0.2080 |

### Conclusión

La fusión lineal no supera al Cross-Encoder.

Todas las variantes mantienen el mismo Recall@5, pero reducen Recall@3.

Por tanto, no se recomienda sustituir el reranking absoluto del Cross-Encoder por una combinación lineal de scores.

---

## 7. Ablación de señales de retrieval

Se evaluaron individualmente las señales principales:

```text
Vector-only
BM25-only
Vector + BM25 mediante RRF
RRF + Cross-Encoder
```

### Resultados

| Variante | Recall@3 | Recall@5 | Precision@3 | Precision@5 |
|---|---:|---:|---:|---:|
| Vector-only | 0.7833 | 0.9033 | 0.2867 | 0.1960 |
| BM25-only | 0.5033 | 0.5733 | 0.1867 | 0.1280 |
| RRF | 0.8833 | **0.9533** | 0.3200 | **0.2080** |
| RRF + Cross-Encoder | **0.9333** | **0.9533** | **0.3400** | **0.2080** |

Casos con Recall@5 = 0:

```text
Vector-only:          4
BM25-only:           21
RRF:                  2
RRF + Cross-Encoder:  2
```

### Conclusión

BM25 tiene bajo desempeño como recuperador independiente, pero aporta información complementaria.

La combinación Vector + BM25 mediante RRF mejora Recall@5:

```text
Vector-only: 0.9033
RRF:         0.9533
```

Por tanto, no se recomienda eliminar BM25.

---

## 8. Weighted RRF

Se evaluó si otorgar mayor peso a la señal vectorial podía mejorar la recuperación.

La fórmula evaluada fue:

```text
weighted_rrf =
vector_weight / (k + vector_rank)
+
bm25_weight / (k + bm25_rank)
```

con:

```text
k = 60
```

### Configuraciones

| Variante | Vector | BM25 |
|---|---:|---:|
| 50/50 | 0.50 | 0.50 |
| 60/40 | 0.60 | 0.40 |
| 70/30 | 0.70 | 0.30 |
| 80/20 | 0.80 | 0.20 |

### Resultados

| Variante | Recall@3 | Recall@5 | Precision@3 | Precision@5 |
|---|---:|---:|---:|---:|
| RRF 50/50 | **0.8833** | 0.9533 | **0.3200** | 0.2080 |
| RRF 60/40 | 0.8433 | **0.9800** | 0.3067 | **0.2160** |
| RRF 70/30 | 0.8033 | 0.9500 | 0.2933 | 0.2080 |
| RRF 80/20 | 0.7833 | 0.9500 | 0.2867 | 0.2080 |

Casos Recall@5 = 0:

```text
50/50: 2
60/40: 1
70/30: 2
80/20: 2
```

### Hallazgo

RRF 60/40 mejora la cobertura Top-5:

```text
Recall@5:
0.9533 → 0.9800
```

pero degrada el ranking temprano:

```text
Recall@3:
0.8833 → 0.8433
```

---

## 9. Weighted RRF + Cross-Encoder

Debido al aumento de Recall@5 observado con RRF 60/40, se evaluó si esta configuración también mejoraba el pipeline completo.

Se compararon:

```text
RRF 50/50 + Cross-Encoder
RRF 60/40 + Cross-Encoder
```

### Resultados

| Variante | Recall@3 | Recall@5 | Precision@3 | Precision@5 |
|---|---:|---:|---:|---:|
| RRF 50/50 + Cross | **0.9333** | **0.9533** | **0.3400** | **0.2080** |
| RRF 60/40 + Cross | 0.9133 | 0.9333 | 0.3333 | 0.2040 |

Casos Recall@5 = 0:

```text
50/50 + Cross: 2
60/40 + Cross: 3
```

### Conclusión

La mejora de RRF 60/40 observada antes del reranking no se conserva al incorporar Cross-Encoder.

La variante 60/40 empeora todas las métricas del pipeline completo.

Por tanto:

```text
RRF 50/50 + Cross-Encoder
```

se mantiene como configuración recomendada.

---

## 10. Análisis de fallos restantes

Después del pipeline completo permanecen dos casos con `Recall@5 = 0`.

### BE-ES-002-Q03

Query:

```text
¿Qué comando crea el proyecto mysite dentro de djangotutorial?
```

Relevant chunk:

```text
BE-ES-002_CH_005
```

Trazabilidad:

```text
Vector Search:  rank 3
BM25:           rank 5
RRF:            rank 3
Cross-Encoder:  rank 8
```

#### Diagnóstico

```text
cross_encoder_reranking_failure
```

El chunk relevante llega correctamente al candidate pool, pero el Cross-Encoder lo degrada fuera del Top-5.

### CLD-ES-001-Q05

Query:

```text
Menciona dos formas de describir a Kubernetes según el documento.
```

Relevant chunk:

```text
CLD-ES-001_CH_002
```

Trazabilidad:

```text
Vector Search:  rank 1
BM25:           rank 13
RRF:            rank 6
Cross-Encoder:  rank 9
```

#### Diagnóstico

El embedding semántico recupera correctamente el chunk como primer resultado.

Sin embargo:

1. BM25 le asigna una posición baja.
2. RRF reduce su posición hasta rank 6.
3. Cross-Encoder lo degrada nuevamente hasta rank 9.

Este caso representa una limitación conocida del pipeline híbrido actual.

---

## 11. Decisión final

Después de las ablaciones realizadas, no se encontró una configuración experimental que supere consistentemente al pipeline actual.

Se mantiene:

```text
document_id filter
→ Vector Search
→ BM25
→ RRF 50/50
→ Cross-Encoder
→ Top-5
```

### Métricas finales

```text
Recall@3:    0.9333
Recall@5:    0.9533
Precision@3: 0.3400
Precision@5: 0.2080
```

Comparado con V1:

```text
Recall@3:    +0.3600
Recall@5:    +0.2000
Precision@3: +0.1267
Precision@5: +0.0440
```

---

## 12. Limitaciones conocidas

Retrieval V2 todavía presenta dos casos con Recall@5 = 0.

No se recomienda ajustar el pipeline únicamente para resolver estos casos porque las alternativas evaluadas generan regresiones en otros ejemplos o reducen las métricas globales.

Los fallos restantes quedan documentados como casos de análisis futuro.

---

## 13. Próximos pasos

Posibles líneas de investigación futuras:

1. Evaluar un Cross-Encoder multilingüe específicamente entrenado para semantic search.
2. Analizar estrategias de reranking adaptativo.
3. Evaluar weighting dinámico entre Vector y BM25 según tipo de query.
4. Aumentar el benchmark antes de realizar optimizaciones adicionales.
5. Evaluar comportamiento con documentos reales aportados por usuarios.
6. Analizar métricas end-to-end del sistema RAG, incluyendo calidad de respuesta generada.

Estas mejoras deben evaluarse mediante experimentos controlados y no reemplazar el pipeline actual sin evidencia de mejora global.

---

## 14. Reproducibilidad

El experimento utiliza artefactos congelados.

### Ground Truth

```text
Data_IA/data/evaluation/ground_truth_v2.csv
```

SHA-256:

```text
8cd975bc8b295d4a106470be55a65cfc10d3c25a61606c1f65855d713d95b515
```

### Corpus

```text
Data_IA/data/evaluation/chunks_v1.csv
```

SHA-256:

```text
309167963f1d5255374f3cb71b5533cfdcd97f02c7fd9650a0387c18903190c0
```

---

## 15. Scripts de evaluación

Los experimentos se encuentran en:

```text
Data_IA/scripts/
```

Scripts principales:

```text
run_retrieval_v2_benchmark.py
run_retrieval_v2_unfiltered_benchmark.py
compare_retrieval_v2_ablation.py
trace_retrieval_v2_failures.py
compare_reranker_ablation_v2.py
compare_fusion_ablation_v2.py
compare_retrieval_signal_ablation_v2.py
compare_weighted_rrf_ablation_v2.py
compare_weighted_rrf_cross_ablation_v2.py
```

---

## 16. Artefactos

Los resultados experimentales se encuentran en:

```text
Data_IA/data/evaluation/results/retrieval_v2_ablation/
```

Subdirectorios principales:

```text
trace_failures/
reranker_ablation/
fusion_ablation/
signal_ablation/
weighted_rrf_ablation/
weighted_rrf_cross_ablation/
```

El benchmark oficial Retrieval V2 permanece separado en:

```text
Data_IA/data/evaluation/results/retrieval_v2/
```

---

## 17. Notebook

El análisis reproducible y las conclusiones se documentan en:

```text
Data_IA/notebooks/06_data_ai_retrieval_ablation_v2.ipynb
```

---

## Estado

```text
Retrieval V2 evaluation: COMPLETE
Recommended configuration: RRF 50/50 + Cross-Encoder
Benchmark cases: 50
Recall@5: 0.9533
Known Recall@5 failures: 2
```