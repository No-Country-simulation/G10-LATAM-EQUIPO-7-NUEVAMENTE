# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI**, **Pydantic v2**, **SQLite** y **OCI Object Storage**.

BackendAPI actúa como **orquestador del producto**: recibe las solicitudes del Frontend, administra la metadata y el ciclo de vida de los documentos, persiste los archivos originales, coordina la indexación con RAG/Agentes, solicita la generación de material educativo y conserva los resultados para su consulta posterior.

BackendAPI **no implementa internamente** extracción de texto, limpieza, chunking, embeddings, Vector Store, retrieval semántico, prompts ni generación mediante LLM. Tampoco ejecuta directamente la evaluación de calidad de Data/IA. Estas responsabilidades permanecen desacopladas mediante Ports y Adapters.

El frontend se encuentra en [`../frontend`](../frontend).

> Los comandos de este documento se ejecutan desde `backend/`, salvo que se indique lo contrario.

---

## Estado actual

El flujo principal de Sprint 2 se encuentra integrado de extremo a extremo desde BackendAPI.

Actualmente están implementados:

### Documentos y almacenamiento

- API FastAPI y configuración centralizada.
- Endpoint de salud.
- `POST /api/v1/documents` como **única entrada pública para cargar y procesar un documento**.
- `GET /api/v1/documents` para listar documentos disponibles en la biblioteca.
- `GET /api/v1/documents/{document_id}` para consultar metadata y estado del documento.
- `GET /api/v1/documents/{document_id}/formats` para consultar Quiz y Flashcards persistidos.
- Admisión de archivos PDF, Markdown (`.md`) y TXT.
- Validación de extensión y MIME type declarado.
- Rechazo de archivos vacíos.
- Control de tamaño máximo de carga.
- Lectura del upload por bloques durante el staging temporal.
- Almacenamiento temporal desacoplado mediante `TemporaryStoragePort`.
- Implementación local mediante `LocalTemporaryStorageAdapter`.
- Eliminación del archivo temporal después del almacenamiento persistente o ante fallos.
- Identificación de documentos mediante SHA-256.
- Detección de contenido duplicado mediante SHA-256.
- Generación de `document_id` canónico para documentos nuevos.
- Persistencia de metadata y estado mediante `DocumentRepositoryPort`.
- Implementación SQLite mediante `SQLiteDocumentRepositoryAdapter`.
- Persistencia del archivo original en OCI mediante `ObjectStoragePort`.
- Implementación OCI mediante `OCIObjectStorageAdapter`.
- Convención de objetos OCI: `documents/{document_id}/original.ext`.
- Persistencia de `oci_object_name`.
- Recuperación interna: `document_id → metadata → oci_object_name → bytes`.
- Representación del documento recuperado mediante `RetrievedDocument`.
- Compensación cuando OCI finaliza correctamente pero falla la actualización final en BD.
- Eliminación compensatoria del objeto OCI para evitar objetos huérfanos.
- Manejo explícito mediante `DocumentStorageConsistencyError` cuando no puede garantizarse consistencia entre OCI y la BD.

### Orquestación automática de adaptación

La carga pública ya no termina en `STORED`.

Después de almacenar el documento, BackendAPI ejecuta internamente el caso de uso:

```text
AdaptationOrchestrationService
```

El orquestador:

1. consulta el estado actual del documento;
2. indexa el documento cuando está `STORED` o `INDEXING_FAILED`;
3. evita reindexar un documento que ya está `INDEXED`;
4. solicita automáticamente los formatos de Sprint 2;
5. delega la generación y persistencia a `FormatGenerationService`.

Los formatos solicitados automáticamente son:

```text
quiz
flashcards
```

El endpoint público independiente `/api/v1/adaptations` **ya no existe**. La adaptación permanece como un caso de uso interno y es invocada desde `POST /api/v1/documents`.

La capa API utiliza `app/api/adaptation_execution.py` para ejecutar la adaptación y traducir errores de aplicación e integración a respuestas HTTP sin trasladar lógica de negocio al endpoint.

### Contexto pedagógico recibido desde Frontend

`POST /api/v1/documents` recibe mediante `multipart/form-data`:

| Campo | Tipo | Obligatorio | Valores / descripción |
|---|---|---:|---|
| `file` | archivo | Sí | PDF, Markdown o TXT |
| `profile` | string | Sí | `beginner`, `intermediate`, `advanced` |
| `niche` | string | Sí | `general`, `backend`, `health`, `legal`, `business`, `humanities` |
| `detail_level` | string | Sí | Texto no vacío |
| `learning_objective` | string | No | Objetivo específico de aprendizaje |

Frontend **no envía**:

```text
document_id
formats
output_format
chunks
```

Backend genera el `document_id` y decide internamente que Sprint 2 produce Quiz y Flashcards.

### Respuesta de carga

`POST /api/v1/documents` ejecuta el procesamiento completo de forma **síncrona**.

En una ejecución exitosa, Backend ya realizó almacenamiento, indexación, generación y persistencia antes de responder. Sin embargo, la respuesta de carga **no incluye el contenido de Quiz ni Flashcards**, porque esos recursos se consultan mediante el endpoint específico de formatos.

Ejemplo:

```json
{
  "document_id": "doc_123",
  "filename": "manual.pdf",
  "status": "indexed",
  "duplicate": false
}
```

Para un documento nuevo la respuesta es normalmente:

```text
HTTP 201 Created
```

Para un contenido previamente registrado:

```text
HTTP 200 OK
```

con:

```json
{
  "duplicate": true
}
```

Un contenido duplicado reutiliza el mismo `document_id` y no vuelve a almacenar el archivo original en OCI. Si el documento ya está `INDEXED`, la orquestación evita una reindexación innecesaria y puede generar un nuevo intento de Quiz y Flashcards, conservando el historial de generaciones.

