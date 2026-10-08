# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI**, **Pydantic v2**, **SQLite** y **OCI Object Storage**.

BackendAPI actúa como **orquestador del producto**: recibe las solicitudes del Frontend, administra la metadata técnica y pedagógica y el ciclo de vida de los documentos, persiste los archivos originales, coordina la indexación con RAG/Agentes, solicita la generación de material educativo, conserva los resultados para su consulta posterior y mantiene en OCI un paquete JSON con el contenido educativo vigente.

BackendAPI **no implementa internamente** extracción de texto, limpieza, chunking, embeddings, Vector Store, retrieval semántico, prompts, generación mediante LLM ni cálculo de métricas de calidad. Estas responsabilidades permanecen desacopladas mediante Ports y Adapters. BackendAPI orquesta la evaluación de formatos exitosos mediante el servicio externo Data/IA y persiste sus resultados históricos.

El frontend se encuentra en [`../frontend`](../frontend).

> Los comandos de este documento se ejecutan desde `backend/`, salvo que se indique lo contrario.

---

## Estado actual

El flujo principal se encuentra integrado de extremo a extremo desde BackendAPI y, a partir de Sprint 3, **la indexación RAG y la generación de formatos tienen ciclos de ejecución separados**.

Actualmente están implementados:

### Documentos y almacenamiento

- API FastAPI y configuración centralizada.
- Endpoint de salud.
- `POST /api/v1/documents` como entrada pública para cargar, almacenar e indexar un documento y programar su generación pedagógica inicial.
- `GET /api/v1/documents` para listar documentos disponibles en la biblioteca.
- `GET /api/v1/documents/{document_id}` para consultar metadata técnica, metadata pedagógica y estado del documento.
- `GET /api/v1/documents/{document_id}/download` para recuperar desde OCI el archivo original mediante BackendAPI.
- `GET /api/v1/documents/{document_id}/formats` para consultar Quiz y Flashcards persistidos.
- `POST /api/v1/documents/{document_id}/formats/regenerate` para iniciar una nueva generación de uno o varios formatos reutilizando el contexto pedagógico persistido.
- Contrato transversal de errores con `code`, `detail`, `errors[]` y `timestamp`, independiente de los mensajes de UI de Frontend.
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
- La identidad lógica del documento depende del contenido (SHA-256), no del nombre del archivo.
- Mismo SHA-256 reutiliza el mismo `document_id` y evita una nueva carga del original a OCI.
- Mismo nombre de archivo con contenido diferente genera un nuevo `document_id` y un objeto OCI independiente, sin sobrescribir el original previo.
- Generación de `document_id` canónico para documentos nuevos.
- Persistencia de metadata técnica, metadata pedagógica y estado mediante `DocumentRepositoryPort`.
- Implementación SQLite mediante `SQLiteDocumentRepositoryAdapter`.
- Persistencia del archivo original en OCI mediante `ObjectStoragePort`.
- Implementación OCI mediante `OCIObjectStorageAdapter`.
- Convención del original en OCI: `documents/{document_id}/original.ext`.
- Persistencia de `oci_object_name`.
- Persistencia del paquete educativo generado en el **mismo bucket OCI** mediante `documents/{document_id}/generated/content.json`.
- Escritura del paquete JSON en memoria mediante `ObjectStoragePort.upload_bytes(...)`, sin archivo temporal adicional.
- Reconstrucción del paquete desde el estado canónico persistido de BackendAPI, sin guardar directamente la respuesta bruta de Agentes.
- El paquete OCI incluye `document_id`, `learning_metadata` y los formatos educativos vigentes.
- `chunks_used`, `GenerationContext` y la evaluación de Data/IA no forman parte del paquete OCI actual.
- Integración HTTP BackendAPI → Data/IA mediante `DataIAPort` y `HTTPDataIAAdapter`.
- Evaluación automática de cada `GeneratedFormat` exitoso después de la generación.
- Persistencia histórica de evaluaciones mediante `FormatEvaluationRepositoryPort` y SQLite.
- Un fallo de Data/IA no degrada un formato ya generado con `success` ni impide conservar el snapshot educativo.
- Recepción de `learning_metadata` desde Agentes a nivel raíz del contrato de generación.
- Persistencia de `learning_metadata` una sola vez a nivel de documento mediante `learning_metadata_json`.
- Exposición de `learning_metadata` mediante `GET /api/v1/documents/{document_id}`.
- Recuperación interna: `document_id → metadata → oci_object_name → bytes`.
- La misma recuperación se reutiliza para indexación RAG y para la descarga pública del original.
- Representación del documento recuperado mediante `RetrievedDocument`.
- Descarga HTTP del original con su `Content-Type` persistido y `Content-Disposition: attachment`.
- Exposición CORS de `Content-Disposition` para que Frontend pueda recuperar el nombre original.
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
3. valida el contrato recibido, incluyendo `learning_metadata`;
4. persiste `learning_metadata` a nivel del documento cuando corresponde;
5. actualiza los mismos `format_id`;
6. termina cada intento en uno de estos estados;
7. reconstruye el paquete educativo terminal vigente;
8. persiste `documents/{document_id}/generated/content.json` en OCI:

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

No se crea una nueva fila para completar un intento iniciado por la misma generación. El mismo `format_id` se conserva durante la transición. La metadata pedagógica no se duplica por formato.

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

\| Campo | Tipo | Obligatorio | Valores / descripción |

\|---|---|---:|---|

\| `file` | archivo | Sí | PDF, Markdown o TXT |

\| `profile` | string | Sí | `beginner`, `intermediate`, `advanced` |

\| `niche` | string | Sí | `general`, `backend`, `health`, `legal`, `business`, `humanities` |

\| `detail_level` | string | Sí | Texto no vacío |

\| `learning_objective` | string | No | Objetivo específico de aprendizaje |

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
→ validar y persistir learning_metadata cuando corresponda
→ actualizar mismos format_id
→ success | failed | no_results
→ reconstruir snapshot educativo vigente
→ persistir documents/{document_id}/generated/content.json en OCI
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

#### Identidad, deduplicación y no sobrescritura

BackendAPI no utiliza `original_filename` como identidad del documento. La identidad se determina por la firma SHA-256 calculada sobre el contenido recibido.

Reglas del flujo:

```text
mismo SHA-256
→ mismo document_id
→ duplicate = true
→ no se vuelve a cargar el original en OCI
SHA-256 diferente
→ nuevo document_id
→ duplicate = false
→ nuevo objeto OCI independiente
```

Por tanto, subir dos archivos con el mismo nombre no implica sobrescritura. Si sus contenidos son diferentes, cada uno conserva su propio `document_id` y su propio objeto:

```text
documents/{document_id}/original.ext
```

Del mismo modo, volver a subir exactamente el mismo contenido —aunque cambie el nombre del archivo— reutiliza el documento ya registrado. La restricción `UNIQUE` sobre `sha256` en SQLite refuerza esta identidad a nivel de persistencia.

