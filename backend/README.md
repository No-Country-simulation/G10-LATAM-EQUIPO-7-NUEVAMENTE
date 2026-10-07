# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI**, **Pydantic v2**, **SQLite** y **OCI Object Storage**.

BackendAPI actúa como **orquestador del producto**: recibe las solicitudes del Frontend, administra la metadata y el ciclo de vida de los documentos, persiste los archivos originales, coordina la indexación con RAG/Agentes, solicita la generación de material educativo y conserva los resultados para su consulta posterior.

BackendAPI **no implementa internamente** extracción de texto, limpieza, chunking, embeddings, Vector Store, retrieval semántico, prompts ni generación mediante LLM. Tampoco ejecuta directamente la evaluación de calidad de Data/IA. Estas responsabilidades permanecen desacopladas mediante Ports y Adapters.

El frontend se encuentra en [`../frontend`](../frontend).

> Los comandos de este documento se ejecutan desde `backend/`, salvo que se indique lo contrario.

---

## Estado actual

El flujo principal se encuentra integrado de extremo a extremo desde BackendAPI y, a partir de Sprint 3, **la indexación RAG y la generación de formatos tienen ciclos de ejecución separados**.

Actualmente están implementados:

### Documentos y almacenamiento

- API FastAPI y configuración centralizada.
- Endpoint de salud.
- `POST /api/v1/documents` como **única entrada pública para cargar, almacenar e indexar un documento y programar su generación pedagógica**.
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

### Orquestación de adaptación: indexación y generación separadas

Después de almacenar un documento, BackendAPI utiliza internamente:

```text
AdaptationOrchestrationService
```

En Sprint 3, el orquestador separa tres responsabilidades:

```text
ensure_document_indexed()
        ↓
indexación RAG síncrona

prepare_default_formats()
        ↓
registro persistente de Quiz y Flashcards en processing

complete_default_generation()
        ↓
generación real en segundo plano
```

#### 1. Indexación síncrona

`ensure_document_indexed()`:

1. consulta el estado actual del documento;
2. indexa cuando el documento está `STORED` o `INDEXING_FAILED`;
3. evita reindexar cuando ya está `INDEXED`;
4. solo permite responder exitosamente al `POST /documents` cuando el documento ya alcanzó `INDEXED`.

#### 2. Preparación de formatos antes de responder

Después de que el documento queda `INDEXED`, BackendAPI ejecuta:

```text
prepare_default_formats()
```

Esta etapa:

- crea un intento para `quiz`;
- crea un intento para `flashcards`;
- persiste ambos con estado `processing`;
- asigna un `format_id` estable a cada intento;
- conserva el contexto pedagógico de generación;
- ocurre **antes** de registrar la tarea de segundo plano y antes de responder al Frontend.

Por tanto, cuando `POST /documents` responde exitosamente, los formatos solicitados ya existen en persistencia y pueden ser observados por Frontend mediante polling.

#### 3. Generación en segundo plano

Luego BackendAPI registra una `BackgroundTask` de FastAPI:

```text
complete_default_generation()
```

La tarea:

1. recibe los intentos persistidos en `processing`;
2. invoca `POST /api/v1/generate` en Agentes;
3. valida el contrato recibido;
4. actualiza los mismos `format_id`;
5. termina cada intento en uno de estos estados:

```text
success
failed
no_results
```

El flujo por formato es:

```text
processing
    ↓
success | failed | no_results
```

No se crea una nueva fila para completar un intento iniciado por la misma generación. El mismo `format_id` se conserva durante la transición.

#### Formatos automáticos

BackendAPI solicita automáticamente:

```text
quiz
flashcards
```

El endpoint público independiente:

```text
POST /api/v1/adaptations
```

**no existe**.

La adaptación permanece como un caso de uso interno iniciado desde `POST /api/v1/documents`.

---
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

Backend genera el `document_id` y decide internamente que la adaptación produce Quiz y Flashcards.

### Respuesta de carga

`POST /api/v1/documents` mantiene síncronas las etapas necesarias para garantizar que el documento está disponible en RAG:

```text
validación
→ registro
→ almacenamiento
→ indexación RAG
→ INDEXED
→ persistencia de Quiz/Flashcards en processing
→ registrar BackgroundTask
→ responder al Frontend
```

La generación mediante Agentes ocurre después:

```text
background
→ POST /api/v1/generate
→ actualizar mismos format_id
→ success | failed | no_results
```

Una respuesta exitosa significa:

- el documento fue almacenado;
- el documento fue indexado;
- Quiz y Flashcards fueron registrados como intentos activos;
- la generación LLM puede continuar en segundo plano.

No significa que los formatos ya estén terminados.

Ejemplo:

```json
{
  "document_id": "doc_123",
  "filename": "manual.pdf",
  "status": "indexed",
  "duplicate": false
}
```

Para un documento nuevo:

```text
HTTP 201 Created
```

Para contenido previamente registrado:

```text
HTTP 200 OK
```

con:

```json
{
  "duplicate": true
}
```

Un contenido duplicado reutiliza el mismo `document_id` y no vuelve a almacenar el archivo original en OCI.

---
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

La indexación continúa siendo parte del contrato síncrono de `POST /documents`. Por ello, un fallo de OCI, recuperación o RAG puede impedir la respuesta exitosa del POST.

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

`AGENTS_TIMEOUT_SECONDS` controla el timeout de la llamada de generación y es independiente del timeout de RAG.

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

BackendAPI trabaja públicamente con:

```text
quiz
flashcards
```

`FormatGenerationService` divide el lifecycle en dos operaciones.

#### `prepare_generation(...)`

Responsabilidades:

- validar que el documento exista;
- exigir que esté `INDEXED`;
- validar el contexto pedagógico;
- crear un intento por formato;
- asignar un `format_id`;
- persistir cada intento como `processing`.

#### `complete_generation(...)`

Responsabilidades:

- recibir intentos previamente creados;
- exigir que estén en `processing`;
- validar que pertenezcan al mismo documento y contexto;
- construir la solicitud hacia Agentes;
- invocar `AgentsPort`;
- validar `document_id`;
- validar exactamente los formatos solicitados;
- rechazar resultados duplicados;
- actualizar cada intento sobre el mismo `format_id`;
- conservar chunks utilizados como evidencia;
- terminar en `success`, `failed` o `no_results`.

Estados soportados por formato:

```text
processing
success
failed
no_results
```

#### Fallos de integración

Si Agentes falla por conexión, HTTP o timeout:

```text
processing
    ↓
failed
```

para todos los intentos del lote.

#### Fallos de contrato

Si Agentes devuelve:

- otro `document_id`;
- formatos incompletos;
- formatos duplicados;
- estados incompatibles;
- contenido inválido;

BackendAPI marca los intentos en `failed` y produce `FormatGenerationContractError`.

Estos fallos **no modifican `DocumentStatus.INDEXED`**.

---
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

Frontend consulta:

```text
GET /api/v1/documents/{document_id}/formats
```

Estados agregados:

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
| `pending` | El documento existe pero todavía no hay intentos persistidos para exponer. |
| `processing` | Existe al menos un intento vigente en `processing`, o el documento aún está indexándose sin historial de formatos. |
| `ready` | Quiz y Flashcards vigentes están en `success`. |
| `partial` | No hay intentos activos y existe al menos un formato exitoso, pero no todos. |
| `error` | No hay intentos activos ni formatos exitosos vigentes. |

#### Durante generación

Ejemplo:

```json
{
  "document_id": "doc_123",
  "status": "processing",
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_1",
      "status": "processing",
      "content": null,
      "error_message": null
    },
    "flashcards": {
      "format_id": "fmt_flashcards_1",
      "status": "processing",
      "content": null,
      "error_message": null
    }
  }
}
```

Frontend debe continuar haciendo polling mientras:

```text
status = processing
```

#### Después de éxito

```json
{
  "document_id": "doc_123",
  "status": "ready",
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_1",
      "status": "success",
      "content": {},
      "error_message": null
    },
    "flashcards": {
      "format_id": "fmt_flashcards_1",
      "status": "success",
      "content": {},
      "error_message": null
    }
  }
}
```

#### Después de fallo total

```json
{
  "document_id": "doc_123",
  "status": "error",
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_1",
      "status": "failed",
      "content": null,
      "error_message": "Agentes no pudo generar los formatos del documento doc_123."
    },
    "flashcards": {
      "format_id": "fmt_flashcards_1",
      "status": "failed",
      "content": null,
      "error_message": "Agentes no pudo generar los formatos del documento doc_123."
    }
  }
}
```

`DocumentStatus.INDEXED` sigue significando únicamente:

```text
la indexación RAG terminó correctamente
```

No representa el estado de generación.

---

#### Selección del formato vigente

`GeneratedFormatQueryService` selecciona un resultado vigente por tipo.

Regla actual:

```text
si existe un intento processing
→ se expone el processing más reciente

si no existe processing y existe un success histórico
→ se expone el success más reciente

si nunca existió success
→ se expone el intento terminal más reciente
```