### Integración HTTP BackendAPI → RAG

La integración de indexación se mantiene desacoplada mediante:

```text
RAGIntegrationService
        ↓
RAGPort
        ↑
HTTPRAGAdapter
        ↓
POST /api/v1/index
```

BackendAPI:

- recupera el archivo original desde OCI;
- no expone credenciales ni referencias internas de OCI a RAG;
- envía `multipart/form-data` con `document_id` y `file`;
- valida la respuesta del servicio externo;
- controla las transiciones de estado de indexación.

Respuesta externa esperada:

```json
{
  "document_id": "doc_123",
  "status": "indexed"
}
```

Se valida que el `document_id` retornado sea exactamente el solicitado.

Estados de indexación:

```text
STORED
  ↓
INDEXING
  ↓
INDEXED
```

Ante un fallo durante la indexación:

```text
INDEXING
  ↓
INDEXING_FAILED
```

El reintento se permite desde `INDEXING_FAILED`.

Se manejan explícitamente:

- timeout;
- errores HTTP;
- errores de conexión;
- respuestas incompatibles;
- `document_id` inesperado;
- fallos al recuperar el archivo desde OCI.

Un fallo de recuperación desde OCI no se clasifica como fallo propio de RAG.

### Integración HTTP BackendAPI → Agentes

La generación se implementa mediante:

```text
FormatGenerationService
        ↓
AgentsPort
        ↑
HTTPAgentsAdapter
        ↓
POST /api/v1/generate
```

BackendAPI mantiene un contrato interno independiente del transporte HTTP.

`HTTPAgentsAdapter` es responsable de:

- traducir `AgentGenerationInput` al contrato HTTP de Agentes;
- invocar `POST /api/v1/generate`;
- validar la estructura de la respuesta;
- convertir Quiz y Flashcards al dominio canónico de BackendAPI;
- convertir `sources_used` en `ChunkEvidence`;
- conservar `error_message`;
- traducir errores HTTP, timeouts y errores de conexión a `AgentsError`;
- rechazar respuestas incompatibles con el contrato esperado.

La configuración se encuentra desacoplada mediante:

```text
AGENTS_BASE_URL
AGENTS_GENERATE_PATH
AGENTS_TIMEOUT_SECONDS
```

En desarrollo local RAG y Agentes pueden compartir el mismo servicio en:

```text
http://localhost:8001
```

En un despliegue Docker pueden configurarse mediante el nombre interno del servicio, por ejemplo:

```text
http://agents:8001
```

sin modificar código de aplicación.

### Modelo de generación de formatos

Sprint 2 trabaja públicamente con dos formatos:

```text
quiz
flashcards
```

`AdaptationOrchestrationService` solicita ambos automáticamente.

`FormatGenerationService`:

- valida que el documento exista;
- exige que el documento esté `INDEXED`;
- construye el contexto pedagógico;
- invoca `AgentsPort`;
- valida que el `document_id` retornado coincida con el solicitado;
- valida que Agentes retorne exactamente los formatos solicitados;
- rechaza formatos duplicados;
- convierte cada resultado válido en `GeneratedFormat`;
- persiste cada generación manteniendo historial;
- conserva los chunks utilizados como evidencia;
- registra intentos `FAILED` por cada formato solicitado cuando falla la integración con Agentes;
- registra intentos `FAILED` por cada formato solicitado cuando la respuesta de Agentes incumple el contrato;
- mantiene separado el estado del documento del estado de generación.

Estados soportados por formato:

```text
success
failed
no_results
```

Un error de comunicación con Agentes se traduce mediante `FormatGenerationIntegrationError`.

Cuando la llamada a Agentes falla antes de obtener resultados válidos, BackendAPI persiste un intento fallido para cada formato solicitado antes de propagar el error:

```text
quiz        → failed
flashcards  → failed
```

Del mismo modo, si Agentes responde pero incumple el contrato esperado —por ejemplo, retorna otro `document_id` o un conjunto incompleto de formatos— se persisten intentos `FAILED` antes de propagar `FormatGenerationContractError`.

Estos fallos **no modifican `DocumentStatus.INDEXED`**, porque la indexación ya terminó correctamente. El fallo pertenece al ciclo de vida de los formatos, no al ciclo de vida del documento.

### Contrato BackendAPI → Agentes

Solicitud HTTP esperada:

```json
{
  "document_id": "doc_123",
  "formats": [
    "quiz",
    "flashcards"
  ],
  "profile": "intermediate",
  "niche": "backend",
  "detail_level": "detailed",
  "learning_objective": "Comprender los conceptos principales."
}
```

`learning_objective` es opcional y no se envía cuando no fue informado.

Respuesta esperada:

```json
{
  "document_id": "doc_123",
  "results": [
    {
      "format": "quiz",
      "status": "success",
      "content": {},
      "sources_used": [],
      "error_message": null
    },
    {
      "format": "flashcards",
      "status": "success",
      "content": {},
      "sources_used": [],
      "error_message": null
    }
  ]
}
```

El contrato HTTP utiliza:

```text
sources_used
```

mientras que el dominio de BackendAPI utiliza:

```text
chunks_used
```

La transformación pertenece exclusivamente al adapter:

```text
sources_used
    ↓
HTTPAgentsAdapter
    ↓
ChunkEvidence
    ↓
chunks_used
```

### Contratos canónicos de contenido

Agentes debe devolver contenido usando estructuras canónicas acordadas entre Backend, Frontend y Data/IA.

#### QuizContent