Este comportamiento está cubierto por pruebas de integración específicas que verifican tanto la reutilización por SHA como la conservación simultánea de dos documentos con el mismo nombre y contenido diferente.

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
- recibir `learning_metadata` una sola vez a nivel raíz;
- convertir `learning_metadata` al value object `LearningMetadata`;
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
- validar `learning_metadata`;
- validar exactamente los formatos solicitados;
- rechazar resultados duplicados;
- persistir `learning_metadata` a nivel del documento;
- actualizar cada intento sobre el mismo `format_id`;
- conservar chunks utilizados como evidencia;
- terminar en `success`, `failed` o `no_results`.

Si la persistencia de `learning_metadata` falla, BackendAPI cierra los intentos que continúen en `processing` como `failed` y registra `FormatGenerationMetadataPersistenceError`.

#### `GeneratedPackageStorageService`

La persistencia del paquete educativo se mantiene separada de `FormatGenerationService`.

Flujo:

```text
FormatGenerationService
→ persiste estados terminales en SQLite
↓
AdaptationOrchestrationService
↓
GeneratedPackageStorageService
↓
ObjectStoragePort
↓
OCIObjectStorageAdapter
```

El objeto canónico se almacena en:

```text
documents/{document_id}/generated/content.json
```

Contrato:

```json
{
  "document_id": "doc_123",
  "learning_metadata": {
    "key_concepts": [
      "RAG"
    ],
    "prerequisites": [
      "Fundamentos de Python"
    ],
    "estimated_time_minutes": 18
  },
  "formats": {
    "quiz": {
      "format_id": "fmt_quiz_2",
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

Selección estable por tipo:

```text
processing
→ no reemplaza el snapshot OCI vigente

si existe al menos un success histórico
→ usar el success más reciente

si nunca existió success
→ usar el intento terminal más reciente
```

Así, una regeneración exitosa de un solo formato actualiza únicamente ese formato dentro del snapshot reconstruido y conserva el otro formato vigente. Una regeneración fallida no elimina un `success` anterior válido.

El paquete no incluye actualmente:

```text
chunks_used
GenerationContext
evaluación Data/IA
```

#### `FormatRegenerationService`

La regeneración explícita permanece separada de la generación inicial.

Responsabilidades:

- validar que el documento exista y permanezca `INDEXED`;
- rechazar la solicitud completa si alguno de los formatos pedidos ya tiene un intento `processing`;
- recuperar el `GenerationContext` del intento previo más reciente;
- reutilizar `profile`, `niche`, `detail_level` y `learning_objective`;
- delegar la creación de nuevos intentos a `FormatGenerationService`;
- crear un nuevo `format_id` por formato sin sobrescribir el historial anterior;
- reutilizar el mismo flujo de generación en segundo plano sin reindexar el documento.

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
- `learning_metadata` incompatible;
- formatos incompletos;
- formatos duplicados;
- estados incompatibles;
- contenido inválido;

BackendAPI marca los intentos en `failed` y produce `FormatGenerationContractError`.

Estos fallos **no modifican `DocumentStatus.INDEXED`**.

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
  "learning_metadata": {
    "key_concepts": [
      "RAG",
      "Embeddings",
      "Vector Store"
    ],
    "prerequisites": [
      "Fundamentos de Python"
    ],
    "estimated_time_minutes": 18
  },
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

`learning_metadata` pertenece al documento/adaptación y aparece una sola vez, al mismo nivel que `document_id` y `results`. No se duplica dentro de Quiz, Flashcards u otros formatos.

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

#### Contrato canónico de `learning_metadata`

BackendAPI representa los metadatos pedagógicos mediante el value object:

```text
LearningMetadata
├── key_concepts
├── prerequisites
└── estimated_time_minutes
```

Reglas:

- `key_concepts` y `prerequisites` se representan como colecciones de textos no vacíos;
- `estimated_time_minutes` es un entero mayor o igual a cero;
- el objeto pertenece al documento/adaptación y no a un formato particular;
- BackendAPI lo recibe desde Agentes, lo valida, lo convierte a dominio y lo persiste en `documents`;
- durante la generación inicial puede permanecer en `null` hasta que exista una respuesta válida de Agentes;
- la primera metadata pedagógica útil queda estable a nivel de documento;
- regenerar Quiz o Flashcards no reemplaza metadata pedagógica útil ya persistida;
- el fallback de Agentes puede producir listas vacías y `estimated_time_minutes = 0` sin romper el flujo;
- si el documento solo conserva ese fallback vacío, una generación posterior puede reemplazarlo por metadata útil.

El tiempo de estudio canónico se expone exclusivamente como:

```text
learning_metadata.estimated_time_minutes
```

#### Semántica del tiempo de estudio y los timeouts técnicos

`learning_metadata.estimated_time_minutes` representa **tiempo estimado de estudio o lectura para el estudiante**. No controla la duración de una petición HTTP, no determina cuánto espera Frontend por Backend y no configura cuánto espera Backend por RAG o Agentes.

Los tiempos de espera técnicos permanecen separados mediante configuración específica:

```text
RAG_TIMEOUT_SECONDS
AGENTS_TIMEOUT_SECONDS
```

Frontend mantiene igualmente sus propios timeouts de transporte. Estos valores pertenecen a la comunicación entre servicios y no tienen relación con `learning_metadata.estimated_time_minutes`.

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

\| Estado | Significado |

\|---|---|

\| `pending` | El documento existe pero todavía no hay intentos persistidos para exponer. |

\| `processing` | Existe al menos un intento vigente en `processing`, o el documento aún está indexándose sin historial de formatos. |

\| `ready` | Quiz y Flashcards vigentes están en `success`. |

\| `partial` | No hay intentos activos y existe al menos un formato exitoso, pero no todos. |

\| `error` | No hay intentos activos ni formatos exitosos vigentes. |

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

Esta regla de consulta pública no debe confundirse con la selección del snapshot OCI. Mientras `/formats` expone un intento `processing` para que Frontend pueda observarlo, `generated/content.json` conserva únicamente una proyección terminal estable hasta que la nueva generación finaliza.

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

La tabla `documents` conserva la metadata técnica del archivo y la metadata pedagógica vigente:

```text
document_id
original_filename
sha256
content_type
size_bytes
status
oci_object_name
learning_metadata_json
created_at
updated_at
```

`learning_metadata_json` serializa el value object `LearningMetadata` completo.

La inicialización de SQLite agrega la columna mediante una migración idempotente cuando una base creada previamente aún no la contiene. Los documentos existentes se conservan y reciben `learning_metadata_json = NULL`.

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

La inicialización de SQLite incluye dos migraciones idempotentes relevantes: una agrega `learning_metadata_json` a `documents` cuando la columna no existe y otra actualiza bases anteriores cuyo `CHECK` de `generated_formats.status` no incluía `processing`. Ambas conservan los datos existentes; la migración de formatos mantiene además las relaciones con `format_evaluations`, recrea los índices y valida integridad referencial mediante `foreign_key_check`.

### Persistencia del contenido educativo en OCI

SQLite conserva el historial de generaciones. OCI conserva una proyección JSON del contenido educativo vigente.

Para un mismo documento:

```text
bucket configurado en OCI_BUCKET_NAME
└── documents/
    └── {document_id}/
        ├── original.ext
        └── generated/
            └── content.json