Esto permite:

- hacer visible una generación activa;
- conservar contenido válido previo cuando un reintento posterior ya terminó fallando;
- mantener separado el historial de intentos del contenido vigente.

---
### Persistencia

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

- persistir nuevos intentos mediante `create()`;
- actualizar intentos existentes mediante `update()`;
- recuperar mediante `find_by_id(format_id)`;
- recuperar historial mediante `find_by_document_id(document_id)`;
- conservar múltiples generaciones del mismo tipo;
- persistir intentos `processing` y resultados `success`, `failed` o `no_results`;
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

Un intento conserva el mismo `format_id` durante la transición:

```text
processing → success | failed | no_results
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
- `GeneratedFormatNotFoundError`
- `GeneratedFormatDocumentNotFoundError`
- `GeneratedFormatRepositoryError`

La inicialización de SQLite incluye una migración idempotente para bases anteriores cuyo `CHECK` de `generated_formats.status` no incluía `processing`. La migración conserva formatos existentes, relaciones con `format_evaluations`, recrea los índices y valida integridad referencial mediante `foreign_key_check`.
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
- todavía no forma parte obligatoria del flujo integrado actual.

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
   └─ original → OCI Object Storage
   │
   ▼
ensure_document_indexed()
   │
   ▼
POST /api/v1/index
   │
   ▼
INDEXED
   │
   ▼
prepare_default_formats()
   ├─ quiz = processing
   └─ flashcards = processing
   │
   ▼
registrar BackgroundTask
   │
   ▼
Respuesta de carga
   │
   └──────────── background ─────────────┐
                                         ▼
                         complete_default_generation()
                                         │
                                         ▼
                            POST /api/v1/generate
                              ├─ Quiz
                              └─ Flashcards
                                         │
                                         ▼
                       mismos format_id → estado terminal
```

Frontend consulta:

```text
GET /api/v1/documents/{document_id}/formats
```

y hace polling mientras:

```text
status = processing
```

---
### Flujo de estados del documento

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

Estados de fallo:

```text
VALIDATION_FAILED
STORAGE_FAILED
INDEXING_FAILED
```

La generación no agrega estados a `DocumentStatus`.

Es válido tener:

```text
DocumentStatus = INDEXED
```

mientras:

```text
quiz        = processing
flashcards  = processing
```

o:

```text
quiz        = failed
flashcards  = failed
```

---
## Endpoints públicos actuales

### Salud

```http
GET /api/v1/health
```

### Cargar e indexar documento

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

Flujo ejecutado antes de responder:

```text
validar
→ registrar
→ almacenar en OCI
→ indexar
→ alcanzar INDEXED
→ persistir Quiz y Flashcards en processing
→ registrar BackgroundTask
→ responder metadata del documento
```

Después de responder al cliente:

```text
background task
→ solicitar Quiz + Flashcards a Agentes
→ validar resultados
→ actualizar los mismos format_id
→ success | failed | no_results
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

Respuesta de contenido duplicado:

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

Errores principales de la etapa síncrona:

| HTTP | Caso |
|---:|---|
| `400` | Documento vacío o inválido |
| `409` | Estado del documento incompatible con la indexación |
| `413` | Archivo supera el tamaño máximo permitido |
| `415` | Extensión o MIME type no soportado |
| `422` | Faltan parámetros obligatorios o el contexto pedagógico es inválido |
| `502` | Fallo de OCI, recuperación del original o indexación RAG |

> El endpoint es síncrono hasta completar la indexación. Los errores de generación que ocurren después no modifican la respuesta ya enviada; su resultado se consulta mediante `/formats`.
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

`formats_status` no forma parte de este contrato. La fuente de verdad para disponibilidad y estado de Quiz y Flashcards es `/formats`.

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

La adaptación educativa es una operación interna iniciada desde `POST /api/v1/documents`.

---

## Manejo de errores del flujo integrado

### Durante almacenamiento e indexación

```text
DocumentNotFoundError
    → 404

AdaptationDocumentStateError
DocumentNotStoredError
DocumentIndexingStateError
    → 409

DocumentRetrievalError
RAGIntegrationError
    → 502