```json
{
  "title": "Título del quiz",
  "instructions": "Instrucciones",
  "questions": [
    {
      "question_id": "q1",
      "question": "Pregunta",
      "options": [
        "Opción A",
        "Opción B"
      ],
      "correct_answer": "Opción A",
      "explanation": "Explicación"
    }
  ]
}
```

Reglas principales:

- debe contener al menos una pregunta;
- cada pregunta debe contener al menos dos opciones;
- las opciones no pueden estar vacías;
- no se permiten opciones duplicadas;
- `correct_answer` debe coincidir exactamente con una opción;
- `question_id` debe ser único dentro del Quiz.

#### FlashcardsContent

```json
{
  "title": "Título",
  "instructions": "Instrucciones",
  "cards": [
    {
      "card_id": "card_1",
      "front": "Concepto",
      "back": "Explicación"
    }
  ]
}
```

Reglas principales:

- debe contener al menos una tarjeta;
- `front` y `back` no pueden estar vacíos;
- `front` y `back` no deben ser idénticos;
- `card_id` debe ser único dentro del conjunto.

### Evidencias utilizadas durante la generación

Agentes devuelve las evidencias utilizadas durante retrieval:

```json
{
  "chunk_id": "chunk_1",
  "document_id": "doc_123",
  "rank": 1,
  "score": 0.93,
  "text": "Texto del chunk utilizado como evidencia."
}
```

Una generación exitosa conserva:

```text
content
+
chunks_used
```

BackendAPI **no consulta directamente Chroma ni el Vector Store** para reconstruir evidencias.

La frontera se mantiene:

```text
BackendAPI
    → orquestación y persistencia de negocio

Agentes/RAG
    → extracción, chunking, embeddings, retrieval,
      Vector Store y generación
```

Los `chunks_used` quedan persistidos junto con cada generación para mantener trazabilidad y permitir evaluación posterior aun si cambia el Vector Store.

### Consulta pública de formatos generados

Los contenidos educativos se consultan únicamente mediante:

```text
GET /api/v1/documents/{document_id}/formats
```

La consulta se implementa mediante:

```text
GeneratedFormatQueryService
    ↓
DocumentRepositoryPort
GeneratedFormatRepositoryPort
```

El servicio:

- valida que el `document_id` exista;
- consulta el historial persistido en `generated_formats`;
- selecciona un único resultado vigente por tipo;
- conserva la generación exitosa más reciente cuando existe;
- evita que un reintento posterior fallido o sin resultados oculte contenido válido previo;
- calcula el estado agregado consumido por Frontend.

Estados globales:

```text
pending
processing
ready
partial
error
```

Interpretación:

| Estado | Significado |
|---|---|
| `pending` | No existe historial de generación y el documento no está indexándose ni se encuentra en un estado fallido. Esto incluye un documento `INDEXED` sin intentos persistidos de generación. |
| `processing` | El documento se encuentra actualmente en estado `INDEXING`. |
| `ready` | Quiz y Flashcards disponen de una generación exitosa. |
| `partial` | Existe al menos un formato exitoso, pero no todos. |
| `error` | No existe ningún formato exitoso en el historial seleccionado, o el documento se encuentra en un estado fallido sin resultados. |

Estados por formato:

```text
success
failed
no_results
```

Criterio de selección por tipo:

```text
si existe al menos una generación exitosa
→ se expone la exitosa más reciente

si nunca existió una generación exitosa
→ se expone el intento más reciente
```

Esto permite conservar contenido válido aunque un reintento posterior falle.

`DocumentStatus.INDEXED` significa únicamente que la indexación terminó correctamente. **No significa que la generación continúe en proceso ni que los formatos estén listos.**

Cuando un documento está indexándose y todavía no existe historial de formatos:

```json
{
  "document_id": "doc_123",
  "status": "processing",
  "formats": null
}
```

Cuando un documento ya está `INDEXED` pero todavía no existe ningún intento de generación persistido:

```json
{
  "document_id": "doc_123",
  "status": "pending",
  "formats": null
}
```

BackendAPI no persiste actualmente un estado independiente `generation_in_progress`; por eso `processing` se reserva para la indexación activa y no se infiere a partir de `INDEXED`.

Si la indexación finaliza correctamente pero la integración con Agentes falla, BackendAPI conserva el documento como `INDEXED`, persiste ambos intentos como `FAILED` y la consulta devuelve:

```json
{
  "document_id": "doc_123",
  "status": "error",
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_failed",
      "status": "failed",
      "content": null,
      "error_message": "Agentes no pudo generar los formatos del documento doc_123."
    },
    "flashcards": {
      "format_id": "fmt_flashcards_failed",
      "status": "failed",
      "content": null,
      "error_message": "Agentes no pudo generar los formatos del documento doc_123."
    }
  }
}
```

Cuando ambos formatos están disponibles:

```json
{
  "document_id": "doc_123",
  "status": "ready",
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_1",
      "status": "success",
      "content": {
        "title": "Quiz",
        "instructions": "Seleccione la respuesta correcta.",
        "questions": [
          {
            "question_id": "q1",
            "question": "Pregunta",
            "options": [
              "Opción A",
              "Opción B"
            ],
            "correct_answer": "Opción A",
            "explanation": "Explicación"
          }
        ]
      },
      "error_message": null
    },
    "flashcards": {
      "format_id": "fmt_flashcards_1",
      "status": "success",
      "content": {
        "title": "Flashcards",
        "instructions": "Revise cada tarjeta.",
        "cards": [
          {
            "card_id": "card_1",
            "front": "Concepto",
            "back": "Explicación"
          }
        ]
      },
      "error_message": null
    }
  }
}
```

### Persistencia Sprint 2

SQLite contiene tres estructuras principales:

```text
documents
    1
    │
    N
generated_formats
    1
    │
    N
format_evaluations
```