```

Se utiliza el **mismo bucket** para el original y el JSON generado.

`ObjectStoragePort` expone:

```text
upload_file(...)
upload_bytes(...)
download_file(...)
delete_object(...)
```

`upload_bytes(...)` permite almacenar el JSON directamente como bytes UTF-8 con:

```text
Content-Type: application/json
```

La ruta `generated/content.json` funciona como snapshot actual y puede reemplazarse para el mismo `document_id` después de una generación o regeneración. Esto no modifica la regla de no sobrescritura de archivos originales: `original.ext` continúa siendo inmutable para la identidad lógica del documento y SQLite conserva el historial completo de generaciones.

### Integración BackendAPI → Data/IA

La evaluación de calidad está integrada mediante:

```text
FormatEvaluationService
↓
DataIAPort
↑
HTTPDataIAAdapter
↓
POST /evaluate
```

Data/IA recibe únicamente contenido **ya generado exitosamente**. No genera Quiz ni Flashcards y no controla el estado de generación.

Contrato enviado:

```json
{
  "document_id": "doc_123",
  "format": "quiz",
  "generated_content": {},
  "generation_context": {
    "profile": "intermediate",
    "niche": "backend",
    "detail_level": "detailed",
    "learning_objective": "Comprender arquitectura."
  },
  "chunks_used": []
}
```

El adapter traduce:

```text
relevancia               → relevance
coherencia                → coherence
adaptacion_didactica      → didactic_adaptation
informacion_respaldada    → content_support
```

Una evaluación pertenece a una generación concreta:

```text
GeneratedFormat 1 → N FormatEvaluation
```

SQLite conserva el historial en `format_evaluations`.

Estados:

```text
aprobado
requiere_revision
rechazado
```

Política de resiliencia:

```text
Agentes genera success
↓
Data/IA evalúa
↓
si responde:
    persistir FormatEvaluation

si falla:
    registrar el error
    conservar GeneratedFormat = success
    continuar el flujo
```

Un fallo de Data/IA no invalida contenido que Agentes ya generó correctamente.

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

\| Capa | Responsabilidad |

\|---|---|

\| `api/` | Endpoints HTTP, dependencias FastAPI y traducción de errores de aplicación a HTTP |

\| `schemas/` | Contratos externos de entrada y salida |

\| `domain/` | Entidades, estados, contenido canónico y reglas de dominio |

\| `application/` | Casos de uso y orquestación |

\| `ports/` | Contratos hacia persistencia e integraciones externas |

\| `infrastructure/` | Adapters e implementaciones concretas |

\| `core/` | Configuración, logging, excepciones y utilidades |

### Fronteras del sistema

```text
Frontend
↓
BackendAPI
├── SQLite
├── OCI Object Storage
├── RAG / Agentes
└── Data/IA
```

BackendAPI es el único punto de entrada del Frontend hacia los servicios de negocio e IA.

RAG/Agentes:

- no accede directamente a la BD de negocio;
- no necesita credenciales de OCI;
- no administra la persistencia de documentos de negocio;
- es responsable de extracción, limpieza, chunking, embeddings, retrieval, Vector Store y generación.

Data/IA:

- está desacoplado mediante `DataIAPort`;
- se consume mediante `HTTPDataIAAdapter`;
- evalúa calidad de contenido ya generado exitosamente;
- recibe contenido, contexto de generación y `chunks_used`;
- no administra documentos;
- no genera material educativo;
- no cambia el estado de un `GeneratedFormat`;
- sus resultados se persisten históricamente en SQLite.

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
│
├─ success → FormatEvaluationService
│             ↓
│          Data/IA /evaluate
│             ↓
│          format_evaluations
│
▼
GeneratedPackageStorageService
│
▼
documents/{document_id}/generated/content.json
│
▼
OCI Object Storage
```

Frontend consulta:

```text
GET /api/v1/documents/{document_id}/formats
```

y hace polling mientras:

```text
status = processing
```

La regeneración reutiliza el mismo pipeline de generación:

```text
POST /api/v1/documents/{document_id}/formats/regenerate
↓
FormatRegenerationService
↓
validar INDEXED + ausencia de processing en formatos solicitados
↓
reutilizar GenerationContext persistido
↓
nuevos format_id = processing
↓
202 Accepted
│
└──────────── background ─────────────┐
↓
Agentes /generate
↓
mismos nuevos format_id
↓
success | failed | no_results
↓
success → Data/IA /evaluate
↓
persistir evaluación histórica cuando esté disponible
↓
reconstruir snapshot terminal vigente
↓
actualizar generated/content.json en OCI
```

Frontend continúa consultando el mismo `GET /formats`; no existe un endpoint adicional de estado para la regeneración.

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
quiz        = processing
flashcards  = processing
```

o:

```text
quiz        = failed
flashcards  = failed
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
file                 requerido
profile              requerido
niche                requerido
detail_level         requerido
learning_objective   opcional
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
→ evaluar con Data/IA únicamente los success
→ persistir evaluaciones disponibles
→ actualizar snapshot educativo OCI
```

Ejemplo con `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/documents" \\
-F "file=@manual.txt;type=text/plain" \\
-F "profile=intermediate" \\
-F "niche=backend" \\
-F "detail_level=detailed" \\
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

\| HTTP | Caso |

\|---:|---|

\| `400` | Documento vacío o inválido |

\| `409` | Estado del documento incompatible con la indexación |

\| `413` | Archivo supera el tamaño máximo permitido |

\| `415` | Extensión o MIME type no soportado |

\| `422` | Faltan parámetros obligatorios o el contexto pedagógico es inválido |