```

### Preparación de generación

El registro de intentos `processing` ocurre antes de responder.

Un fallo de persistencia en esta etapa impide programar una generación que Frontend no pueda observar correctamente.

### Generación en background

Casos relevantes:

```text
FormatGenerationAttemptStateError
FormatGenerationIntegrationError
FormatGenerationContractError
GeneratedFormatRepositoryError
```

`execute_background_generation()` registra explícitamente el error.

Cuando Agentes falla normalmente por timeout, conexión, error HTTP o contrato:

```text
processing → failed
```

El documento permanece:

```text
INDEXED
```

---
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

El scaffolding anterior de `Process` fue eliminado porque no representaba un caso de uso persistido ni era necesario para el flujo real.

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

El módulo actual de Agentes contiene integración con Gemini y requiere la configuración correspondiente para ejercer generación real. Una prueba exclusivamente de indexación puede requerir igualmente que las variables de entorno de Agentes estén presentes durante el import del módulo.

---

## Tests y calidad

Ejecutar desde `backend/`:

```bash
python -m ruff check .
python -m pytest -q
git diff --check
```

Última validación local de esta tarjeta de Sprint 3:

```text
Ruff: All checks passed!
Pytest: suite completa OK
Git diff --check: OK
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
- separación de `ensure_document_indexed()`, `prepare_default_formats()` y `complete_default_generation()`;
- indexación síncrona desde `POST /documents`;
- generación automática de Quiz y Flashcards como tarea en segundo plano;
- persistencia SQLite de los resultados recibidos vía HTTP;
- lectura posterior de esos resultados desde SQLite;
- contexto pedagógico de generación;
- persistencia y reconstrucción de `chunks_used`;
- historial de generaciones;
- persistencia de intentos `processing` antes de llamar a Agentes;
- actualización del mismo `format_id` a un estado terminal;
- persistencia de intentos `FAILED` ante errores de integración con Agentes;
- persistencia de intentos `FAILED` ante incumplimientos del contrato de Agentes;
- migración SQLite del `CHECK` de estados sin pérdida de formatos ni evaluaciones;
- semántica de `INDEXED` separada del estado de generación;
- `INDEXING` sin historial como `formats.status = processing`;
- intentos de generación activos como `formats.status = processing`;
- `INDEXED` sin intentos persistidos como `formats.status = pending`;
- rechazo de `format_id` duplicado;
- rechazo de referencias a documentos inexistentes;
- consulta pública de formatos;
- estados `pending`, `processing`, `ready`, `partial` y `error`;
- prioridad de un intento `processing` sobre un éxito histórico mientras está activo;
- conservación de éxito previo frente a reintento fallido una vez termina el reintento;
- contrato de detalle de documento;
- separación entre listado, detalle y formatos;
- ausencia de `/api/v1/adaptations` como endpoint público;
- respuesta de `POST /documents` sin contenidos de formatos;
- disponibilidad posterior de Quiz y Flashcards mediante `/formats`.

---
## Validación E2E de Sprint 3

La separación entre indexación y generación y el lifecycle de estados fueron validados funcionalmente en local.

### Configuración de la prueba

```text
BackendAPI:
http://127.0.0.1:8000

RAG:
http://127.0.0.1:8001

Mock de generación lenta:
http://127.0.0.1:8002

AGENTS_TIMEOUT_SECONDS=15
```

El mock demoró más que el timeout configurado para permitir observar `processing` antes del fallo controlado.

### 1. POST responde sin esperar la generación

Documento probado:

```text
doc_8d770ba4ddda4359836159c74cc4875c
```

Respuesta:

```json
{
  "document_id": "doc_8d770ba4ddda4359836159c74cc4875c",
  "filename": "e2e_processing_20261006202146.txt",
  "status": "indexed",
  "duplicate": false
}
```

Tiempo observado:

```text
TOTAL_TIME=0.3694516 s
```

Esto demuestra que el POST no quedó bloqueado por la generación lenta.

### 2. Estado observable durante la generación

Consulta inmediata:

```text
GET /api/v1/documents/doc_8d770ba4ddda4359836159c74cc4875c/formats
```

Resultado:

```json
{
  "document_id": "doc_8d770ba4ddda4359836159c74cc4875c",
  "status": "processing",
  "formats": {
    "quiz": {
      "format_id": "fmt_2ab0368d1a84415bb262e5815a26ff5e",
      "status": "processing",
      "content": null,
      "error_message": null
    },
    "flashcards": {
      "format_id": "fmt_cd3ec83036354918a2903526381d89f8",
      "status": "processing",
      "content": null,
      "error_message": null
    }
  }
}
```

### 3. Timeout controlado

Después del timeout:

```json
{
  "status": "error",
  "formats": {
    "quiz": {
      "format_id": "fmt_2ab0368d1a84415bb262e5815a26ff5e",
      "status": "failed",
      "content": null
    },
    "flashcards": {
      "format_id": "fmt_cd3ec83036354918a2903526381d89f8",
      "status": "failed",
      "content": null
    }
  }
}
```

Se comprobó:

```text
QUIZ MISMO ID: True
FLASHCARDS MISMO ID: True
```

Por tanto:

```text
processing → failed
```

ocurre actualizando exactamente la misma generación persistida.

### 4. Estado del documento después del fallo

La consulta:

```text
GET /api/v1/documents/doc_8d770ba4ddda4359836159c74cc4875c
```

mantuvo:

```json
{
  "status": "indexed"
}
```

### Conclusión E2E

La prueba confirma:

```text
indexación síncrona                         ✅
POST responde después de INDEXED           ✅
processing se persiste antes de responder  ✅
Frontend puede observar processing         ✅
generación no bloquea POST                  ✅
timeout de Agentes es independiente         ✅
processing termina en failed               ✅
mismo format_id se conserva                ✅
documento permanece INDEXED                ✅
```

---
## Semántica del flujo actual para Frontend

Frontend debe separar:

```text
GET /documents/{id}
→ estado del documento / indexación
```

de:

```text
GET /documents/{id}/formats
→ estado de generación
```

Flujo recomendado:

```text
POST /documents
    ↓
indexed
    ↓
GET /formats
    ↓
processing
    ↓
polling
    ↓
ready | partial | error
```

No se requiere un endpoint adicional de estado.

---
## Data/IA y pendientes complementarios

### Integración Data/IA

El modelo interno está preparado mediante:

```text
DataIAPort
FormatEvaluationService
FormatEvaluationRepositoryPort
```

La integración HTTP concreta todavía debe cablearse mediante un adapter cuando se implemente la conexión efectiva BackendAPI ↔ Data/IA.

Su conexión al pipeline no es obligatoria para completar esta primera tarjeta de Sprint 3.

### Metadata enriquecida

Los campos:

```text
title
summary
estimated_time
```

ya forman parte del contrato de detalle, pero actualmente permanecen en `null` mientras no exista una fuente real que los calcule.

### Limitación conocida: BackgroundTasks no es una cola durable

La implementación actual utiliza:

```text
FastAPI BackgroundTasks
```

Esto desacopla la latencia de generación del `POST /documents`, pero **no ofrece durabilidad ante reinicios del proceso**.

En condiciones normales:

```text
timeout
error HTTP
error de conexión
error de contrato
```

los intentos `processing` son convertidos a `failed`.

Sin embargo, si el proceso de Backend termina abruptamente mientras existe una generación activa, una `BackgroundTask` puede interrumpirse antes de alcanzar un estado terminal.

Por ello, la implementación actual **no debe interpretarse como garantía absoluta ante crash o reinicio de proceso**.

Opciones futuras:

- recuperación de intentos `processing` obsoletos;
- reconciliación al iniciar Backend;
- cola durable de trabajos;
- worker externo.

No es necesario mezclar esta mejora con el alcance actual mientras el equipo no defina explícitamente el mecanismo de recuperación.

---
### Regeneración

El endpoint explícito para regenerar formatos todavía no forma parte del contrato público actual. Su implementación debe reutilizar `FormatGenerationService`, conservar el contexto pedagógico y evitar reindexaciones innecesarias.

### Learning metadata

Pendiente incorporar una estructura a nivel de adaptación/documento:

```text
learning_metadata
├── key_concepts
├── prerequisites
└── estimated_time_minutes
```

No debe confundirse con el campo histórico `estimated_time` de metadata de documento.

### Persistencia de contenido educativo en OCI

Pendiente definir y persistir JSON estructurado de resultados educativos en OCI.

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

## Resumen del flujo actual

```text
Frontend
   ↓
POST /api/v1/documents
   ↓
BackendAPI
   ├── validar
   ├── SHA-256
   ├── SQLite
   └── OCI
   ↓
RAG /index
   ↓
INDEXED
   ↓
Quiz processing
Flashcards processing
   ↓
POST responde
   │
   └──────── background ────────┐
                                ↓
                         Agentes /generate
                                ↓
             mismos format_id → estado terminal
                                ↓
                   success | failed | no_results

Frontend
   ↓
GET /api/v1/documents/{id}/formats
   ↓
pending | processing | ready | partial | error
```

El objetivo arquitectónico se mantiene: **Frontend conoce BackendAPI; BackendAPI orquesta; RAG/Agentes resuelve recuperación y generación; Data/IA permanece desacoplado para evaluación.**