La persistencia de formatos se implementa mediante:

```text
GeneratedFormatRepositoryPort
    ↑
SQLiteGeneratedFormatRepositoryAdapter
```

El repositorio permite:

- persistir mediante `create()`;
- recuperar mediante `find_by_id(format_id)`;
- recuperar historial mediante `find_by_document_id(document_id)`;
- conservar múltiples generaciones del mismo tipo;
- persistir resultados exitosos, fallidos o sin resultados;
- reconstruir contenido, contexto pedagógico y evidencias.

`generated_formats` conserva:

```text
format_id
document_id
format_type
status
content_json
chunks_used_json
profile
niche
detail_level
learning_objective
error_message
created_at
updated_at
```

Una generación exitosa persiste:

```text
GeneratedFormat
├── QuizContent | FlashcardsContent
├── GenerationContext
└── chunks_used
```

No existe restricción única:

```text
document_id + format_type
```

por lo que se conserva historial:

```text
document
    ├── quiz generación 1
    ├── quiz generación 2
    └── flashcards generación 1
```

Integridad referencial:

```text
generated_formats.document_id
→ documents.document_id
```

Errores explícitos:

- `GeneratedFormatAlreadyExistsError`
- `GeneratedFormatDocumentNotFoundError`
- `GeneratedFormatRepositoryError`

### Modelo de evaluación preparado

La integración HTTP efectiva con Data/IA **no forma parte del pipeline obligatorio actual**, pero BackendAPI dispone del modelo necesario para incorporarla sin rediseñar generación ni persistencia.

Se encuentran preparados:

```text
DataIAPort
FormatEvaluationService
FormatEvaluationRepositoryPort
SQLiteFormatEvaluationRepositoryAdapter
```

Una evaluación pertenece a una generación concreta:

```text
GeneratedFormat 1 → N FormatEvaluation
```

Las evaluaciones anteriores no se sobrescriben y se conserva historial.

Campos preparados:

```text
estado
relevancia
coherencia
adaptación didáctica
información respaldada
información no respaldada
observaciones
evaluator_version
rubric_version
```

Estados acordados:

```text
aprobado
requiere_revision
rechazado
```

---

## Arquitectura

BackendAPI mantiene separación por responsabilidades:

```text
API
 ↓
Application
 ↓
Ports
 ↑
Infrastructure implementa los Ports
```

| Capa | Responsabilidad |
|---|---|
| `api/` | Endpoints HTTP, dependencias FastAPI y traducción de errores de aplicación a HTTP |
| `schemas/` | Contratos externos de entrada y salida |
| `domain/` | Entidades, estados, contenido canónico y reglas de dominio |
| `application/` | Casos de uso y orquestación |
| `ports/` | Contratos hacia persistencia e integraciones externas |
| `infrastructure/` | Adapters e implementaciones concretas |
| `core/` | Configuración, logging, excepciones y utilidades |

### Fronteras del sistema

```text
Frontend
    ↓
BackendAPI
    ├── SQLite
    ├── OCI Object Storage
    ├── RAG / Agentes
    └── Data/IA (preparado, no obligatorio en el pipeline actual)
```

BackendAPI es el único punto de entrada del Frontend hacia los servicios de negocio e IA.

RAG/Agentes:

- no accede directamente a la BD de negocio;
- no necesita credenciales de OCI;
- no administra la persistencia de documentos de negocio;
- es responsable de extracción, limpieza, chunking, embeddings, retrieval, Vector Store y generación.

Data/IA:

- está desacoplado mediante un Port;
- puede evaluar calidad del contenido generado;
- no administra documentos;
- no genera material educativo;
- todavía no forma parte obligatoria del flujo integrado de Sprint 2.

### Flujo público actual

```text
Frontend
   │
   │ POST /api/v1/documents
   │
   ├─ file
   ├─ profile
   ├─ niche
   ├─ detail_level
   └─ learning_objective?
   │
   ▼
BackendAPI
   │
   ├─ validación HTTP
   ├─ staging temporal
   ├─ SHA-256 / deduplicación
   ├─ metadata → SQLite
   ├─ original → OCI Object Storage
   │
   ▼
AdaptationOrchestrationService
   │
   ├─ RAGIntegrationService
   │      ├─ recupera original desde OCI
   │      └─ POST /api/v1/index
   │
   └─ FormatGenerationService
          └─ POST /api/v1/generate
                 ├─ Quiz
                 └─ Flashcards
   │
   ├─ GeneratedFormat → SQLite
   └─ chunks_used → SQLite
   │
   ▼
Respuesta de carga
   ├─ document_id
   ├─ filename
   ├─ status
   └─ duplicate
```

Cuando Frontend necesita mostrar el material generado:

```text
Frontend
   │
   │ GET /api/v1/documents/{document_id}/formats
   │
   ▼
GeneratedFormatQueryService
   │
   ▼
SQLite
   │
   ▼
Quiz + Flashcards
```

### Flujo de estados del documento

Durante una carga nueva:

```text
RECEIVED
   ↓
VALIDATED
   ↓
STORING
   ↓
STORED
   ↓
INDEXING
   ↓
INDEXED
```

Estados de fallo disponibles:

```text
VALIDATION_FAILED
STORAGE_FAILED
INDEXING_FAILED
```

`INDEXED` expresa exclusivamente que la indexación del documento finalizó correctamente.

No debe interpretarse como:

```text
generación en progreso
formatos disponibles
adaptación completada sin errores
```

La generación de formatos tiene estados propios y no se mezcla con `DocumentStatus`.

Por ello es válido que un documento permanezca:

```text
DocumentStatus = INDEXED
```

mientras sus formatos se encuentren, por ejemplo, en:

```text
quiz        = failed
flashcards  = failed
```

En ese caso, `GET /documents/{document_id}/formats` expone el estado agregado `error` sin alterar el estado correcto de indexación del documento.

## Endpoints públicos actuales

### Salud

```http
GET /api/v1/health
```

### Cargar y procesar documento

```http
POST /api/v1/documents
Content-Type: multipart/form-data
```

Campos:

```text
file                 requerido
profile              requerido
niche                requerido
detail_level         requerido
learning_objective   opcional
```

Formatos de archivo soportados:

```text
.pdf
.md
.txt
```

Flujo ejecutado por una única solicitud:

```text
validar
→ registrar
→ almacenar en OCI
→ indexar
→ generar Quiz + Flashcards
→ persistir formatos
→ responder metadata del documento
```

Ejemplo con `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/documents" \
  -F "file=@manual.txt;type=text/plain" \
  -F "profile=intermediate" \
  -F "niche=backend" \
  -F "detail_level=detailed" \
  -F "learning_objective=Comprender los conceptos principales"
```

Respuesta de documento nuevo:

```http
HTTP/1.1 201 Created
```

```json
{
  "document_id": "doc_123",
  "filename": "manual.txt",
  "status": "indexed",
  "duplicate": false
}
```

Respuesta de contenido duplicado procesado:

```http
HTTP/1.1 200 OK
```

```json
{
  "document_id": "doc_123",
  "filename": "manual.txt",
  "status": "indexed",
  "duplicate": true
}
```

La respuesta **no contiene `formats`**. Frontend debe usar el endpoint de consulta de formatos cuando necesite mostrar Quiz o Flashcards.

Errores principales:

| HTTP | Caso |
|---:|---|
| `400` | Documento vacío o inválido |
| `409` | Estado del documento incompatible con la adaptación |
| `413` | Archivo supera el tamaño máximo permitido |
| `415` | Extensión o MIME type no soportado |
| `422` | Faltan parámetros obligatorios o el contexto pedagógico es inválido |
| `502` | Fallo de OCI, recuperación, RAG, Agentes o contrato externo |

> El endpoint es síncrono. Frontend espera la finalización del procesamiento antes de recibir una respuesta exitosa. El seguimiento por pasos/progreso en tiempo real no forma parte del contrato actual.

### Listar documentos

```http
GET /api/v1/documents
```

Ejemplo:

```json
{
  "documents": [
    {
      "document_id": "doc_123",
      "filename": "manual.pdf",
      "status": "indexed",
      "content_type": "application/pdf",
      "size_bytes": 1024,
      "created_at": "2026-10-01T12:00:00Z",
      "updated_at": "2026-10-01T12:05:00Z"
    }
  ]
}
```

El listado expone metadata de biblioteca y no incluye contenidos generados.

### Consultar detalle de documento

```http
GET /api/v1/documents/{document_id}
```

Ejemplo:

```json
{
  "document_id": "doc_123",
  "filename": "manual.pdf",
  "status": "indexed",
  "content_type": "application/pdf",
  "size_bytes": 1024,
  "created_at": "2026-10-01T12:00:00Z",
  "updated_at": "2026-10-01T12:05:00Z",
  "title": null,
  "summary": null,
  "estimated_time": null
}
```

Los campos:

```text
title
summary
estimated_time
```

están preparados para metadata enriquecida futura y actualmente pueden permanecer en `null`.

`formats_status` no forma parte de este contrato. La única fuente de verdad para disponibilidad y estado de Quiz y Flashcards es `/formats`.

### Consultar formatos

```http
GET /api/v1/documents/{document_id}/formats
```

Ejemplo con formatos disponibles:

```json
{
  "document_id": "doc_123",
  "status": "ready",
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_1",
      "status": "success",
      "content": {
        "title": "Quiz",
        "instructions": "Seleccione la respuesta correcta.",
        "questions": [
          {
            "question_id": "q1",
            "question": "Pregunta",
            "options": [
              "Opción A",
              "Opción B"
            ],
            "correct_answer": "Opción A",
            "explanation": "Explicación"
          }
        ]
      },
      "error_message": null
    },
    "flashcards": {
      "format_id": "fmt_flashcards_1",
      "status": "success",
      "content": {
        "title": "Flashcards",
        "instructions": "Revise cada tarjeta.",
        "cards": [
          {
            "card_id": "card_1",
            "front": "Concepto",
            "back": "Explicación"
          }
        ]
      },
      "error_message": null
    }
  }
}
```

### Endpoint de adaptación

No existe un endpoint público:

```text
POST /api/v1/adaptations
```

La adaptación educativa es una operación interna ejecutada desde `POST /api/v1/documents`.

---

## Manejo de errores del flujo integrado

La API traduce explícitamente excepciones de aplicación e integración.

Casos relevantes:

```text
DocumentNotFoundError
FormatGenerationDocumentNotFoundError
    → 404

AdaptationDocumentStateError
DocumentNotStoredError
DocumentIndexingStateError
DocumentNotReadyForGenerationError
    → 409

DocumentRetrievalError
RAGIntegrationError
FormatGenerationIntegrationError
FormatGenerationContractError
    → 502
```

### Fallos atómicos informados válidamente por Agentes

Si Agentes responde correctamente a nivel de integración pero un formato retorna:

```text
failed
no_results
```

BackendAPI persiste ese resultado como parte del historial.

Estos resultados no se convierten automáticamente en un error HTTP del documento. El estado final de los formatos se consulta mediante:

```text
GET /api/v1/documents/{document_id}/formats
```

Por ello, un documento puede permanecer `INDEXED` aunque uno de sus formatos tenga resultado `failed` o `no_results`.