\| `502` | Fallo de OCI, recuperación del original o indexación RAG |

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
  "learning_metadata": {
    "key_concepts": [
      "RAG",
      "Embeddings",
      "Vector Store"
    ],
    "prerequisites": [
      "Fundamentos de Python"
    ],
    "estimated_time_minutes": 18
  }
}
```

`learning_metadata` puede permanecer en `null` mientras la generación en segundo plano todavía no haya producido una respuesta válida de Agentes.

Los campos opcionales `title` y `summary` continúan preparados para metadata enriquecida adicional y actualmente pueden permanecer en `null`.

El tiempo pedagógico no se expone mediante un campo paralelo en la raíz. La única fuente de verdad es `learning_metadata.estimated_time_minutes`.

`formats_status` no forma parte de este contrato. La fuente de verdad para disponibilidad y estado de Quiz y Flashcards es `/formats`.

### Descargar documento original

```http
GET /api/v1/documents/{document_id}/download
```

BackendAPI recupera el archivo original desde OCI utilizando el `document_id` canónico. Frontend no conoce `oci_object_name`, credenciales OCI ni la estructura interna del bucket.

Flujo:

```text
Frontend
↓
GET /api/v1/documents/{document_id}/download
↓
DocumentService.retrieve_document()
↓
ObjectStoragePort.download_file()
↓
OCIObjectStorageAdapter
↓
OCI Object Storage
```

Respuesta exitosa:

```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="manual.pdf"; filename*=UTF-8''manual.pdf
```

El body contiene los bytes del archivo original.

Para TXT y Markdown se conserva igualmente el MIME type persistido. Si no existe un MIME type disponible, Backend utiliza `application/octet-stream`.

`Content-Disposition` utiliza `filename` como fallback compatible y `filename*` para conservar correctamente nombres UTF-8.

Errores principales:

| HTTP | `code` | Caso |
|---:|---|---|
| `404` | `DOCUMENT_NOT_FOUND` | El `document_id` no existe. |
| `409` | `DOCUMENT_STATE_CONFLICT` | El documento existe, pero no tiene un objeto original almacenado asociado. |
| `500` | `PERSISTENCE_ERROR` | No fue posible consultar la metadata persistida del documento. |
| `502` | `DOCUMENT_RETRIEVAL_FAILED` | No fue posible recuperar el objeto original desde OCI. |

La descarga pública reutiliza el mismo caso de uso `DocumentService.retrieve_document()` que ya utiliza la integración RAG. No existe una segunda implementación de acceso a OCI.

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

### Regenerar formatos

```http
POST /api/v1/documents/{document_id}/formats/regenerate
Content-Type: application/json
```

Permite iniciar una nueva generación de uno o varios formatos soportados sin volver a cargar ni reindexar el documento.

Solicitud para un solo formato:

```json
{
"formats": [
"quiz"
]
}
```

Solicitud para varios formatos:

```json
{
"formats": [
"quiz",
"flashcards"
]
}
```

Frontend **no vuelve a enviar**:

```text
profile
niche
detail_level
learning_objective
```

Backend recupera automáticamente esos valores desde el contexto pedagógico persistido de la generación anterior.

Antes de crear los nuevos intentos Backend valida:

1. que el documento exista;
2. que el documento esté `INDEXED`;
3. que ninguno de los formatos solicitados tenga un intento activo en `processing`;
4. que exista un contexto pedagógico previo reutilizable para los formatos solicitados.

La regeneración no está limitada a contenido fallido. Un formato solicitado puede tener previamente:

```text
success
failed
no_results
```

y aun así generar un nuevo `format_id`. Por tanto, estados agregados `ready`, `partial` o `error` no bloquean por sí mismos la regeneración.

Si cualquiera de los **formatos solicitados** ya está en `processing`, la solicitud completa se rechaza y no se inicia una regeneración parcial.

Respuesta aceptada:

```http
HTTP/1.1 202 Accepted
```

```json
{
"document_id": "doc_123",
"status": "processing",
"formats": {
"quiz": {
"format_id": "fmt_quiz_2",
"status": "processing"
}
}
}
```

Cada regeneración crea un nuevo `format_id`. Los intentos anteriores permanecen persistidos como historial.

Después del `202`, la generación continúa en segundo plano mediante el mismo pipeline utilizado por la generación inicial:

```text
processing
↓
success | failed | no_results
```

Frontend debe continuar haciendo polling mediante:

```http
GET /api/v1/documents/{document_id}/formats
```

Errores principales:

\| HTTP | Caso |

\|---:|---|

\| `404` | `document_id` inexistente |

\| `409` | Documento no `INDEXED`, formato solicitado en `processing` o ausencia/conflicto de contexto previo reutilizable |

\| `422` | `formats` vacío, duplicado o con un formato no soportado |

\| `500` | No fue posible registrar los nuevos intentos |

La regeneración no vuelve a almacenar el archivo original en OCI y no ejecuta una nueva indexación RAG. Después de alcanzar estados terminales, Backend reconstruye el paquete educativo y actualiza `documents/{document_id}/generated/content.json`, conservando los formatos vigentes que no fueron regenerados.

### Endpoint de adaptación

No existe un endpoint público:

```text
POST /api/v1/adaptations
```

La adaptación educativa inicial es una operación interna iniciada desde `POST /api/v1/documents`.

---

## Manejo de errores del flujo integrado

BackendAPI expone un contrato transversal de errores para que Frontend pueda

distinguir la causa funcional sin depender únicamente del HTTP status ni de

comparar mensajes humanos.

La respuesta estándar es:

```json
{
"code": "RAG_INDEXING_FAILED",
"detail": "No fue posible completar la indexación del documento.",
"errors": [],
"timestamp": "2026-10-07T18:00:00Z"
}
```

Responsabilidad de cada campo:

\| Campo | Responsabilidad |

\|---|---|

\| HTTP status | Semántica del protocolo (`404`, `409`, `422`, `500`, `502`, etc.). |

\| `code` | Identificador funcional estable consumible por Frontend. |

\| `detail` | Mensaje seguro y legible para el cliente. |

\| `errors[]` | Detalles estructurados, especialmente validaciones por campo. |

\| `timestamp` | Momento en que Backend construyó la respuesta de error. |

Los códigos públicos se centralizan en:

```text
app/core/error_codes.py
```

Los errores HTTP controlados utilizan:

```text
APIHTTPException
```

definida en:

```text
app/core/http_exceptions.py
```

La traducción final al `ErrorResponse` continúa centralizada en:

```text
app/core/exceptions.py
```

Frontend no debe depender de nombres de excepciones Python ni comparar el texto

de `detail` para decidir comportamiento. Debe usar prioritariamente `code`.

### Validaciones `422`

Los errores de Pydantic conservan un código raíz estable y el detalle por campo:

```json
{
"code": "REQUEST_VALIDATION_ERROR",
"detail": "Error de validación en la petición.",
"errors": [
{
"code": "value_error",
"message": "formats no puede contener valores duplicados.",
"field": "formats"
}
],
"timestamp": "2026-10-07T18:00:00Z"
}
```

El `code` raíz identifica la categoría funcional completa. El `code` interno de

cada elemento de `errors[]` conserva el identificador específico producido por

la validación.

### Códigos funcionales expuestos

\| `code` | HTTP | Caso principal |

\|---|---:|---|

\| `DOCUMENT_FILENAME_REQUIRED` | `400` | El archivo no tiene un nombre válido. |

\| `DOCUMENT_EMPTY` | `400` | El archivo recibido tiene cero bytes. |

\| `DOCUMENT_NOT_FOUND` | `404` | El `document_id` solicitado no existe. |

\| `DOCUMENT_STATE_CONFLICT` | `409` | El documento no permite la transición solicitada. |

\| `DOCUMENT_NOT_INDEXED` | `409` | Se intenta generar/regenerar sin estado `INDEXED`. |

\| `FILE_TOO_LARGE` | `413` | El archivo supera el máximo configurado. |

\| `UNSUPPORTED_FILE_TYPE` | `415` | La extensión no está soportada. |

\| `MIME_TYPE_MISMATCH` | `415` | El MIME type declarado no corresponde al formato admitido. |

\| `REQUEST_VALIDATION_ERROR` | `422` | El request no cumple el schema HTTP. |

\| `DOCUMENT_STORAGE_FAILED` | `502` | Falló el almacenamiento del original en OCI. |

\| `DOCUMENT_RETRIEVAL_FAILED` | `502` | No fue posible recuperar el original desde Object Storage. |

\| `RAG_INDEXING_FAILED` | `502` | Falló la integración/indexación RAG. |

\| `FORMAT_REGISTRATION_FAILED` | `500` | No fue posible registrar los intentos iniciales de generación. |

\| `FORMAT_REGENERATION_IN_PROGRESS` | `409` | Algún formato solicitado ya tiene un intento `processing`. |

\| `FORMAT_CONTEXT_NOT_FOUND` | `409` | No existe contexto pedagógico previo reutilizable. |

\| `FORMAT_CONTEXT_CONFLICT` | `409` | Los formatos solicitados no comparten un contexto reutilizable. |

\| `FORMAT_REGENERATION_REGISTRATION_FAILED` | `500` | No fue posible registrar los nuevos intentos de regeneración. |

\| `PERSISTENCE_ERROR` | `500` | Fallo conocido al acceder a la persistencia. |

\| `INTERNAL_SERVER_ERROR` | `500` | Excepción no controlada. |

\| `HTTP_ERROR` | variable | `HTTPException` de framework/ruta sin una causa funcional clasificada. |

`BAD_REQUEST` permanece disponible en el catálogo para errores `400` genéricos

que no tengan todavía una causa más específica.

### Durante almacenamiento e indexación

La traducción diferencia causas que pueden compartir el mismo HTTP status:

```text
DocumentNotFoundError
→ 404 DOCUMENT_NOT_FOUND
AdaptationDocumentStateError
DocumentNotStoredError
DocumentIndexingStateError
→ 409 DOCUMENT_STATE_CONFLICT
DocumentRetrievalError
→ 502 DOCUMENT_RETRIEVAL_FAILED
RAGIntegrationError
→ 502 RAG_INDEXING_FAILED
DocumentStorageError
→ 502 DOCUMENT_STORAGE_FAILED
```

De esta forma un fallo RAG ya no necesita interpretarse en Frontend como si

fuera un fallo de OCI únicamente porque ambos utilicen `502`.

### Descarga del documento original

La descarga traduce explícitamente los errores del caso de uso:

```text
DocumentNotFoundError
→ 404 DOCUMENT_NOT_FOUND

