# BackendAPI ↔ Agentes — contrato de revisión pedagógica (Sprint 4)

**Referencias:** Trello BackendAPI #70 y #69; Agentes #67; Data/IA `POST /evaluate/v2`.

**Estado:** puerto y adaptador de Backend implementados; endpoint externo y prueba E2E pendientes de Agentes. Esta implementación **no activa por sí misma** la corrección automática ni modifica el flujo de generación.

## Responsabilidades

- **BackendAPI**: inicia la evaluación, toma el veredicto, verifica presupuesto (una corrección pedagógica automática por formato), crea una versión nueva, llama al puerto de revisión, conserva historial y solicita la segunda evaluación.
- **Data/IA**: produce `verdict`, `heuristic_scores` y `semantic_evaluation` mediante Evaluation V2.
- **Agentes**: recibe un formato y el feedback, reescribe utilizando evidencia del documento y devuelve una versión completa. No evalúa ni persiste versiones del ciclo.

Los campos internos `format_id`, `evaluation_id` y `cycle_id` **no** se transmiten a Agentes. La solicitud tampoco se mezcla con la regeneración manual de Frontend.

## Endpoint del proveedor

`POST /api/v1/revise` — una revisión de un solo formato; no utiliza HTTP 207.

### Request

```json
{
  "document_id": "doc_123",
  "format": "tldr",
  "current_content": {
    "title": "APIs REST",
    "summary": "REST define recursos accesibles mediante HTTP.",
    "key_points": ["GET consulta recursos"],
    "conclusion": "REST organiza las comunicaciones web."
  },
  "generation_context": {
    "profile": "beginner",
    "niche": "backend",
    "detail_level": "medium",
    "learning_objective": "Explicar REST"
  },
  "chunks_used": [
    {
      "chunk_id": "c1",
      "document_id": "doc_123",
      "rank": 1,
      "score": 3.74,
      "text": "REST organiza las interacciones alrededor de recursos."
    }
  ],
  "feedback": {
    "verdict": "requires_revision",
    "heuristic_scores": {
      "relevance": 4.0,
      "coherence": 4.0,
      "didactic_adaptation": 2.0,
      "content_support": 4.0
    },
    "semantic_evaluation": {
      "status": "success",
      "scores": {
        "relevance": 4.0,
        "coherence": 4.0,
        "didactic_adaptation": 2.0,
        "content_support": 4.0
      },
      "observations": [
        {
          "dimension": "didactic_adaptation",
          "severity": "medium",
          "message": "No explica qué es un recurso.",
          "item_id": null
        }
      ],
      "recommendations": [
        {
          "dimension": "didactic_adaptation",
          "message": "Introducir una definición accesible de recurso.",
          "item_id": null
        }
      ],
      "unsupported_information": [],
      "error_code": null,
      "error_message": null,
      "model": "gemini-model",
      "prompt_version": "v2",
      "latency_ms": 120
    }
  }
}
```

`current_content` usa exactamente el formato canónico vigente en Backend (quiz/flashcards/tldr/video_script), no un esquema nuevo. `chunks_used` contiene la evidencia factual íntegra, con `rank` único y `score` que puede ser negativo o superior a 1 (logit de retrieval). El contexto pedagógico no es una fuente factual.

El feedback conserva el objeto anidado de Evaluation V2. `verdict` solo puede ser `requires_revision` o `rejected`; `approved` y `null` **no** generan solicitudes de revisión. Para enviar la solicitud debe haber al menos un hallazgo accionable (`observations`, `recommendations` o `unsupported_information`). El consumidor no inventa observaciones si el evaluador no las produjo.

### Respuesta exitosa

```http
HTTP/1.1 200 OK
```

```json
{
  "document_id": "doc_123",
  "format": "tldr",
  "status": "success",
  "content": {
    "title": "APIs REST",
    "summary": "Un recurso es un elemento accesible mediante una dirección web.",
    "key_points": ["GET permite consultar un recurso"],
    "conclusion": "REST permite operar sobre recursos mediante HTTP."
  },
  "sources_used": [
    {"chunk_id": "c1", "document_id": "doc_123", "rank": 1, "score": 3.74, "text": "REST organiza las interacciones alrededor de recursos."}
  ],
  "error_message": null,
  "error": null,
  "execution_time_seconds": 2.3
}
```

`content` debe ser válido para el formato solicitado y `sources_used` debe representar la **lista completa** de evidencias usadas por la versión revisada. Backend no la fusiona a ciegas con la evidencia de la versión anterior.

### Fallo controlado

```http
HTTP/1.1 429 Too Many Requests
```

```json
{
  "document_id": "doc_123",
  "format": "tldr",
  "status": "failed",
  "content": null,
  "sources_used": [],
  "error_message": "Cuota agotada.",
  "error": {
    "code": "RESOURCE_EXHAUSTED",
    "message": "Cuota agotada.",
    "retryable": true,
    "http_status": 429,
    "upstream_status": 429,
    "provider": "gemini"
  },
  "execution_time_seconds": 0.5
}
```

El adaptador interpreta el cuerpo contractual aun si HTTP indica `4xx/5xx`. Un HTTP de validación FastAPI `422` sin cuerpo contractual, timeout, desconexión o respuesta JSON inválida se convierten en `AgentRevisionError`. **No existe reintento de transporte automático.**

## Implementación y límites de esta entrega

- `app/domain/revision_feedback.py`: value objects de feedback V2 tipados.
- `app/ports/agent_revision_port.py`: contratos internos y `AgentRevisionPort`.
- `app/infrastructure/integrations/http_agent_revision_adapter.py`: serialización HTTP, validaciones y mapeo de respuestas; sin lógica de negocio.
- `tests/unit/test_http_agent_revision_adapter.py`: pruebas de contrato con `httpx.MockTransport`.

La nueva interfaz se mantiene separada de `AgentsPort.generate_formats` y `HTTPAgentsAdapter` para no alterar `/generate` ni requerir cambios en el wiring hasta que el endpoint real sea publicable. En la tarjeta de orquestación se inyectará el puerto desde `app/main.py`, con el cliente HTTP existente de Agentes y una ruta configurable. En otra tarjeta se adaptará el puerto de Data/IA V1.1 a V2 y se construirá `RevisionFeedback` con sus resultados. **No se debe cambiar `compose.yaml` de Infra.**

## Validación de cierre

Las pruebas con MockTransport son de contrato, **no E2E**. La tarjeta solo se cierra cuando:

1. Agentes publica `/api/v1/revise` y confirma este esquema.
2. Se ejecuta un flujo real con documento cargado/indexado → generación → Evaluation V2 → revisión → nueva Evaluation V2 → persistencia y consulta desde Backend.
3. Se verifica con evidencia real el caso de éxito y un fallo controlado sin sobrescribir la versión inicial.
4. Se ejecutan `python -m ruff check .` y `python -m pytest -q` sobre `QA` sincronizada.

Hasta cumplir estos puntos, el estado será **implementación parcial validada en pruebas de contrato**.
