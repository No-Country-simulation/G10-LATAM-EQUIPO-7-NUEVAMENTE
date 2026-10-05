# Retrieval Contract v1 — Data/IA ↔ Agentes

## Propósito

Este contrato define la estructura mínima que el equipo de **Agentes** debe entregar al equipo de **Data/IA** para evaluar la calidad del retrieval mediante:

- Recall@3
- Recall@5
- Precision@3
- Precision@5

Data/IA no depende de la implementación interna de embeddings, Vector Store o motor de búsqueda. Solo consume una salida estable y versionada.

## Versión del contrato

```text
contract_version = "1.0"
```

Si se modifica la estructura de campos, tipos, estados o semántica del contrato, debe incrementarse la versión.

## Entrada esperada al retrieval

| Campo | Tipo | Requerido | Descripción |
|---|---|---:|---|
| `case_id` | string | Sí | Identificador del caso. Debe coincidir con `ground_truth_v1.csv`. |
| `query` | string | Sí | Pregunta enviada al motor de retrieval. |
| `top_k` | integer | Sí | Número máximo de resultados. Para v1 se acuerda `top_k = 5`. |

## Respuesta estándar

| Campo | Tipo | Requerido | Descripción |
|---|---|---:|---|
| `contract_version` | string | Sí | Versión del contrato. |
| `case_id` | string | Sí | Identificador del caso evaluado. |
| `query` | string | Sí | Consulta original. |
| `top_k` | integer | Sí | Valor solicitado para retrieval. |
| `score_type` | string | Sí | Tipo de score usado, por ejemplo `cosine_similarity`. |
| `status` | string | Sí | `success`, `no_results` o `error`. |
| `results` | array | Sí | Lista ordenada de resultados recuperados. |
| `error` | object/null | Sí | Información de error técnico cuando `status = error`. |

## Estructura de cada resultado

| Campo | Tipo | Requerido | Descripción |
|---|---|---:|---|
| `rank` | integer | Sí | Posición del resultado; 1 es el más relevante. |
| `chunk_id` | string | Sí | Identificador del chunk recuperado. |
| `document_id` | string | Sí | Documento de origen. |
| `score` | number | Sí | Valor según `score_type`; no representa porcentaje. |
| `text` | string | Sí | Contenido del chunk recuperado. |
| `metadata` | object | No | Metadatos adicionales. |

## Estados permitidos

### `success`

El retrieval se ejecutó correctamente y devolvió resultados.

```text
status = "success"
results.length >= 1
error = null
```

### `no_results`

El retrieval se ejecutó correctamente, pero no encontró evidencia suficiente o resultados válidos.

```text
status = "no_results"
results = []
error = null
```

### `error`

Ocurrió un fallo técnico y el retrieval no pudo ejecutarse correctamente.

```text
status = "error"
results = []
error = {
  "code": "...",
  "message": "..."
}
```

## Reglas de ranking

- `rank = 1` corresponde al resultado más relevante.
- Los resultados conservan el orden real del motor.
- Recall@3 y Precision@3 usan los primeros 3 resultados.
- Recall@5 y Precision@5 usan los primeros 5 resultados.
- Para v1 se acuerda `top_k = 5`.

## Regla crítica de compatibilidad con Ground Truth

Para Retrieval v1, los `chunk_id` entregados por Agentes deben ser compatibles con:

```text
data/evaluation/chunks_v1.csv
data/evaluation/ground_truth_v1.csv
```

Si el equipo de Agentes cambia el chunking productivo y cambian los `chunk_id`, el Ground Truth debe versionarse nuevamente antes de calcular métricas.

No se debe comparar un Ground Truth construido con un chunking distinto al utilizado por el retrieval evaluado.

## Ejemplo — success

```json
{
  "contract_version": "1.0",
  "case_id": "CLD-ES-001-Q01",
  "query": "¿Qué es Kubernetes?",
  "top_k": 5,
  "score_type": "cosine_similarity",
  "status": "success",
  "results": [
    {
      "rank": 1,
      "chunk_id": "CLD-ES-001_CH_001",
      "document_id": "CLD-ES-001",
      "score": 0.91,
      "text": "Kubernetes es una plataforma de código abierto para administrar cargas de trabajo y servicios en contenedores.",
      "metadata": {
        "category": "Cloud/DevOps"
      }
    }
  ],
  "error": null
}
```

## Ejemplo — no_results

```json
{
  "contract_version": "1.0",
  "case_id": "CLD-ES-001-Q01",
  "query": "¿Qué es Kubernetes?",
  "top_k": 5,
  "score_type": "cosine_similarity",
  "status": "no_results",
  "results": [],
  "error": null
}
```

## Ejemplo — error

```json
{
  "contract_version": "1.0",
  "case_id": "CLD-ES-001-Q01",
  "query": "¿Qué es Kubernetes?",
  "top_k": 5,
  "score_type": "cosine_similarity",
  "status": "error",
  "results": [],
  "error": {
    "code": "RETRIEVAL_FAILED",
    "message": "No fue posible ejecutar la búsqueda vectorial."
  }
}
```

## Criterios de aceptación del contrato v1

1. Agentes confirma los campos obligatorios.
2. Agentes confirma el significado de `score` y `score_type`.
3. Agentes confirma que `rank` corresponde al ranking real.
4. Se confirma el manejo de `success`, `no_results` y `error`.
5. Se confirma compatibilidad de `chunk_id` con Ground Truth v1.
6. Se valida al menos un ejemplo real de respuesta con Data/IA.