### Fallo de integración o incumplimiento de contrato después de indexar

Si el documento ya quedó `INDEXED` pero ocurre uno de estos casos:

```text
AgentsError
FormatGenerationContractError
```

`FormatGenerationService` persiste un intento `FAILED` por cada formato solicitado antes de propagar el error.

El flujo observable queda:

```text
indexación
    ↓
INDEXED
    ↓
generación
    ↓
falla integración o contrato
    ↓
quiz = FAILED
flashcards = FAILED
    ↓
POST /documents = 502
```

Posteriormente:

```text
GET /documents/{document_id}
→ status = indexed
```

y:

```text
GET /documents/{document_id}/formats
→ status = error
```

De esta forma, `INDEXED` conserva su significado correcto y el fallo posterior queda representado por el historial de `GeneratedFormat`.

El reintento explícito de generación después de este tipo de fallo no forma parte del alcance actual y puede refinarse en un Sprint posterior.

## Stack

| Componente | Tecnología |
|---|---|
| API | FastAPI |
| Servidor | Uvicorn |
| Validación | Pydantic v2 |
| Configuración | Pydantic Settings |
| Uploads | python-multipart |
| Cliente HTTP interno | httpx |
| Staging temporal | Sistema de archivos local |
| Persistencia de negocio | SQLite |
| Persistencia futura posible | PostgreSQL / Supabase mediante nuevos adapters |
| Object Storage | OCI Object Storage |
| SDK Cloud | OCI Python SDK |
| RAG / Vector Store externo | Servicio Agentes/RAG |
| Testing | pytest / httpx |
| Calidad | Ruff |

Python soportado:

```text
Python >= 3.11
```

---

## Estructura actual

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── adaptation_execution.py
│   │   ├── dependencies.py
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── health.py
│   │           └── documents.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── adaptation.py
│   │   ├── document.py
│   │   └── generated_format.py
│   ├── domain/
│   │   ├── document.py
│   │   ├── enums.py
│   │   ├── generated_content.py
│   │   ├── generated_format.py
│   │   └── format_evaluation.py
│   ├── application/
│   │   ├── adaptation_orchestration_service.py
│   │   ├── document_service.py
│   │   ├── rag_integration_service.py
│   │   ├── format_generation_service.py
│   │   ├── generated_format_query_service.py
│   │   └── format_evaluation_service.py
│   ├── ports/
│   │   ├── document_repository_port.py
│   │   ├── temporary_storage_port.py
│   │   ├── object_storage_port.py
│   │   ├── rag_port.py
│   │   ├── agents_port.py
│   │   ├── generated_format_repository_port.py
│   │   ├── format_evaluation_repository_port.py
│   │   └── data_ia_port.py
│   ├── infrastructure/
│   │   ├── integrations/
│   │   │   ├── http_rag_adapter.py
│   │   │   └── http_agents_adapter.py
│   │   ├── persistence/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── repository_factory.py
│   │   │   ├── sqlite_document_repository_adapter.py
│   │   │   ├── sqlite_generated_format_repository_adapter.py
│   │   │   └── sqlite_format_evaluation_repository_adapter.py
│   │   └── storage/
│   │       ├── local_temporary_storage_adapter.py
│   │       └── oci_object_storage_adapter.py
│   └── core/
│       ├── config.py
│       ├── exceptions.py
│       ├── logging.py
│       └── hashing.py
├── tests/
│   ├── conftest.py
│   ├── fakes.py
│   ├── integration/
│   │   ├── test_agents_generation_integration.py
│   │   ├── test_document_formats_api.py
│   │   └── test_documents_api.py
│   └── unit/
│       ├── test_adaptation_orchestration_service.py
│       ├── test_application_wiring.py
│       ├── test_database.py
│       ├── test_document_domain.py
│       ├── test_document_indexing_state.py
│       ├── test_document_listing.py
│       ├── test_document_repository.py
│       ├── test_document_schemas.py
│       ├── test_document_service.py
│       ├── test_documents_list_api.py
│       ├── test_format_generation_service.py
│       ├── test_generated_content.py
│       ├── test_generated_format_query_service.py
│       ├── test_generated_format_repository.py
│       ├── test_hashing.py
│       ├── test_http_agents_adapter.py
│       ├── test_http_rag_adapter.py
│       ├── test_local_temporary_storage_adapter.py
│       ├── test_oci_object_storage_adapter.py
│       ├── test_persistence_models.py
│       ├── test_rag_integration_service.py
│       └── test_repository_factory.py
├── storage/
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

El scaffolding anterior de `Process` fue eliminado porque no representaba un caso de uso persistido ni era necesario para el flujo real de Sprint 2.

---

## Configuración local

Crear `.env` a partir de `.env.example`.

Variables actuales:

```env
# --- Aplicación ---
PROJECT_NAME="NuevaMente API"
DESCRIPTION="Backend API de NuevaMente para gestión de documentos y adaptación educativa asistida por IA."
VERSION="0.1.0"
ENVIRONMENT=local
DEBUG=true

# --- API ---
API_V1_PREFIX=/api/v1

# --- Servidor ---
HOST=0.0.0.0
PORT=8000

# --- CORS ---
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500

# --- Documentos / almacenamiento temporal ---
MAX_UPLOAD_SIZE_MB=10
UPLOAD_DIR=storage/uploads

# --- Base de datos ---
DATABASE_URL=sqlite:///storage/nuevamente.db

# --- OCI Object Storage ---
OCI_NAMESPACE=
OCI_BUCKET_NAME=
OCI_REGION=
OCI_CONFIG_FILE=~/.oci/config
OCI_CONFIG_PROFILE=DEFAULT

# --- RAG ---
RAG_BASE_URL=http://localhost:8001
RAG_INDEX_PATH=/api/v1/index
RAG_TIMEOUT_SECONDS=30

# --- Agentes ---
AGENTS_BASE_URL=http://localhost:8001
AGENTS_GENERATE_PATH=/api/v1/generate
AGENTS_TIMEOUT_SECONDS=60
```