DocumentNotStoredError
→ 409 DOCUMENT_STATE_CONFLICT

DocumentRetrievalError
→ 502 DOCUMENT_RETRIEVAL_FAILED

DocumentRepositoryError
→ 500 PERSISTENCE_ERROR
```

Los fallos de OCI no exponen credenciales, nombres internos del proveedor ni stack traces al cliente.

### Preparación de generación

El registro de intentos `processing` ocurre antes de responder.

Casos públicos principales:

```text
FormatGenerationDocumentNotFoundError
→ 404 DOCUMENT_NOT_FOUND
DocumentNotReadyForGenerationError
→ 409 DOCUMENT_NOT_INDEXED
GeneratedFormatRepositoryError
→ 500 FORMAT_REGISTRATION_FAILED
```

Un fallo de persistencia en esta etapa impide programar una generación que

Frontend no pueda observar correctamente.

### Generación en background

Casos relevantes:

```text
FormatGenerationAttemptStateError
FormatGenerationIntegrationError
FormatGenerationContractError
FormatGenerationDocumentNotFoundError
FormatGenerationMetadataPersistenceError
FormatGenerationRecoveryError
GeneratedFormatRepositoryError
GeneratedPackageError
```

`execute_background_generation()` registra explícitamente el error.

Cuando Agentes falla por timeout, conexión, error HTTP o contrato, o cuando BackendAPI no puede persistir los metadatos pedagógicos recibidos:

```text
processing → failed
```

El documento permanece:

```text
INDEXED
```

Como la respuesta HTTP ya fue enviada, estos errores se observan posteriormente

mediante `GET /documents/{document_id}/formats` y no mediante un nuevo

`ErrorResponse`.

Si Quiz o Flashcards ya alcanzaron estados terminales en SQLite y posteriormente falla la escritura de `generated/content.json` en OCI, Backend registra el fallo de infraestructura pero no convierte artificialmente en `failed` un formato que Agentes ya generó correctamente. La persistencia SQLite continúa siendo la fuente de verdad del historial de generación.

### Regeneración

La preparación de una regeneración traduce cada conflicto a un código estable:

```text
FormatRegenerationDocumentNotFoundError
FormatGenerationDocumentNotFoundError
→ 404 DOCUMENT_NOT_FOUND
FormatRegenerationDocumentStateError
DocumentNotReadyForGenerationError
→ 409 DOCUMENT_NOT_INDEXED
FormatRegenerationInProgressError
→ 409 FORMAT_REGENERATION_IN_PROGRESS
FormatRegenerationContextNotFoundError
→ 409 FORMAT_CONTEXT_NOT_FOUND
FormatRegenerationContextConflictError
→ 409 FORMAT_CONTEXT_CONFLICT
GeneratedFormatRepositoryError
→ 500 FORMAT_REGENERATION_REGISTRATION_FAILED
DocumentRepositoryError
→ 500 PERSISTENCE_ERROR
```

Los errores de validación del body se resuelven mediante Pydantic como:

```text
422 REQUEST_VALIDATION_ERROR
```

### Fallbacks seguros

Un error HTTP del framework que no tenga una clasificación funcional explícita

usa:

```text
HTTP_ERROR
```

Por ejemplo, una ruta inexistente no se etiqueta falsamente como

`DOCUMENT_NOT_FOUND`.

Cualquier excepción no controlada utiliza:

```text
500 INTERNAL_SERVER_ERROR
```

y el detalle interno se registra en Backend sin exponer stack traces ni nombres

de excepciones al cliente.

---

## Stack

\| Componente | Tecnología |

\|---|---|

\| API | FastAPI |

\| Servidor | Uvicorn |

\| Validación | Pydantic v2 |

\| Configuración | Pydantic Settings |

\| Uploads | python-multipart |

\| Cliente HTTP interno | httpx |

\| Staging temporal | Sistema de archivos local |

\| Persistencia de negocio | SQLite |

\| Persistencia futura posible | PostgreSQL / Supabase mediante nuevos adapters |

\| Object Storage | OCI Object Storage |

\| SDK Cloud | OCI Python SDK |

\| RAG / Vector Store externo | Servicio Agentes/RAG |

\| Testing | pytest / httpx |

\| Calidad | Ruff |

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
│   │           ├── documents.py
│   │           └── format_regeneration.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── adaptation.py
│   │   ├── document.py
│   │   ├── generated_format.py
│   │   └── format_regeneration.py
│   ├── domain/
│   │   ├── document.py
│   │   ├── enums.py
│   │   ├── generated_content.py
│   │   ├── generated_educational_package.py
│   │   ├── generated_format.py
│   │   ├── learning_metadata.py
│   │   └── format_evaluation.py
│   ├── application/
│   │   ├── adaptation_orchestration_service.py
│   │   ├── document_service.py
│   │   ├── rag_integration_service.py
│   │   ├── format_generation_service.py
│   │   ├── format_regeneration_service.py
│   │   ├── generated_format_query_service.py
│   │   ├── generated_package_storage_service.py
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
│   │   │   ├── http_agents_adapter.py
│   │   │   └── http_data_ia_adapter.py
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
│       ├── error_codes.py
│       ├── exceptions.py
│       ├── hashing.py
│       ├── http_exceptions.py
│       └── logging.py
├── tests/
│   ├── conftest.py
│   ├── fakes.py
│   ├── integration/
│   │   ├── test_agents_generation_integration.py
│   │   ├── test_document_download_api.py
│   │   ├── test_document_formats_api.py
│   │   ├── test_documents_api.py
│   │   ├── test_document_overwrite_behavior.py
│   │   ├── test_error_contract.py
│   │   ├── test_format_regeneration_api.py
│   │   ├── test_learning_metadata_api.py
│   │   └── test_regeneration_existing_content_api.py
│   └── unit/
│       ├── test_adaptation_orchestration_service.py
│       ├── test_application_wiring.py
│       ├── test_database.py
│       ├── test_document_domain.py
│       ├── test_document_learning_metadata.py
│       ├── test_document_indexing_state.py
│       ├── test_document_listing.py
│       ├── test_document_repository.py
│       ├── test_document_schemas.py
│       ├── test_document_service.py
│       ├── test_documents_list_api.py
│       ├── test_format_generation_service.py
│       ├── test_format_regeneration_service.py
│       ├── test_generated_content.py
│       ├── test_generated_educational_package.py
│       ├── test_generated_format_query_service.py
│       ├── test_generated_format_repository.py
│       ├── test_generated_package_storage_service.py
│       ├── test_hashing.py
│       ├── test_http_agents_adapter.py
│       ├── test_http_data_ia_adapter.py
│       ├── test_http_rag_adapter.py
│       ├── test_learning_metadata.py
│       ├── test_learning_metadata_migration.py
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
OCI_CONFIG_FILE=\~/.oci/config
OCI_CONFIG_PROFILE=DEFAULT
# --- RAG ---
RAG_BASE_URL=http://localhost:8001
RAG_INDEX_PATH=/api/v1/index
RAG_TIMEOUT_SECONDS=30
# --- Agentes ---
AGENTS_BASE_URL=http://localhost:8001
AGENTS_GENERATE_PATH=/api/v1/generate
AGENTS_TIMEOUT_SECONDS=60
# --- Data/IA ---
DATA_IA_BASE_URL=http://localhost:8002
DATA_IA_EVALUATE_PATH=/evaluate
DATA_IA_TIMEOUT_SECONDS=60
```

