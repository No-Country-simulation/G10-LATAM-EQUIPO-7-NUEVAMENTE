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

La carga pública ya no termina en `STORED`.

Después de almacenar el documento, BackendAPI utiliza internamente:

```text
AdaptationOrchestrationService
```

A partir de Sprint 3, el orquestador separa explícitamente dos responsabilidades:

```text
ensure_document_indexed()
        ↓
indexación RAG síncrona


generate_default_formats()
        ↓
generación de Quiz + Flashcards
```

El flujo de indexación:

1. consulta el estado actual del documento;
2. indexa cuando el documento está `STORED` o `INDEXING_FAILED`;
3. evita reindexar cuando ya está `INDEXED`;
4. solo permite responder exitosamente al `POST /documents` cuando el documento ya alcanzó `INDEXED`.

Después de completar la indexación, la API programa la generación de formatos como una **BackgroundTask de FastAPI** y responde al Frontend sin esperar a que Agentes termine `/api/v1/generate`.

Los formatos solicitados automáticamente son:

```text
quiz
flashcards
```

El endpoint público independiente `/api/v1/adaptations` **no existe**. La adaptación permanece como un caso de uso interno.

La capa API utiliza `app/api/adaptation_execution.py` para mantener separadas las dos etapas:

- `execute_indexing(...)`: ejecuta la indexación síncrona y traduce sus errores a HTTP;
- `execute_background_generation(...)`: ejecuta la generación después de la respuesta, registra fallos y deja que `FormatGenerationService` persista los intentos fallidos.

Esta separación evita mezclar lógica HTTP, lógica de orquestación y lógica de integración externa.

> La BackgroundTask no constituye una cola durable. Si el proceso de Backend se reinicia mientras una generación está ejecutándose, esa ejecución puede interrumpirse. La recuperación explícita mediante regeneración corresponde a una tarjeta posterior de Sprint 3.

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
```

Después:

```text
programar generación en background
→ responder al Frontend
```

Por tanto, una respuesta exitosa significa que el documento ya fue almacenado e indexado, **no que Quiz y Flashcards hayan terminado de generarse**.

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

Un contenido duplicado reutiliza el mismo `document_id` y no vuelve a almacenar el archivo original en OCI. Si el documento ya está `INDEXED`, la orquestación evita una reindexación innecesaria y puede programar un nuevo intento de generación, conservando el historial de formatos.

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

BackendAPI trabaja públicamente con dos formatos:

```text
quiz
flashcards
```

`generate_default_formats()` solicita ambos automáticamente.

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

Un error de comunicación con Agentes se traduce internamente mediante `FormatGenerationIntegrationError`.

Cuando la llamada a Agentes falla antes de obtener resultados válidos, BackendAPI persiste un intento fallido por cada formato solicitado:

```text
quiz        → failed
flashcards  → failed
```

Del mismo modo, si Agentes responde pero incumple el contrato esperado —por ejemplo, retorna otro `document_id` o un conjunto incompleto de formatos— se persisten intentos `FAILED` antes de producir `FormatGenerationContractError`.

Estos fallos **no modifican `DocumentStatus.INDEXED`**, porque la indexación ya terminó correctamente. El fallo pertenece al ciclo de vida de los formatos, no al ciclo de vida del documento.

En el flujo de carga actual, los errores posteriores de generación ocurren en background y **no pueden convertir en `502` una respuesta de `POST /documents` que ya fue enviada**.

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
| `pending` | No existe historial de generación y el documento no está indexándose ni se encuentra en un estado fallido. Esto incluye un documento `INDEXED` cuya generación en background aún no ha persistido un resultado. |
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

BackendAPI no persiste todavía un estado independiente `generation_in_progress`. Por eso, durante esta primera tarjeta de Sprint 3, el estado `processing` continúa reservado para la indexación activa. La granularidad de estados de generación pertenece a la siguiente tarjeta de Sprint 3.

Si la indexación finaliza correctamente pero la integración con Agentes falla o supera su timeout, BackendAPI conserva el documento como `INDEXED`, persiste ambos intentos como `FAILED` y la consulta devuelve:

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
AdaptationOrchestrationService
   │
   └─ ensure_document_indexed()
          ↓
      RAGIntegrationService
          ├─ recupera original desde OCI
          └─ POST /api/v1/index
                 ↓
              INDEXED
                 ↓
      programar generación en background
                 ↓
Respuesta de carga
   ├─ document_id
   ├─ filename
   ├─ status = indexed
   └─ duplicate
                 │
                 └──────────── background ────────────┐
                                                     ↓
                                         generate_default_formats()
                                                     ↓
                                         FormatGenerationService
                                                     ↓
                                         POST /api/v1/generate
                                             ├─ Quiz
                                             └─ Flashcards
                                                     ↓
                                   GeneratedFormat + chunks_used → SQLite
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

Flujo síncrono ejecutado por una solicitud:

```text
validar
→ registrar
→ almacenar en OCI
→ indexar
→ alcanzar INDEXED
→ programar generación en background
→ responder metadata del documento
```

Después de responder al cliente:

```text
background task
→ solicitar Quiz + Flashcards a Agentes
→ validar resultados
→ persistir GeneratedFormat
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