En despliegues Docker pueden utilizarse nombres internos de servicio, por ejemplo:

```env
RAG_BASE_URL=http://agents:8001
AGENTS_BASE_URL=http://agents:8001
```

RAG y generación mantienen configuraciones independientes aunque actualmente puedan residir en el mismo servicio.

Nunca versionar credenciales, claves privadas ni `.env` con datos sensibles.

---

## Ejecución local

### BackendAPI

Desde `backend/`:

```bash
python -m venv .venv
```

Activar el entorno virtual.

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements-dev.txt
```

Levantar BackendAPI:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### RAG / Agentes para pruebas integradas

En el repositorio actual, RAG y Agentes pueden ejecutarse en el puerto `8001`.

Desde la raíz del repositorio, utilizando el entorno correspondiente a Agentes:

```powershell
.\.venv-agentes\Scripts\Activate.ps1
python -m uvicorn agentes.api:app --host 127.0.0.1 --port 8001
```

Swagger de Agentes:

```text
http://127.0.0.1:8001/docs
```

> El servicio de Agentes utilizado durante las validaciones actuales ejecuta indexación/retrieval reales, mientras que el contenido generado por el agente continúa usando la simulación existente en ese módulo.

---

## Tests y calidad

Ejecutar desde `backend/`:

```bash
python -m ruff check app tests
python -m pytest
```

Última validación local del flujo actual:

```text
Ruff: All checks passed!
Pytest: 121 passed
```

La suite cubre, entre otros:

- carga de PDF, Markdown y TXT;
- validación de extensión y MIME;
- documentos vacíos;
- límite máximo de archivo;
- staging temporal;
- SHA-256 y deduplicación;
- persistencia de metadata;
- relación `document_id → oci_object_name`;
- almacenamiento y recuperación mediante Object Storage;
- compensación ante inconsistencia OCI/BD;
- transiciones de indexación;
- reintentos desde `INDEXING_FAILED`;
- multipart HTTP hacia RAG;
- timeouts y errores HTTP de RAG;
- validación de `document_id` devuelto por RAG;
- `AgentsPort`;
- `HTTPAgentsAdapter`;
- request canónico hacia `/api/v1/generate`;
- `learning_objective` opcional;
- Quiz canónico;
- Flashcards canónicas;
- mapeo `sources_used → ChunkEvidence`;
- estado `no_results`;
- errores HTTP de Agentes;
- timeouts de Agentes;
- respuestas incompatibles de Agentes;
- contenido canónico inválido;
- inicialización de servicios en el lifespan;
- `AdaptationOrchestrationService`;
- ejecución automática de indexación desde `POST /documents`;
- generación automática de Quiz y Flashcards;
- persistencia SQLite de los resultados recibidos vía HTTP;
- lectura posterior de esos resultados desde SQLite;
- contexto pedagógico de generación;
- persistencia y reconstrucción de `chunks_used`;
- historial de generaciones;
- persistencia de generaciones fallidas;
- persistencia de intentos `FAILED` ante errores de integración con Agentes;
- persistencia de intentos `FAILED` ante incumplimientos del contrato de Agentes;
- semántica de `INDEXED` separada del estado de generación;
- `INDEXING` como único estado de documento que produce `formats.status = processing` sin historial;
- `INDEXED` sin intentos de generación como `formats.status = pending`;
- rechazo de `format_id` duplicado;
- rechazo de referencias a documentos inexistentes;
- consulta pública de formatos;
- estados `pending`, `processing`, `ready`, `partial` y `error`;
- conservación de éxito previo frente a reintento fallido;
- contrato de detalle de documento;
- separación entre listado, detalle y formatos;
- ausencia de `/api/v1/adaptations` como endpoint público;
- respuesta de `POST /documents` sin contenidos de formatos;
- disponibilidad posterior de Quiz y Flashcards mediante `/formats`.

---

## Validación end-to-end real

El flujo integrado fue validado localmente utilizando servicios reales de infraestructura del proyecto.

### Happy path

Se comprobó:

```text
POST /api/v1/documents
    ↓
SQLite
    ↓
OCI Object Storage
    ↓
recuperación del original desde OCI
    ↓
BackendAPI → POST Agentes/RAG /api/v1/index
    ↓
extracción + limpieza + chunking + Vector Store
    ↓
BackendAPI → POST Agentes /api/v1/generate
    ↓
retrieval
    ↓
Quiz + Flashcards
    ↓
validación de contratos
    ↓
persistencia de GeneratedFormat + chunks_used en SQLite
    ↓
respuesta de metadata a Frontend
```

Respuesta validada de carga:

```json
{
  "document_id": "doc_1d587f6a1399430080c33747a226f3dc",
  "filename": "e2e_contract.txt",
  "status": "indexed",
  "duplicate": true
}
```

La respuesta no incluyó `formats`.

Posteriormente se consultó:

```text
GET /api/v1/documents/{document_id}/formats
```

obteniendo:

```text
status = ready
quiz = success
flashcards = success
```

También se comprobó que:

- los formatos permanecen persistidos después de finalizar el `POST`;
- la biblioteca muestra el documento con estado `indexed`;
- `/api/v1/adaptations` no aparece en OpenAPI;
- una llamada directa a `/api/v1/adaptations` retorna `404 Not Found`.

### Fallo de generación después de indexación

También se reprodujo de forma end-to-end el caso reportado durante la revisión de la PR #41.

La indexación permaneció operativa y se configuró deliberadamente un endpoint de generación no disponible para provocar el fallo después de que el documento quedara indexado.

Flujo comprobado:

```text
POST /api/v1/documents
    ↓