En despliegues Docker pueden utilizarse nombres internos de servicio, por ejemplo:

```env
RAG_BASE_URL=http://agents:8001
AGENTS_BASE_URL=http://agents:8001
DATA_IA_BASE_URL=http://data-ia:8002
```

RAG, generación y evaluación mantienen configuraciones independientes. La configuración concreta del despliegue pertenece a Infraestructura.

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

### Data/IA para pruebas integradas

Data/IA puede ejecutarse localmente en el puerto `8002`.

Desde `Data_IA/`:

```bash
python -m uvicorn data_ai.api.app:app --host 127.0.0.1 --port 8002
```

Health check:

```bash
curl http://127.0.0.1:8002/health
```

Respuesta esperada:

```json
{
  "status": "ok"
}
```

BackendAPI utiliza por defecto:

```text
http://localhost:8002/evaluate
```

---

## Tests y calidad

Ejecutar desde `backend/`:

```bash
python -m ruff check .
python -m pytest -q
git diff --check
```

Validación requerida antes de integrar cambios:

```text
python -m ruff check .
python -m pytest -q
git diff --check
```

La suite debe completarse sin errores antes de publicar el contrato actualizado.

La suite cubre, entre otros:

- carga de PDF, Markdown y TXT;
- validación de extensión y MIME;
- documentos vacíos;
- límite máximo de archivo;
- staging temporal;
- SHA-256 y deduplicación;
- reutilización del mismo `document_id` cuando el SHA-256 coincide;
- no sobrescritura cuando dos archivos comparten nombre pero tienen contenido diferente;
- persistencia simultánea de objetos OCI independientes para contenidos con SHA-256 distinto;
- persistencia de metadata técnica;
- contrato `learning_metadata` recibido desde Agentes a nivel raíz;
- validación de `key_concepts`, `prerequisites` y `estimated_time_minutes`;
- conversión HTTP → dominio mediante `LearningMetadata`;
- persistencia y reconstrucción de `learning_metadata_json`;
- migración SQLite idempotente para bases sin `learning_metadata_json`;
- exposición de `learning_metadata` mediante `GET /documents/{document_id}`;
- conservación de `learning_metadata = null` antes de disponer de una respuesta válida de Agentes;
- relación `document_id → oci_object_name`;
- almacenamiento y recuperación mediante Object Storage;
- descarga pública del archivo original mediante `GET /documents/{document_id}/download`;
- igualdad de bytes entre la respuesta HTTP y el objeto almacenado;
- conservación del `Content-Type` original;
- `Content-Disposition` con nombre original y soporte UTF-8;
- exposición CORS de `Content-Disposition`;
- errores `404`, `409` y `502` del flujo de descarga;
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
- disponibilidad posterior de Quiz y Flashcards mediante `/formats`;
- regeneración de un solo formato y de varios formatos en una misma solicitud;
- reutilización automática de `profile`, `niche`, `detail_level` y `learning_objective`;
- creación de nuevos `format_id` sin sobrescribir el historial anterior;
- rechazo `409` cuando alguno de los formatos solicitados ya está en `processing`;
- rechazo de regeneración para documentos no `INDEXED`;
- regeneración de un formato previamente `success`;
- regeneración desde estados agregados `ready` y `partial`;
- estabilidad de `learning_metadata` durante regeneraciones;
- reemplazo del fallback vacío de `learning_metadata` cuando posteriormente existe metadata útil;
- serialización del paquete educativo canónico;
- exclusión de `chunks_used` y `GenerationContext` del paquete OCI;
- selección del `success` más reciente por formato para el snapshot OCI;
- preservación del éxito previo cuando una regeneración posterior falla;
- actualización de Quiz conservando las Flashcards vigentes y viceversa;
- integración HTTP real BackendAPI → Data/IA mediante `HTTPDataIAAdapter`;
- serialización del request de evaluación;
- traducción de scores Data/IA al dominio BackendAPI;
- timeouts, errores HTTP y respuestas incompatibles de Data/IA;
- persistencia histórica de `FormatEvaluation`;
- evaluación automática después de una generación exitosa;
- conservación de `GeneratedFormat.success` cuando Data/IA falla;
- escritura directa de bytes mediante `ObjectStoragePort.upload_bytes(...)`;
- ruta canónica `documents/{document_id}/generated/content.json`;
- codificación UTF-8 y `Content-Type: application/json`;
- validación `422` para listas vacías, formatos duplicados y formatos no soportados;
- traducción a `500` cuando no es posible registrar los nuevos intentos de regeneración.
- contrato transversal `code + detail + errors[] + timestamp`;
- clasificación estable de errores `400`, `404`, `409`, `413`, `415`, `422`, `500` y `502`;
- diferenciación entre fallo de almacenamiento OCI, recuperación del original e indexación RAG;
- diferenciación de conflictos de regeneración mediante códigos funcionales;
- conservación de errores de validación por campo en `errors[]`;
- fallback `HTTP_ERROR` para errores HTTP no clasificados sin asignar causas funcionales incorrectas;
- fallback `INTERNAL_SERVER_ERROR` para excepciones no controladas.

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

