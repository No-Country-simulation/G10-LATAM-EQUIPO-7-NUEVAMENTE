# NuevaMente — Endpoint Generate Validation V1

**Estado:** Validado y cerrado  
**Sprint:** 5  
**Área responsable:** BackendAPI / Data/IA  
**Requerimiento asociado:** R04 (Selección de formato pedagógico de salida)  
**Tarea asociada:** Exponer Endpoint Público de Generación (`POST /generate`)  
**Integración principal:** BackendAPI ↔ Data/IA  
**Objetivo:** Registrar la validación funcional del nuevo endpoint público de generación asíncrona y el manejo de excepciones del dominio.

---

## 1. Contexto

Durante los Sprints anteriores, la generación de formatos educativos operaba de manera interna durante la carga documental, forzando la creación de los cuatro formatos por defecto (`quiz`, `flashcards`, `tldr`, `video_script`) y sin exponer un punto de acceso público para integraciones externas o solicitudes bajo demanda.

En el Sprint 5 se implementó el endpoint público:

```http
POST /api/v1/documents/{document_id}/formats/generate
```

Este endpoint permite solicitar la generación selectiva de uno o más formatos pedagógicos sobre un documento previamente indexado y responde de manera asíncrona para no bloquear al cliente.

---

## 2. Principios de arquitectura

1. **Generación selectiva:** El array `formats` de la solicitud define explícitamente qué formatos construir, rechazando valores duplicados mediante validación Pydantic (`PublicFormatGenerationRequest`).
2. **Procesamiento asíncrono:** El registro inicial ocurre de forma síncrona con estado `processing` y la ejecución se delega a `BackgroundTasks`, respondiendo inmediatamente `HTTP 202 Accepted`.
3. **Traducción de errores:** Las excepciones de dominio se mapean a contratos HTTP explícitos (`404`, `409`, `500`) mediante `APIHTTPException` y `ErrorCode`.

Flujo de ejecución del endpoint:

```text
Cliente / Integración
   ↓
POST /api/v1/documents/{document_id}/formats/generate
   ↓
FormatGenerationService.prepare_generation()
   ↓
Persistencia de intentos en estado "processing"
   ↓
Registro de tarea en BackgroundTasks (execute_background_generation)
   ↓
Respuesta inmediata HTTP 202 Accepted
   ↓
Generación (Agentes) + Evaluación V2 (Data/IA) en segundo plano
```

El endpoint no modifica la lógica interna del sistema ni el flujo productivo de evaluación: únicamente expone y orquesta la funcionalidad existente manteniendo la trazabilidad entre `BackendAPI`, `Agentes` y `Data/IA`.

---

## 3. Entorno de pruebas

- **Entorno:** QA (OCI)
- **URL:** `http://155.181.154.104:8000/docs`
- **Herramienta:** Swagger UI
- **Documento indexado:** `doc_70698467973644118c2e4f5a7cbdd035`

---

## 4. Caso de prueba 1: Generación selectiva (Happy Path)

### 4.1. Request enviado

Endpoint invocado:

```http
POST /api/v1/documents/doc_70698467973644118c2e4f5a7cbdd035/formats/generate
Content-Type: application/json
```

Payload enviado:

```json
{
  "formats": ["quiz", "tldr"],
  "profile": "beginner",
  "niche": "backend",
  "detail_level": "bajo"
}
```

### 4.2. Resultado esperado y validado

Código de estado HTTP:

```text
HTTP 202 Accepted
```

Respuesta estructurada (`FormatGenerationResponse`):

```json
{
  "document_id": "doc_70698467973644118c2e4f5a7cbdd035",
  "status": "processing",
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_01",
      "status": "processing"
    },
    "tldr": {
      "format_id": "fmt_tldr_01",
      "status": "processing"
    }
  }
}
```

Comportamiento verificado:

- Se registran en persistencia únicamente los formatos solicitados (`quiz` y `tldr`).
- Cada formato recibe un `format_id` estable y estado inicial `processing`.
- `BackgroundTasks` inicia `execute_background_generation` sin bloquear el hilo HTTP principal.
- Una vez completada la generación en `Agentes`, `BackendAPI` invoca automáticamente `POST /evaluate/v2` en `Data/IA`.

---

## 5. Validación de excepciones de dominio y contratos de error

Se verificó la traducción de excepciones del servicio de dominio hacia respuestas HTTP controladas en [`public_generation.py`](../../backend/app/api/v1/endpoints/public_generation.py):

| Caso | Excepción / Condición | HTTP Status | `ErrorCode` | Comportamiento validado |
|---|---|---:|---|---|
| **Documento inexistente** | `FormatGenerationDocumentNotFoundError` | `404 Not Found` | `DOCUMENT_NOT_FOUND` | Rechaza la solicitud cuando el `document_id` no existe en base de datos. |
| **Documento no indexado** | `DocumentNotReadyForGenerationError` | `409 Conflict` | `DOCUMENT_NOT_INDEXED` | Impide iniciar la generación cuando el documento aún no alcanza el estado `INDEXED`. |
| **Formatos duplicados o vacíos** | Validación Pydantic (`validate_unique_formats`) | `422 Unprocessable Entity` | `REQUEST_VALIDATION_ERROR` | Rechaza arrays vacíos o con formatos repetidos en la misma solicitud. |
| **Fallo de registro** | `GeneratedFormatRepositoryError` | `500 Internal Server Error` | `FORMAT_REGISTRATION_FAILED` | Devuelve error controlado si el documento está indexado pero falla la persistencia del intento. |

### 5.1. Ejemplo de respuesta de error (`404 Not Found`)

```json
{
  "code": "DOCUMENT_NOT_FOUND",
  "detail": "Document not found: doc_inexistente"
}
```

### 5.2. Ejemplo de respuesta de conflicto de estado (`409 Conflict`)

```json
{
  "code": "DOCUMENT_NOT_INDEXED",
  "detail": "Document is not ready for generation."
}
```

---

## 6. Conclusión

El endpoint público de generación asíncrona cumple con el requerimiento **R04** y respeta los contratos de integración entre `BackendAPI`, `Agentes` y `Data/IA`.

Resultado formal:

```text
Happy Path (202 Accepted):      PASS
Domain Exception Mapping:       PASS
Schema Validation (Pydantic):   PASS

Estado final:
VALIDADO Y CERRADO (Sprint 5)
```
