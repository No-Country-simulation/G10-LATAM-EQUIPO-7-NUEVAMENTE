# Contrato BackendAPI → Agentes · Revisión V2 (propuesta para Sprint 4)

**Responsabilidad:** BackendAPI decide si hay corrección, persiste la versión `processing`, llama una sola vez a Agentes, persiste la respuesta terminal, solicita la reevaluación a Data/IA y actualiza el snapshot. Agentes solo genera una versión corregida. No debe consultar Data/IA ni decidir el número de ciclos.

## POST /api/v1/revise

### Request

```json
{
  "revision_id": "fmt_rev_abc123",
  "original_format_id": "fmt_quiz_001",
  "document_id": "doc_123",
  "format": "quiz",
  "generation_context": {
    "profile": "profesional",
    "niche": "finanzas",
    "detail_level": "avanzado",
    "learning_objective": "Comprender indicadores financieros"
  },
  "previous_content": {
    "title": "Quiz inicial",
    "instructions": "Selecciona la respuesta correcta",
    "questions": [{
      "question_id": "q1",
      "question": "¿Qué mide la liquidez?",
      "options": ["Capacidad de pago", "Ventas", "Inventario"],
      "correct_answer": "Capacidad de pago",
      "explanation": "Permite afrontar obligaciones a corto plazo"
    }]
  },
  "chunks_used": [{
    "chunk_id": "chunk_1",
    "document_id": "doc_123",
    "rank": 1,
    "score": 0.91,
    "text": "La liquidez es la capacidad de afrontar obligaciones de corto plazo."
  }],
  "evaluator_response": {
    "document_id": "doc_123",
    "format": "quiz",
    "verdict": "requires_revision",
    "heuristic_scores": {
      "relevance": 4.0,
      "coherence": 3.0,
      "didactic_adaptation": 2.0,
      "content_support": 4.0
    },
    "semantic_evaluation": {
      "status": "unavailable",
      "scores": null,
      "observations": [],
      "recommendations": [{
        "dimension": "didactic_adaptation",
        "message": "Simplificar los enunciados",
        "item_id": "q1"
      }],
      "unsupported_information": [],
      "error_code": "not_configured",
      "error_message": null,
      "model": null,
      "prompt_version": null,
      "latency_ms": null
    },
    "evaluator_version": "2.0",
    "rubric_version": "2.0"
  }
}
```

`evaluator_response` reproduce las **claves y los valores tipados** del contrato `EvaluationResponseV2` de Data/IA almacenado por Backend. No se inventan scores ni se convierte el estado técnico semántico en veredicto. La persistencia actual conserva la respuesta V2 estructurada, no los bytes HTTP originales; si se requiere equivalencia de bytes, será necesario ampliar el almacenamiento en otra tarea.

**Reglas de entrada:**

- `revision_id` identifica el intento reservado en Backend y sirve como clave de idempotencia. El equipo de Agentes debe confirmar almacenamiento o deduplicación por esta clave antes de habilitar reintentos automáticos.
- `original_format_id` conserva la identidad de la primera versión del ciclo.
- `generation_context` mantiene los mismos campos que `POST /evaluate/v2`.
- `previous_content` corresponde exclusivamente al esquema canónico del `format` indicado.
- `chunks_used` son evidencias documentales canónicas. No se inventan ni vuelven a recuperar silenciosamente; Agentes debe reutilizarlas o devolver evidencias nuevas verificables.
- `evaluator_response` tiene veredicto `requires_revision` o `rejected`, un resultado V2 no vacío, y hallazgos accionables. `approved`, `null` o respuestas V1 no disparan corrección.
- **Un solo intento de corrección por generación original**. La versión corregida nunca vuelve a generar otra corrección automáticamente.

### Response exitosa · HTTP 200

```json
{
  "revision_id": "fmt_rev_abc123",
  "original_format_id": "fmt_quiz_001",
  "document_id": "doc_123",
  "format": "quiz",
  "status": "success",
  "content": { "title": "Quiz revisado", "instructions": "...", "questions": [] },
  "sources_used": [{
    "chunk_id": "chunk_1", "document_id": "doc_123",
    "rank": 1, "score": 0.91, "text": "..."
  }],
  "execution_time_seconds": 1.25,
  "error_message": null,
  "error": null
}
```

El objeto `content` del ejemplo ilustra la estructura, pero **no constituye un Quiz válido**: cada formato debe cumplir sus validaciones canónicas antes de devolver éxito.

### Response de fallo · HTTP 4xx/5xx

```json
{
  "revision_id": "fmt_rev_abc123",
  "original_format_id": "fmt_quiz_001",
  "document_id": "doc_123",
  "format": "quiz",
  "status": "failed",
  "content": null,
  "sources_used": [],
  "execution_time_seconds": 0.75,
  "error_message": "Proveedor no disponible",
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "Proveedor no disponible",
    "retryable": true,
    "http_status": 503,
    "upstream_status": 503,
    "provider": "gemini"
  }
}
```

El HTTP status debe coincidir con `error.http_status`. Backend valida documento, tipo y ambos ID; una respuesta contradictoria **no** sustituye la versión original. La operación es atómica para un único formato (no HTTP 207).

### Fallos técnicos, trazabilidad e idempotencia

Backend reserva una versión `processing` antes de HTTP. Si Agentes falla, el intento queda `failed` y el original no se sobrescribe. Si la generación revisada tiene éxito y falla la reevaluación, se conserva `success` con evaluación ausente (visible en historial). El límite es una revisión por original, no una cadena indefinida.

**Política inicial:** 1 llamada HTTP por intento reservado y **0 reintentos automáticos**. Reintentar timeouts sin deduplicación del lado de Agentes podría ejecutar dos veces el LLM; coordinar un acuerdo de idempotencia para activar presupuestos de reintentos técnicos con la **misma** `revision_id`.

### Criterios de aceptación conjunta

1. Mismo `revision_id` enviado más de una vez no crea dos revisiones independientes en Agentes; comportamiento acordado por ambos equipos.
2. `200 success` con IDs y `sources_used` válidos se persiste y reevalúa.
3. Resultado pedagógico negativo por segunda vez se registra, pero no dispara otra corrección.
4. `rejected`, `requires_revision` y `null` tienen tratamiento explícito; `null` no produce revisión.
5. HTTP 4xx/5xx, timeout, JSON mal formado, IDs discordantes y caída de Data/IA conservan original y estados consistentes.
6. Se valida flujo real BackendAPI → Agentes → Data/IA → BackendAPI → Frontend; los mocks locales no equivalen a esta prueba.

### Despliegue

`AUTO_REVISION_ENABLED=false` por defecto. Habilitar solo tras implementación del endpoint, contrato HTTP y pruebas E2E. En BackendAPI el adaptador antiguo se conserva exclusivamente para pruebas directas aisladas hasta la migración completa de consumidores del puerto; el ciclo automático usa el contrato nuevo.