La API traduce explícitamente los errores de la etapa que todavía forma parte de la solicitud HTTP.

### Durante almacenamiento e indexación

Casos relevantes:

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

El fallo ocurre antes de programar la generación, por lo que el `POST /documents` puede fallar.

### Durante generación en background

Casos relevantes:

```text
FormatGenerationDocumentNotFoundError
DocumentNotReadyForGenerationError
FormatGenerationIntegrationError
FormatGenerationContractError
```

Estos errores ya no se convierten en una respuesta HTTP del `POST /documents`, porque la respuesta fue enviada después de la indexación.

`execute_background_generation()`:

1. ejecuta `generate_default_formats()`;
2. permite que `FormatGenerationService` persista los intentos fallidos cuando corresponde;
3. registra el error en logs;
4. evita que una excepción de background cambie la respuesta ya enviada al cliente.

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

### Fallo de integración o contrato después de indexar

Si el documento ya quedó `INDEXED` pero ocurre uno de estos casos:

```text
AgentsError
FormatGenerationContractError
```

`FormatGenerationService` persiste un intento `FAILED` por cada formato solicitado.

El flujo observable actual queda:

```text
indexación
    ↓
INDEXED
    ↓
POST /documents responde 201/200
    │
    └── generación background
            ↓
       falla integración,
       timeout o contrato
            ↓
       quiz = FAILED
       flashcards = FAILED
```

Posteriormente:

```text
GET /documents/{document_id}
→ status = indexed
```

```text
GET /documents/{document_id}/formats
→ status = error
```

De esta forma, `INDEXED` conserva su significado correcto y el fallo posterior queda representado por el historial de `GeneratedFormat`.

El endpoint explícito de regeneración no forma parte todavía de esta tarjeta y corresponde a una implementación posterior de Sprint 3.

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
- separación de `ensure_document_indexed()` y `generate_default_formats()`;
- indexación síncrona desde `POST /documents`;
- generación automática de Quiz y Flashcards como tarea en segundo plano;
- persistencia SQLite de los resultados recibidos vía HTTP;
- lectura posterior de esos resultados desde SQLite;
- contexto pedagógico de generación;
- persistencia y reconstrucción de `chunks_used`;
- historial de generaciones;
- persistencia de generaciones fallidas;
- persistencia de intentos `FAILED` ante errores de integración con Agentes;
- persistencia de intentos `FAILED` ante incumplimientos del contrato de Agentes;
- semántica de `INDEXED` separada del estado de generación;
- `INDEXING` como único estado de documento que produce actualmente `formats.status = processing` sin historial;
- `INDEXED` sin intentos persistidos como `formats.status = pending`;
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

## Validación funcional de la separación indexación / generación

La tarjeta de Sprint 3 **“Separar indexación RAG síncrona y generación con tiempo controlado”** fue validada funcionalmente en local.

### 1. Validación aislada de RAG

Se ejecutó directamente:

```text
POST http://127.0.0.1:8001/api/v1/index
```

con un archivo TXT de prueba.

Resultado:

```http
HTTP/1.1 200 OK
```

```json
{
  "document_id": "doc_rag_test_sprint3",
  "status": "indexed"
}
```

Tiempo observado:

```text
~0.34 s
```

Esto confirmó que el servicio de indexación estaba operativo antes de probar el comportamiento asíncrono del Backend.

### 2. Generación lenta con timeout controlado

Para aislar la responsabilidad de Backend, la generación se dirigió temporalmente a un mock HTTP que demoraba 10 segundos en responder:

```text
RAG_BASE_URL=http://127.0.0.1:8001
RAG_TIMEOUT_SECONDS=30

AGENTS_BASE_URL=http://127.0.0.1:8002
AGENTS_TIMEOUT_SECONDS=2
```

El flujo probado fue:

```text
POST /api/v1/documents
    ↓
SQLite + OCI
    ↓
RAG /index real
    ↓
INDEXED
    ↓
programar generación background
    ↓
HTTP 201
         │
         └── POST /api/v1/generate
                  ↓
            mock demora 10 s
                  ↓
        Backend corta a los 2 s
                  ↓
       persistencia de FAILED
```