### 5. Regeneración real con Agentes/Gemini

También se validó el endpoint de regeneración contra BackendAPI y el servicio real de Agentes con Gemini.

Documento utilizado:

```text
doc_0621bc23b79f4c948f25c0c53a7bd25f
```

Estado previo:

```text
document.status = indexed
quiz.status = failed
flashcards.status = failed
formats.status = error
```

Se solicitó únicamente:

```json
{
"formats": [
"quiz"
]
}
```

Backend respondió:

```text
HTTP 202 Accepted
TIME_MS=71
```

con un nuevo intento:

```json
{
"document_id": "doc_0621bc23b79f4c948f25c0c53a7bd25f",
"status": "processing",
"formats": {
"quiz": {
"format_id": "fmt_908088188f9f417fa6e3353b1239e7f7",
"status": "processing"
}
}
}
```

Un segundo `POST /formats/regenerate` inmediato para `quiz` devolvió:

```text
HTTP 409 Conflict
```

porque el nuevo intento todavía estaba activo.

La generación real terminó posteriormente con el mismo `format_id`:

```text
fmt_908088188f9f417fa6e3353b1239e7f7
processing → success
```

Como Flashcards conservaba su fallo anterior, el estado agregado pasó a:

```text
partial
```

El documento permaneció:

```text
indexed
```

por lo que la regeneración no modificó el estado de indexación.

También se comprobó la validación de duplicados:

```json
{
"formats": [
"quiz",
"quiz"
]
}
```

Resultado:

```text
HTTP 422 Unprocessable Entity
```

### Conclusión E2E

La prueba confirma:

```text
indexación síncrona                         ✅
POST responde después de INDEXED           ✅
processing se persiste antes de responder  ✅
Frontend puede observar processing         ✅
generación no bloquea POST                  ✅
timeout de Agentes es independiente         ✅
processing termina en failed               ✅
mismo format_id se conserva                ✅
documento permanece INDEXED                ✅
regeneración responde 202                   ✅
regeneración crea un nuevo format_id        ✅
segundo intento activo se rechaza con 409   ✅
regeneración real termina en success        ✅
historial previo se conserva                ✅
body con formatos duplicados devuelve 422   ✅
regeneración no reindexa el documento       ✅
```

---

### 6. Persistencia real del paquete educativo en OCI

También se validó la tarjeta de persistencia del JSON generado utilizando BackendAPI, OCI Object Storage, RAG/Agentes y Gemini reales.

Documento:

```text
doc_57c8136e661545f4be1fb06ad3df8d1f
```

Generación inicial:

```text
document.status       = indexed
formats.status        = ready
quiz.status           = success
flashcards.status     = success
```

Objetos verificados en el mismo bucket:

```text
documents/doc_57c8136e661545f4be1fb06ad3df8d1f/original.txt
documents/doc_57c8136e661545f4be1fb06ad3df8d1f/generated/content.json
```

El paquete inicial confirmó:

```text
document_id                         ✅
learning_metadata                   ✅
Quiz vigente                        ✅
Flashcards vigentes                 ✅
UTF-8                               ✅
mismo bucket OCI                    ✅
sin evaluación Data/IA en la raíz   ✅
```

Resultado:

```text
E2E OCI INICIAL: OK
```

Después se regeneró únicamente Quiz. Backend creó un nuevo `format_id` y mantuvo las Flashcards anteriores.

Estado final validado:

```text
Quiz vigente:
fmt_05f5c9bb8dfc41039699e5bfebc3e398

Flashcards vigentes:
fmt_4e90377ad0b94dc9b7bfb67939340eef
```

La comparación directa entre Backend y OCI confirmó:

```text
Metadata Backend == OCI: True
Quiz Backend == OCI: True
Flashcards Backend == OCI: True
```

Además, después de reiniciar Backend con la política de metadata estable y regenerar nuevamente solo Quiz:

```text
Metadata estable: True
```

Validación final:

```text
Metadata Backend == Metadata OCI         ✅
Quiz regenerado sincronizado con OCI     ✅
Flashcards anteriores conservadas        ✅
UTF-8 validado                           ✅

E2E METADATA ESTABLE + OCI: OK
```

La visualización `bÃ¡sicos` observada en algunas salidas de PowerShell correspondía al renderizado de consola. La comparación directa en Python entre la respuesta HTTP y los bytes UTF-8 descargados de OCI confirmó que el contenido persistido conserva correctamente los caracteres.

---

### 7. Descarga real del documento original desde OCI

También se validó de extremo a extremo el contrato público de descarga del archivo original.

Documento utilizado:

```text
document_id:
doc_57c8136e661545f4be1fb06ad3df8d1f

filename:
e2e_oci_20261007-180726.txt

objeto OCI:
documents/doc_57c8136e661545f4be1fb06ad3df8d1f/original.txt
```

El endpoint público respondió:

```text
GET /api/v1/documents/{document_id}/download
HTTP 200
Content-Type: text/plain; charset=utf-8
Content-Disposition:
attachment; filename="e2e_oci_20261007-180726.txt";
filename*=UTF-8''e2e_oci_20261007-180726.txt

bytes: 601
```

Se descargó además el mismo objeto directamente desde OCI y se compararon ambos contenidos mediante SHA-256:

```text
SHA Backend:
a156c1602b6109d23918a923f8a5e68370186c48ae222b859d35accdff450e7a

SHA OCI:
a156c1602b6109d23918a923f8a5e68370186c48ae222b859d35accdff450e7a

Bytes Backend == OCI: True
```

Resultado:

```text
Archivo recuperado desde OCI                 ✅
Bytes Backend == Bytes OCI                   ✅
SHA-256 Backend == SHA-256 OCI               ✅
Content-Type original                        ✅
Content-Disposition presente                 ✅

E2E DOWNLOAD ORIGINAL OCI: OK
```

Esta validación confirma que BackendAPI actúa como frontera pública de descarga y que Frontend no necesita acceso directo al bucket.

---

### 8. Conexión real BackendAPI → Data/IA

Primero se validó un Quiz ya generado:

```text
format_id:
fmt_05f5c9bb8dfc41039699e5bfebc3e398

status:
aprobado

relevance: 5
coherence: 5
didactic_adaptation: 5
content_support: 4
unsupported_information: False

evaluator_version: 1.0.0
rubric_version: 1.0.0
```

Resultado:

```text
Data/IA respondió                      ✅
Contrato HTTP convertido a dominio    ✅
Evaluación persistida en SQLite       ✅

E2E BACKEND -> DATA IA: OK
```

Después se validó el pipeline automático mediante una regeneración real de Quiz:

```text
format_id:
fmt_2a6208575f3a4040962b523ecf8ae651

processing → success
```

La generación exitosa disparó Data/IA y creó:

```text
evaluation_id:
eval_a710e8178d5a4e1b83c76fbd9a17e9ca

format_id:
fmt_2a6208575f3a4040962b523ecf8ae651

status:
aprobado
```

Validación:

```text
Nuevo format_id generado                  ✅
Generación terminó en success             ✅
Data/IA ejecutada después de generar      ✅
Evaluación asociada al nuevo format_id     ✅
Evaluación persistida en SQLite            ✅

E2E GENERACIÓN -> DATA IA: OK
```

Esto confirma que `evaluate` evalúa un artefacto previamente generado y no forma parte de la generación del contenido.

---

## Semántica del flujo actual para Frontend

Frontend debe separar:

```text
GET /documents/{id}
→ estado del documento / indexación
→ learning_metadata cuando esté disponible
```

de:

```text
GET /documents/{id}/formats
→ estado de generación
```

y puede recuperar el archivo fuente mediante:

```text
GET /documents/{id}/download
→ bytes del original
→ Content-Type original
→ Content-Disposition con filename
```

Frontend no debe construir URLs de OCI ni utilizar credenciales del bucket.

Flujo recomendado para la generación inicial:

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

Cuando Frontend necesite regenerar uno o varios formatos:

```text
POST /documents/{id}/formats/regenerate
↓
202 processing
↓
GET /documents/{id}/formats
↓
polling
↓
ready | partial | error
```

Frontend puede solicitar uno o varios formatos independientemente de que el estado agregado previo sea `ready`, `partial` o `error`. Backend no impide regenerar un formato porque su intento anterior haya terminado en `success`.

Si alguno de los formatos solicitados ya posee un intento `processing`, Backend responde `409` y Frontend debe continuar observando el intento existente.

No se requiere un endpoint adicional de estado.

---

## Data/IA y pendientes complementarios

### Integración Data/IA

La integración BackendAPI ↔ Data/IA está implementada.

Componentes:

```text
DataIAPort
HTTPDataIAAdapter
FormatEvaluationService
FormatEvaluationRepositoryPort
SQLiteFormatEvaluationRepositoryAdapter
```

Flujo:

```text
GeneratedFormat success
↓
FormatEvaluationService
↓
POST Data/IA /evaluate
↓
FormatEvaluation
↓
format_evaluations
```

La evaluación es best-effort respecto de la generación: un fallo de Data/IA se registra, pero no invalida contenido que Agentes ya generó correctamente.

El paquete `generated/content.json` continúa excluyendo las evaluaciones. SQLite es actualmente la fuente de verdad de `FormatEvaluation`; incluirlas en OCI requiere una decisión de contrato independiente.

### Metadata enriquecida

Los campos opcionales:

```text
title
summary
```

forman parte del contrato de detalle y actualmente pueden permanecer en `null` mientras no exista una fuente real que los calcule.

La metadata pedagógica acordada con Agentes ya está implementada mediante `learning_metadata`. El tiempo estimado de estudio se expone únicamente como `learning_metadata.estimated_time_minutes`.

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

La misma limitación aplica a las regeneraciones, ya que reutilizan `FastAPI BackgroundTasks`.

---

### Learning metadata

La estructura pedagógica ya está implementada a nivel de adaptación/documento:

```text
learning_metadata
├── key_concepts
├── prerequisites
└── estimated_time_minutes
```

Flujo actual:

```text
Agentes /generate
    ↓
learning_metadata en la raíz
    ↓
HTTPAgentsAdapter
    ↓
LearningMetadata
    ↓
Document.learning_metadata
    ↓
documents.learning_metadata_json
    ↓
GET /api/v1/documents/{document_id}
```

Agentes genera los metadatos; BackendAPI los recibe, valida, persiste y expone. No se duplican dentro de los formatos individuales.

Una vez existe metadata pedagógica útil en el documento, regenerar un formato no la reemplaza. Solo el fallback vacío oficial puede ser sustituido posteriormente por metadata útil.

`estimated_time_minutes` representa minutos estimados de estudio; no es un timeout técnico ni controla esperas entre servicios.

### Persistencia de contenido educativo en OCI

La persistencia ya está implementada mediante:

```text
GeneratedPackageStorageService
↓
ObjectStoragePort.upload_bytes(...)
↓
OCIObjectStorageAdapter
```

Ruta:

```text
documents/{document_id}/generated/content.json
```

Se utiliza el mismo bucket definido en `OCI_BUCKET_NAME`.

El objeto contiene el snapshot terminal vigente de:

```text
document_id
learning_metadata
quiz
flashcards
```

SQLite conserva el historial completo de intentos. OCI conserva la proyección educativa vigente.

Una regeneración individual reconstruye el paquete completo. Por ejemplo:

```text
antes:
Quiz v1 + Flashcards v1

regenerar Quiz:
Quiz v2 + Flashcards v1
```

Una regeneración fallida no reemplaza un `success` histórico previo dentro del snapshot OCI.

La evaluación de Data/IA permanece excluida del JSON hasta que el equipo cierre su contrato de evaluación.

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
             learning_metadata → documento
                                ↓
             mismos format_id → estado terminal
                                ↓
                   success | failed | no_results
                                ↓
              success → Data/IA /evaluate
                                ↓
                 persistir evaluación
                                ↓
              reconstruir snapshot educativo
                                ↓
 documents/{document_id}/generated/content.json
                                ↓
                        mismo bucket OCI

Frontend
   ↓
GET /api/v1/documents/{id}
   ↓
estado / learning_metadata

Frontend
   ↓
GET /api/v1/documents/{id}/download
   ↓
BackendAPI
   ↓
DocumentService.retrieve_document()
   ↓
ObjectStoragePort.download_file()
   ↓
OCI
   ↓
bytes originales + Content-Type + Content-Disposition

Frontend
   ↓
GET /api/v1/documents/{id}/formats
   ↓
pending | processing | ready | partial | error

Cuando solicita regeneración:

Frontend
   ↓
POST /api/v1/documents/{id}/formats/regenerate
   ↓
BackendAPI
   ├── validar INDEXED
   ├── rechazar si un formato solicitado sigue processing
   ├── reutilizar GenerationContext previo
   └── crear nuevos format_id en processing
   ↓
202 Accepted
   │
   └──────── background ────────┐
                                ↓
                         Agentes /generate
                                ↓
             learning_metadata estable → documento
                                ↓
             mismos nuevos format_id → estado terminal
                                ↓
              success → Data/IA /evaluate
                                ↓
                 persistir evaluación
                                ↓
               reconstruir snapshot vigente
                                ↓
                  actualizar JSON en OCI

Frontend
   ↓
GET /api/v1/documents/{id}/formats
   ↓
polling hasta ready | partial | error
```

El objetivo arquitectónico se mantiene: **Frontend conoce BackendAPI; BackendAPI orquesta; RAG/Agentes resuelve recuperación y generación; Data/IA evalúa calidad de contenido ya generado mediante un contrato desacoplado.**