SQLite + OCI
    ↓
RAG /index
    ↓
INDEXED
    ↓
Agentes /generate
    ↓
fallo de conexión
    ↓
persistencia de intentos FAILED
    ↓
HTTP 502
```

Se verificó que el documento conservó correctamente:

```text
status = indexed
```

y que:

```text
GET /api/v1/documents/{document_id}/formats
```

retornó:

```text
status = error
quiz = failed
flashcards = failed
```

Cada formato conservó además su `format_id`, `content = null` y un `error_message` explícito.

Esta validación confirma que `INDEXED` no se utiliza como sinónimo de procesamiento de formatos y que un fallo posterior de generación queda representado en el historial de `GeneratedFormat`.

La generación textual del módulo de Agentes continúa marcada como simulación. El transporte HTTP, almacenamiento, OCI, indexación, Vector Store, retrieval, persistencia y contratos de BackendAPI sí fueron ejercitados de forma real.

## Semántica del flujo actual para Frontend

El contrato actual separa explícitamente **procesamiento** de **consulta de contenido**.

### Durante la carga

Frontend ejecuta:

```text
POST /api/v1/documents
```

Backend completa internamente:

```text
persistencia
→ almacenamiento
→ indexación
→ generación
→ persistencia de formatos
```

Frontend recibe únicamente la metadata final del documento.

### Al mostrar material educativo

Frontend ejecuta:

```text
GET /api/v1/documents/{document_id}/formats
```

Ese endpoint es la fuente de verdad para:

- disponibilidad de Quiz;
- disponibilidad de Flashcards;
- contenido generado;
- estado global de formatos;
- errores atómicos de generación;
- fallos de integración de generación persistidos como `FAILED`.

### Progreso por pasos

El seguimiento visual de pasos como:

```text
almacenando
indexando
generando
```

no forma parte del alcance implementado actualmente.

El flujo público es síncrono, por lo que Frontend recibe el `document_id` después de finalizar el procesamiento. Un futuro seguimiento de progreso en tiempo real requeriría un contrato de procesamiento independiente y, probablemente, ejecución asíncrona o consulta periódica de estado.

No se deben mezclar esos futuros estados de proceso con `DocumentStatus`, ya que documento y generación mantienen ciclos de vida distintos.

---

## Data/IA y pendientes complementarios

### Integración Data/IA

El modelo interno está preparado mediante:

```text
DataIAPort
FormatEvaluationService
FormatEvaluationRepositoryPort
```

La integración HTTP concreta dependerá del endpoint funcional disponible en Data/IA.

Su conexión al pipeline no es obligatoria para completar el flujo actual de Sprint 2.

### Metadata enriquecida

Los campos:

```text
title
summary
estimated_time
```

ya forman parte del contrato de detalle, pero actualmente permanecen en `null` mientras no exista una fuente real que los calcule.

### Seguimiento de procesamiento

Un futuro requerimiento de progreso por pasos debería modelarse como una responsabilidad separada del documento y de los formatos.

Una posible evolución podría contemplar conceptos como:

```text
ProcessingStep
ProcessingStepStatus
ProcessingStatusService
```

sin ampliar artificialmente `DocumentStatus` con estados de generación.

### Persistencia alternativa

SQLite es el motor actual de desarrollo. Un motor adicional puede incorporarse mediante nuevos adapters sin modificar los casos de uso.

---

## Lineamientos de desarrollo

- Modularizar el código en componentes y funciones con una única responsabilidad clara.
- Mantener una estructura de carpetas organizada por responsabilidades.
- Separar lógica HTTP, aplicación, dominio, persistencia e integraciones externas.
- Evitar dependencias directas desde `application/` hacia implementaciones de `infrastructure/`.
- Usar Ports como contratos estables.
- Usar Adapters para tecnologías externas.
- Mantener contratos explícitos de entrada, salida, tipos y errores.
- Utilizar nombres descriptivos y evitar duplicación de lógica.
- Manejar errores de forma explícita.
- Priorizar código simple, claro y mantenible.
- Documentar funciones, módulos y decisiones técnicas relevantes.
- Acompañar funcionalidades con pruebas automatizadas.
- Mantener `document_id` como identificador canónico entre Backend, OCI, RAG, Agentes, formatos y evaluaciones.
- No permitir que Backend acceda directamente al Vector Store de Agentes.
- No permitir que Agentes acceda directamente a OCI ni a la BD de negocio.
- Mantener configuraciones de RAG y Agentes desacopladas aunque compartan despliegue.
- No versionar credenciales ni configuración sensible.

---

## Resumen del flujo Sprint 2

```text
Frontend
   ↓
POST /api/v1/documents
   ↓
BackendAPI
   ├── validación
   ├── SHA-256 / deduplicación
   ├── SQLite
   └── OCI Object Storage
   ↓
AdaptationOrchestrationService
   ├── RAGIntegrationService
   │      ↓
   │   POST /api/v1/index
   │      ↓
   │   INDEXED
   │
   └── FormatGenerationService
          ↓
       POST /api/v1/generate
          ↓
       Quiz + Flashcards
          ↓
       SQLite
   ↓
Respuesta de metadata

Frontend
   ↓
GET /api/v1/documents/{document_id}/formats
   ↓
Quiz + Flashcards persistidos
```

El objetivo arquitectónico se mantiene: **Frontend conoce BackendAPI; BackendAPI orquesta el producto; RAG/Agentes resuelve recuperación y generación; Data/IA permanece desacoplado para evaluación.**