Respuesta observada de `POST /documents`:

```http
HTTP/1.1 201 Created
```

```json
{
  "document_id": "doc_0621bc23b79f4c948f25c0c53a7bd25f",
  "filename": "e2e_async_timeout.txt",
  "status": "indexed",
  "duplicate": false
}
```

Tiempo observado:

```text
TOTAL_TIME=0.277318s
```

El POST respondió mucho antes del timeout de generación y mucho antes de los 10 segundos del mock, demostrando que `/generate` ya no bloquea la solicitud de carga.

### 3. Estado del documento después del timeout

Posteriormente:

```text
GET /api/v1/documents/doc_0621bc23b79f4c948f25c0c53a7bd25f
```

mantuvo:

```json
{
  "status": "indexed"
}
```

### 4. Estado de formatos después del timeout

La consulta:

```text
GET /api/v1/documents/doc_0621bc23b79f4c948f25c0c53a7bd25f/formats
```

retornó:

```json
{
  "document_id": "doc_0621bc23b79f4c948f25c0c53a7bd25f",
  "status": "error",
  "formats": {
    "quiz": {
      "status": "failed",
      "content": null
    },
    "flashcards": {
      "status": "failed",
      "content": null
    }
  }
}
```

Ambos formatos conservaron además su `format_id` y un `error_message` explícito.

La prueba confirma:

```text
indexación síncrona                     ✅
POST responde después de INDEXED       ✅
generación desacoplada                  ✅
timeout independiente de Agentes        ✅
fallo de generación no produce 502      ✅
documento permanece INDEXED             ✅
fallos quedan persistidos por formato   ✅
```

También se comprobó previamente el comportamiento complementario: si RAG falla durante la etapa síncrona, `POST /documents` responde `502` y el documento queda en `INDEXING_FAILED`. Esto confirma que la separación entre ambas etapas es efectiva.

---

## Semántica del flujo actual para Frontend

El contrato actual separa explícitamente **estado del documento** de **estado del material generado**.

### Durante la carga

Frontend ejecuta:

```text
POST /api/v1/documents
```

Backend completa antes de responder:

```text
persistencia
→ almacenamiento
→ indexación
→ INDEXED
```

Después programa:

```text
Quiz + Flashcards
→ persistencia de formatos
```

Frontend recibe la metadata del documento una vez terminada la indexación, sin esperar a la generación.

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

### Estado durante la generación

En esta primera tarjeta de Sprint 3 **todavía no se agregó un estado persistido `processing` específico de generación**.

Por ello, después de que el documento alcanza `INDEXED` y antes de que exista historial de formatos, `/formats` puede retornar:

```text
status = pending
```

La granularidad de estados reales para Frontend corresponde a la tarjeta posterior **“Envío de estados a Frontend”**.

No se debe ampliar artificialmente `DocumentStatus` con estados de Quiz o Flashcards, porque documento y generación mantienen ciclos de vida distintos.

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

### Estados de generación

La separación indexación/generación ya está implementada, pero el modelado de estados detallados de ejecución de Quiz y Flashcards corresponde a una tarjeta posterior.

La evolución debe mantener esta separación:

```text
DocumentStatus
→ ciclo de vida del documento e indexación

GeneratedFormat / estado agregado de formatos
→ ciclo de vida del contenido pedagógico
```

### Regeneración

El endpoint explícito para regenerar formatos todavía no forma parte del contrato público actual. Su implementación debe reutilizar `FormatGenerationService`, conservar el contexto pedagógico y evitar reindexaciones innecesarias.

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
   ├── validación
   ├── SHA-256 / deduplicación
   ├── SQLite
   └── OCI Object Storage
   ↓
AdaptationOrchestrationService
   ↓
ensure_document_indexed()
   ↓
RAGIntegrationService
   ↓
POST /api/v1/index
   ↓
INDEXED
   ↓
programar BackgroundTask
   ↓
Respuesta de metadata al Frontend
   │
   └────────────── background ──────────────┐
                                            ↓
                              generate_default_formats()
                                            ↓
                              FormatGenerationService
                                            ↓
                              POST /api/v1/generate
                                            ↓
                                  Quiz + Flashcards
                                            ↓
                                         SQLite

Frontend
   ↓
GET /api/v1/documents/{document_id}/formats
   ↓
Quiz + Flashcards persistidos
```

El objetivo arquitectónico se mantiene: **Frontend conoce BackendAPI; BackendAPI orquesta el producto; RAG/Agentes resuelve recuperación y generación; Data/IA permanece desacoplado para evaluación.**
