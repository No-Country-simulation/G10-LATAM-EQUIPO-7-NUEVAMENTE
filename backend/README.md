# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI**, **Pydantic v2**, **SQLite** y **OCI Object Storage**.

BackendAPI actúa como **orquestador del producto**: centraliza la comunicación con Frontend, persistencia de negocio, OCI Object Storage y los servicios externos de RAG/Agentes y Data/IA.

BackendAPI **no implementa internamente** extracción de texto, limpieza, chunking, embeddings, Vector Store, retrieval semántico, prompts, generación mediante LLM ni evaluación de calidad. Estas responsabilidades permanecen desacopladas mediante Ports y Adapters.

El frontend se encuentra en [`../frontend`](../frontend).

> Los comandos de este documento se ejecutan desde `backend/`.

---

## Estado actual

Actualmente están implementados:

### Documentos y almacenamiento

- API FastAPI y configuración central.
- Endpoint de salud.
- `POST /api/v1/documents` para cargar documentos mediante `multipart/form-data`.
- `GET /api/v1/documents/{document_id}` para consultar metadata y estado.
- `GET /api/v1/documents` para listar documentos disponibles en la biblioteca.
- `GET /api/v1/documents/{document_id}/formats` para consultar Quiz y Flashcards persistidos.
- Contrato de detalle preparado para metadata enriquecida futura mediante:
  - `title`
  - `summary`
  - `estimated_time`
- Los campos enriquecidos anteriores son opcionales y actualmente se exponen como `null` mientras no exista una fuente real para calcularlos.
- `formats_status` no forma parte del detalle del documento; `GET /api/v1/documents/{document_id}/formats` es la única fuente de verdad para disponibilidad y estado de Quiz y Flashcards.
- El contrato de `GET /api/v1/documents` permanece independiente del contrato de detalle y no incluye los campos enriquecidos anteriores.
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

### Integración HTTP BackendAPI → RAG

- Contrato interno estable mediante `RAGPort`.
- Transporte HTTP implementado mediante `HTTPRAGAdapter`.
- Endpoint externo de indexación: `POST /api/v1/index`.
- Envío `multipart/form-data` con `document_id` y `file`.
- Backend recupera el archivo desde OCI antes de enviarlo a RAG.
- RAG no recibe referencias internas de OCI ni credenciales.
- Validación de la respuesta `{"document_id": "...", "status": "indexed"}`.
- Validación de que el `document_id` retornado sea exactamente el solicitado.
- Manejo de timeout, errores HTTP, errores de conexión y respuestas incompatibles.
- Cliente HTTP desacoplado mediante configuración.
- Estados de indexación activos: `STORED → INDEXING → INDEXED`.
- Estado de fallo: `INDEXING → INDEXING_FAILED`.
- Reintento permitido desde `INDEXING_FAILED`.
- Un fallo recuperando OCI no se clasifica como fallo de RAG.
- `RAGIntegrationService` coordina recuperación desde OCI, transición de estados e invocación del puerto.

### Modelo de generación de formatos

Sprint 2 trabaja con dos formatos:

```text
quiz
flashcards
```

BackendAPI ya dispone de los contratos y persistencia necesarios para recibir resultados de Agentes.

- `FormatGenerationService` es el único caso de uso de generación.
- El servicio valida que el documento exista y esté `INDEXED`, construye el contexto pedagógico, invoca `AgentsPort`, valida la respuesta y persiste cada resultado manteniendo historial.
- Parámetros de contexto acordados:
  - `profile`
  - `niche`
  - `detail_level`
  - `learning_objective` opcional.
- `detail_level` forma parte explícita del contexto de generación.
- Una solicitud puede incluir uno o ambos formatos.
- No se permiten formatos duplicados en una misma solicitud.

### Contratos canónicos de contenido

Agentes debe devolver el contenido usando las estructuras canónicas acordadas con Data/IA.

#### QuizContent

```json
{
  "title": "Título del quiz",
  "instructions": "Instrucciones",
  "questions": [
    {
      "question_id": "q1",
      "question": "Pregunta",
      "options": ["Opción A", "Opción B"],
      "correct_answer": "Opción A",
      "explanation": "Explicación"
    }
  ]
}
```

Reglas principales:

- al menos dos opciones;
- opciones no vacías;
- opciones sin duplicados;
- `correct_answer` debe coincidir con una opción;
- `question_id` único dentro del Quiz.

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

- `front` y `back` no pueden estar vacíos;
- `front` y `back` no deben ser idénticos;
- `card_id` único dentro del conjunto.

### Evidencias utilizadas durante la generación

Agentes debe devolver las evidencias completas utilizadas durante retrieval:

```json
{
  "chunk_id": "chunk_1",
  "document_id": "doc_123",
  "rank": 1,
  "score": 0.93,
  "text": "Texto del chunk utilizado como evidencia."
}
```

Una generación exitosa debe incluir:

```text
content
+
chunks_used completos
```

BackendAPI **no consulta directamente Chroma ni el Vector Store** para reconstruir evidencias.

Esta decisión mantiene la frontera:

```text
BackendAPI
    → orquestación y persistencia de negocio

Agentes/RAG
    → retrieval y Vector Store
```

Los `chunks_used` quedan persistidos junto con la generación para conservar trazabilidad y permitir la evaluación posterior aun si cambia el Vector Store.

### Modelo de evaluación preparado

La integración HTTP efectiva con Data/IA sigue desacoplada, pero BackendAPI ya deja preparado el modelo para realizarla sin rediseñar la aplicación.

- Contrato interno mediante `DataIAPort`.
- Caso de uso mediante `FormatEvaluationService`.
- Una evaluación pertenece a una generación concreta.
- Relación `GeneratedFormat 1 → N FormatEvaluation`.
- Las evaluaciones anteriores no se sobrescriben.
- Se conserva historial.
- Campos preparados:
  - estado;
  - relevancia;
  - coherencia;
  - adaptación didáctica;
  - información respaldada;
  - indicador de información no respaldada;
  - observaciones;
  - `evaluator_version`;
  - `rubric_version`.
- Estados acordados:
  - `aprobado`
  - `requiere_revision`
  - `rechazado`

El futuro adapter HTTP de Data/IA será responsable únicamente de traducir el contrato interno hacia `POST /evaluate`.

### Consulta pública de formatos generados

BackendAPI expone actualmente:

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

Estados globales expuestos:

```text
processing
ready
partial
error
```

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

El endpoint utiliza los contratos canónicos ya acordados:

```text
formats.quiz.content.questions
formats.flashcards.content.cards
```

`correct_answer` se mantiene como el texto exacto de una opción, sin convertirlo a índice.

Actualmente, cuando el documento existe pero todavía no hay registros en `generated_formats`, el endpoint devuelve:

```json
{
  "document_id": "doc_123",
  "status": "processing",
  "formats": null
}
```

Este estado representa ausencia temporal de formatos disponibles. BackendAPI todavía no persiste un estado separado que permita distinguir entre “generación no iniciada” y “generación en ejecución”.

### Persistencia Sprint 2

SQLite contiene actualmente tres estructuras principales:

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

La persistencia de formatos generados se encuentra implementada mediante:

```text
GeneratedFormatRepositoryPort
    ↑
SQLiteGeneratedFormatRepositoryAdapter
```

El repositorio permite:

- persistir una generación mediante `create()`;
- recuperar una generación concreta mediante `find_by_id(format_id)`;
- recuperar las generaciones asociadas a un documento mediante `find_by_document_id(document_id)`;
- conservar múltiples generaciones del mismo tipo para un mismo documento;
- persistir resultados exitosos, fallidos o sin resultados;
- reconstruir desde SQLite el contenido canónico, el contexto pedagógico y las evidencias utilizadas.

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

Una generación exitosa conserva en la BD:

```text
GeneratedFormat
├── QuizContent | FlashcardsContent
├── GenerationContext
└── chunks_used
```

No existe una restricción única por:

```text
document_id + format_type
```

por lo que BackendAPI mantiene historial de generaciones:

```text
document
    ├── quiz generación 1
    ├── quiz generación 2
    └── flashcards generación 1
```

La integridad referencial se mantiene mediante:

```text
generated_formats.document_id
→ documents.document_id
```

El adapter distingue explícitamente entre:

- `GeneratedFormatAlreadyExistsError`, cuando `format_id` ya existe;
- `GeneratedFormatDocumentNotFoundError`, cuando el `document_id` asociado no existe;
- `GeneratedFormatRepositoryError`, para otros errores de persistencia.

La persistencia fue validada tanto mediante pruebas automatizadas como mediante una prueba manual sobre SQLite real, comprobando:

```text
Document
→ GeneratedFormat Quiz
→ GeneratedFormat Flashcards
→ SQLite
→ find_by_id()
→ find_by_document_id()
→ reconstrucción correcta del dominio
```

`format_evaluations` conserva:

```text
evaluation_id
format_id
status
relevance_score
coherence_score
didactic_adaptation_score
content_support_score
unsupported_information
observations_json
evaluator_version
rubric_version
created_at
```

La relación:

```text
GeneratedFormat 1 → N FormatEvaluation
```

permite conservar historial de evaluaciones sin sobrescribir resultados anteriores.

---

## Cambios recientes

Los últimos cambios relevantes de BackendAPI consolidan siete frentes.

### 1. Estandarización de Ports y Adapters

Convención actual:

```text
ports/
├── agents_port.py                → AgentsPort
├── document_repository_port.py   → DocumentRepositoryPort
├── object_storage_port.py        → ObjectStoragePort
├── rag_port.py                   → RAGPort
└── temporary_storage_port.py     → TemporaryStoragePort
```

Implementaciones concretas:

```text
infrastructure/
├── integrations/
│   └── http_rag_adapter.py
│       └── HTTPRAGAdapter
├── persistence/
│   ├── sqlite_document_repository_adapter.py
│   ├── sqlite_generated_format_repository_adapter.py
│   └── sqlite_format_evaluation_repository_adapter.py
└── storage/
    ├── local_temporary_storage_adapter.py
    └── oci_object_storage_adapter.py
```

Los módulos usan `snake_case` y las clases `CapWords`.

### 2. Integración HTTP con RAG

Se sustituyó el adapter provisional por `HTTPRAGAdapter`.

```text
document_id
    ↓
SQLite
    ↓
oci_object_name
    ↓
OCI Object Storage
    ↓
bytes originales
    ↓
RAGIntegrationService
    ↓
RAGPort
    ↓
HTTPRAGAdapter
    ↓
POST /api/v1/index
```

### 3. Modelo de formatos y evaluaciones

Se incorporaron:

```text
GeneratedFormat
GenerationContext
ChunkEvidence
QuizContent
FlashcardsContent
FormatEvaluation
EvaluationScores
```

junto con sus Ports, repositories y servicios de aplicación.

`AdaptationService` fue retirado para evitar solapamiento. La generación queda centralizada en `FormatGenerationService` y la evaluación en `FormatEvaluationService`.

### 4. Persistencia validada de formatos generados

La persistencia de Quiz y Flashcards quedó validada sobre SQLite real.

Se verificó:

```text
create()
find_by_id()
find_by_document_id()
```

incluyendo:

- round-trip de `QuizContent`;
- round-trip de `FlashcardsContent`;
- persistencia de `GenerationContext`;
- persistencia de `chunks_used`;
- historial de múltiples generaciones para el mismo documento;
- persistencia de resultados fallidos;
- errores explícitos ante `format_id` duplicado;
- errores explícitos ante `document_id` inexistente.

### 5. Persistencia validada de documentos y ruta OCI

La relación entre el identificador canónico del documento y su ubicación lógica en Object Storage quedó validada usando `DocumentService`, `SQLiteDocumentRepositoryAdapter` y un `ObjectStoragePort` de prueba.

Flujo comprobado:

```text
archivo local
   ↓
DocumentService.register_document()
   ↓
documents.document_id
   ↓
DocumentService.store_document()
   ↓
documents/{document_id}/original.ext
   ↓
documents.oci_object_name
   ↓
SQLite
```

La validación manual confirmó que, después del almacenamiento:

```text
status = stored
document_id = doc_...
oci_object_name = documents/doc_.../original.ext
```

y que el objeto asociado existe en Object Storage.

Esto garantiza que BackendAPI conserva en la BD de negocio la referencia necesaria para recuperar posteriormente el archivo original sin persistir rutas locales temporales.

### 6. Contrato de detalle de documento preparado para Frontend

El contrato HTTP de detalle quedó preparado para metadata enriquecida futura sin modificar el contrato ya cerrado del listado de biblioteca.

`GET /api/v1/documents/{document_id}` expone:

```json
{
  "document_id": "doc_123",
  "filename": "manual.pdf",
  "status": "indexed",
  "content_type": "application/pdf",
  "size_bytes": 1024,
  "created_at": "2026-09-30T12:00:00Z",
  "updated_at": "2026-09-30T12:05:00Z",
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

son opcionales y actualmente permanecen en `null` hasta que exista una fuente real para calcularlos.

`formats_status` se excluye deliberadamente de este recurso. La disponibilidad y el estado de Quiz y Flashcards pertenecerán a:

```text
GET /api/v1/documents/{document_id}/formats
```

De esta forma se evita mantener dos representaciones potencialmente inconsistentes del estado de generación.

El contrato de biblioteca permanece independiente:

```text
GET /api/v1/documents
```

y continúa exponiendo solamente la metadata base de cada documento.

### 7. Consulta pública de formatos para Frontend

Se incorporó el endpoint:

```text
GET /api/v1/documents/{document_id}/formats
```

junto con:

```text
GeneratedFormatQueryService
DocumentFormatsStatus
DocumentFormatsResponse
GeneratedFormatResponse
QuizContentResponse
FlashcardsContentResponse
```

La consulta no genera contenido ni llama a Agentes. Su responsabilidad es leer el historial persistido y construir la representación actual para Frontend.

Se preserva historial en SQLite, pero el endpoint expone un único resultado vigente por tipo.

Los estados agregados disponibles son:

```text
processing
ready
partial
error
```

La implementación fue validada con pruebas automatizadas y manuales sobre SQLite real.

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
| Persistencia futura posible | PostgreSQL / Supabase |
| Object Storage | OCI Object Storage |
| SDK Cloud | OCI Python SDK |
| Testing | pytest / httpx |
| Calidad | Ruff |

El proyecto soporta **Python 3.11 o superior**.

---

## Arquitectura

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
| `api/` | Endpoints HTTP y dependencias FastAPI |
| `schemas/` | Contratos externos de entrada y salida |
| `domain/` | Entidades, estados y reglas de dominio |
| `application/` | Casos de uso y orquestación |
| `ports/` | Contratos hacia persistencia e integraciones |
| `infrastructure/` | Adapters e implementaciones concretas |
| `core/` | Configuración, logging, errores y utilidades |

### Principio de fronteras

```text
Frontend
    ↓
BackendAPI
    ├── SQLite
    ├── OCI Object Storage
    ├── RAG / Agentes
    └── Data/IA
```

BackendAPI es el orquestador y único punto de entrada del Frontend.

RAG/Agentes:

- no accede directamente a la BD de negocio;
- no necesita acceder directamente a OCI;
- es responsable de extracción, chunking, embeddings, retrieval y generación.

Data/IA:

- evalúa la calidad del contenido generado;
- recibe el contenido, evidencias y contexto pedagógico;
- no administra documentos ni realiza generación.

---

## Flujo de carga e indexación

```text
Frontend
   ↓
POST /api/v1/documents
   ↓
TemporaryStoragePort
   ↑
LocalTemporaryStorageAdapter
   ↓
archivo temporal
   ↓
DocumentService.register_document()
   ├── SHA-256
   ├── deduplicación
   ├── document_id
   └── metadata → SQLite
   ↓
DocumentService.store_document()
   ↓
ObjectStoragePort
   ↑
OCIObjectStorageAdapter
   ↓
OCI
   ↓
metadata final → SQLite
   ↓
eliminación del temporal
```

Posteriormente:

```text
document_id
   ↓
DocumentService.retrieve_document()
   ↓
OCI
   ↓
bytes originales
   ↓
RAGIntegrationService
   ↓
STORED → INDEXING
   ↓
HTTPRAGAdapter
   ↓
POST /api/v1/index
   ↓
RAG
   ↓
{"document_id": "...", "status": "indexed"}
   ↓
INDEXING → INDEXED
```

Si la llamada RAG falla:

```text
INDEXING → INDEXING_FAILED
```

---

## Contrato BackendAPI → RAG

### Endpoint externo

```text
POST /api/v1/index
Content-Type: multipart/form-data
```

Partes:

```text
document_id
file
```

`file` contiene `filename`, `content_type` y bytes originales.

Respuesta esperada:

```json
{
  "document_id": "doc_123",
  "status": "indexed"
}
```

BackendAPI no envía información interna de OCI ni de la BD.

---

## Flujo de generación

La generación es independiente de la indexación.

```text
documento INDEXED
   ↓
FormatGenerationService
   ↓
AgentsPort
   ↓
Agentes /generate
   ↓
QuizContent / FlashcardsContent
+ chunks_used completos
   ↓
GeneratedFormat
   ↓
GeneratedFormatRepositoryPort
   ↓
SQLite
```

Contrato conceptual de solicitud:

```json
{
  "document_id": "doc_123",
  "formats": ["quiz", "flashcards"],
  "profile": "beginner",
  "niche": "technology",
  "detail_level": "detailed",
  "learning_objective": "Opcional"
}
```

---

## Flujo de evaluación preparado

Cuando Data/IA habilite la integración definitiva:

```text
GeneratedFormat persistido
   ↓
FormatEvaluationService
   ↓
DataIAPort
   ↓
HTTPDataIAAdapter
   ↓
POST /evaluate
   ↓
resultado
   ↓
FormatEvaluationRepositoryPort
   ↓
SQLite
```

BackendAPI ya conserva todo lo necesario para armar la evaluación:

```text
document_id
format
generated_content
chunks_used completos
profile
niche
detail_level
learning_objective?
```

---

## Validación E2E BackendAPI → RAG

La integración real de indexación fue validada end-to-end utilizando un documento PDF persistido previamente en OCI.

Flujo comprobado:

```text
document_id
→ metadata SQLite
→ recuperación del archivo desde OCI
→ RAGIntegrationService
→ HTTPRAGAdapter
→ POST /api/v1/index
→ multipart/form-data
→ RAG / Chroma
→ HTTP 200
→ INDEXING → INDEXED
```

La prueba confirmó que BackendAPI conserva la responsabilidad sobre OCI y entrega a RAG únicamente el archivo original y el `document_id` canónico.

---

## Estructura actual

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── dependencies.py
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── health.py
│   │           ├── documents.py
│   │           ├── adaptations.py
│   │           └── processes.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── document.py
│   │   ├── generated_format.py
│   │   ├── adaptation.py
│   │   └── process.py
│   ├── domain/
│   │   ├── document.py
│   │   ├── process.py
│   │   ├── generated_content.py
│   │   ├── generated_format.py
│   │   ├── format_evaluation.py
│   │   └── enums.py
│   ├── application/
│   │   ├── document_service.py
│   │   ├── rag_integration_service.py
│   │   ├── format_generation_service.py
│   │   ├── generated_format_query_service.py
│   │   ├── format_evaluation_service.py
│   │   └── process_service.py
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
│   │   ├── persistence/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── repository_factory.py
│   │   │   ├── sqlite_document_repository_adapter.py
│   │   │   ├── sqlite_generated_format_repository_adapter.py
│   │   │   └── sqlite_format_evaluation_repository_adapter.py
│   │   ├── storage/
│   │   │   ├── local_temporary_storage_adapter.py
│   │   │   └── oci_object_storage_adapter.py
│   │   └── integrations/
│   │       └── http_rag_adapter.py
│   └── core/
│       ├── config.py
│       ├── exceptions.py
│       ├── logging.py
│       └── hashing.py
├── tests/
│   ├── conftest.py
│   ├── fakes.py
│   ├── unit/
│   │   ├── test_document_service.py
│   │   ├── test_document_indexing_state.py
│   │   ├── test_document_schemas.py
│   │   ├── test_documents_list_api.py
│   │   ├── test_rag_integration_service.py
│   │   ├── test_http_rag_adapter.py
│   │   ├── test_format_generation_service.py
│   │   ├── test_generated_format_query_service.py
│   │   └── test_generated_format_repository.py
│   └── integration/
│       ├── test_documents_api.py
│       └── test_document_formats_api.py
├── storage/                         # local, ignorado por Git
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Endpoints públicos actuales

### Salud

```text
GET /api/v1/health
```

### Cargar documento

```text
POST /api/v1/documents
Content-Type: multipart/form-data
Campo: file
```

Formatos soportados:

```text
.pdf
.md
.txt
```

### Listar documentos disponibles

```text
GET /api/v1/documents
```

Contrato actual:

```json
{
  "documents": [
    {
      "document_id": "doc_123",
      "filename": "manual.pdf",
      "status": "indexed",
      "content_type": "application/pdf",
      "size_bytes": 1024,
      "created_at": "2026-09-30T12:00:00Z",
      "updated_at": "2026-09-30T12:05:00Z"
    }
  ]
}
```

### Consultar documento

```text
GET /api/v1/documents/{document_id}
```

Contrato actual:

```json
{
  "document_id": "doc_123",
  "filename": "manual.pdf",
  "status": "indexed",
  "content_type": "application/pdf",
  "size_bytes": 1024,
  "created_at": "2026-09-30T12:00:00Z",
  "updated_at": "2026-09-30T12:05:00Z",
  "title": null,
  "summary": null,
  "estimated_time": null
}
```

Los campos `title`, `summary` y `estimated_time` forman parte del contrato público, pero su cálculo o enriquecimiento todavía no está implementado.

`formats_status` no forma parte de este endpoint.

### Consultar formatos de un documento

```text
GET /api/v1/documents/{document_id}/formats
```

Ejemplo sin formatos disponibles:

```json
{
  "document_id": "doc_123",
  "status": "processing",
  "formats": null
}
```

Ejemplo con Quiz y Flashcards disponibles:

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
            "options": ["Opción A", "Opción B"],
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

La generación y evaluación continúan siendo casos de uso internos. Este endpoint solo consulta resultados previamente persistidos.

---

## Configuración local

Crear `.env` a partir de `.env.example`.

Variables principales:

```env
PROJECT_NAME="NuevaMente API"
ENVIRONMENT=local
DEBUG=true

API_V1_PREFIX=/api/v1

HOST=0.0.0.0
PORT=8000

BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

MAX_UPLOAD_SIZE_MB=10
UPLOAD_DIR=storage/uploads

DATABASE_URL=sqlite:///storage/nuevamente.db

OCI_NAMESPACE=
OCI_BUCKET_NAME=
OCI_REGION=
OCI_CONFIG_FILE=~/.oci/config
OCI_CONFIG_PROFILE=DEFAULT

RAG_BASE_URL=http://localhost:8001
RAG_INDEX_PATH=/api/v1/index
RAG_TIMEOUT_SECONDS=30
```

BackendAPI utiliza el puerto `8000` en desarrollo local. RAG debe usar otro puerto cuando ambos se ejecuten en la misma máquina, por ejemplo `8001`.

No versionar credenciales ni claves privadas.

---

## Ejecución local

Desde `backend/`:

```bash
python -m venv .venv
```

Activar el entorno virtual e instalar dependencias:

```bash
pip install -r requirements-dev.txt
```

Levantar BackendAPI:

```bash
python -m uvicorn app.main:app --reload
```

Disponible en:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## Tests y calidad

Ejecutar:

```bash
python -m ruff check app tests
python -m pytest
```

Última validación local:

```text
Ruff: All checks passed!
Pytest: 93 passed
```

La suite cubre, entre otros:

- carga de PDF, Markdown y TXT;
- validación de extensión y MIME;
- documentos vacíos;
- límite máximo de archivo;
- staging temporal;
- SHA-256 y deduplicación;
- persistencia de metadata;
- persistencia de `document_id` y `oci_object_name` en SQLite;
- reconstrucción desde BD de la relación `document_id → ruta lógica OCI`;
- almacenamiento y recuperación mediante OCI/Object Storage;
- compensación ante inconsistencia OCI/BD;
- transiciones de indexación;
- reintentos desde `INDEXING_FAILED`;
- multipart HTTP hacia RAG;
- timeouts y errores HTTP;
- validación del `document_id` devuelto por RAG;
- generación de Quiz y Flashcards;
- contexto pedagógico de generación;
- contrato canónico `QuizContent`;
- contrato canónico `FlashcardsContent`;
- evidencias `chunks_used`;
- rechazo de respuestas incompletas o asociadas a otro documento;
- persistencia SQLite de Quiz y Flashcards;
- recuperación de generaciones mediante `format_id`;
- recuperación de generaciones mediante `document_id`;
- round-trip de `QuizContent` y `FlashcardsContent`;
- persistencia y reconstrucción de `GenerationContext`;
- persistencia y reconstrucción de `chunks_used`;
- historial de múltiples generaciones del mismo tipo;
- persistencia de generaciones fallidas;
- rechazo explícito de `format_id` duplicado;
- rechazo explícito de formatos asociados a documentos inexistentes;
- modelo y persistencia preparados para evaluaciones;
- contrato HTTP del detalle de documento;
- presencia de `title`, `summary` y `estimated_time` como metadata opcional;
- exclusión de `formats_status` del detalle del documento;
- separación entre el contrato de listado y el contrato de detalle;
- consulta de formatos mediante `GET /documents/{document_id}/formats`;
- estado agregado `processing`, `ready`, `partial` y `error`;
- estados por formato `success`, `failed` y `no_results`;
- selección de la generación exitosa más reciente por tipo;
- conservación de un éxito previo frente a un reintento posterior fallido;
- contrato HTTP canónico de Quiz y Flashcards;
- respuesta 404 para documentos inexistentes.

La BD fue validada manualmente para comprobar las tablas:

```text
documents
generated_formats
format_evaluations
```

y las Foreign Keys:

```text
generated_formats.document_id
→ documents.document_id

format_evaluations.format_id
→ generated_formats.format_id
```

También se realizó una validación manual de persistencia sobre una base SQLite aislada. Se persistieron un Quiz y un conjunto de Flashcards asociados al mismo `document_id` y posteriormente se recuperaron mediante:

```text
find_by_id()
find_by_document_id()
```

La prueba confirmó la reconstrucción correcta de:

```text
format_id
format_type
status
content
chunks_used
generation_context
```

Adicionalmente, se validó manualmente la persistencia del documento y su ruta lógica en Object Storage. El flujo creó un `document_id`, almacenó el archivo y volvió a consultar el registro desde SQLite.

Resultado comprobado:

```text
Document ID: doc_...
Estado: stored
Ruta OCI: documents/doc_.../original.ext
Existe en Object Storage: True
```

También se realizó una validación HTTP manual del contrato de detalle usando un documento real previamente indexado.

Se comprobó:

```text
GET /api/v1/documents/{document_id}
→ status = indexed
→ title = null
→ summary = null
→ estimated_time = null
→ formats_status ausente
```

y posteriormente:

```text
GET /api/v1/documents
```

continuó devolviendo únicamente la metadata base, sin incorporar `title`, `summary`, `estimated_time` ni `formats_status`.

Esta prueba confirma que el contrato de detalle puede evolucionar de forma independiente sin modificar el contrato de biblioteca ya integrado por Frontend.

También se validó manualmente `GET /api/v1/documents/{document_id}/formats` usando un documento real previamente indexado.

Primero, sin formatos persistidos:

```text
HTTP 200
status = processing
formats = null
```

Para un `document_id` inexistente:

```text
HTTP 404
detail = "No existe el documento doc_inexistente."
```

Después se persistieron temporalmente en SQLite un Quiz y un conjunto de Flashcards exitosos asociados al mismo documento.

La consulta confirmó:

```text
HTTP 200
status = ready
formats.quiz.status = success
formats.flashcards.status = success
formats.quiz.content.questions
formats.flashcards.content.cards
correct_answer = texto exacto de la opción
```

Los registros manuales fueron eliminados al finalizar la validación y una nueva consulta volvió a:

```text
status = processing
formats = null
```

Esto confirmó que el endpoint consulta el estado actual de SQLite y no conserva resultados en memoria.

---

## Pendientes

### Backend → Agentes

Pendiente implementar el adapter HTTP concreto de generación:

```text
AgentsPort
    ↑
HTTPAgentsAdapter
    ↓
POST /api/v1/generate
```

El contrato acordado debe entregar:

```text
document_id
results[]
 ├── format
 ├── status
 ├── content canónico
 └── chunks_used completos
```

### Backend → Data/IA

Pendiente implementar:

```text
DataIAPort
    ↑
HTTPDataIAAdapter
    ↓
POST /evaluate
```

El modelo y el caso de uso ya están preparados.

### API pública de orquestación

Pendiente exponer el flujo que utilizará Frontend para:

- solicitar generación;
- incorporar `detail_level` en el contrato Frontend → Backend;
- poblar posteriormente `title`, `summary` y `estimated_time` cuando exista una fuente real para generar esos valores.

### Otros pendientes

- Integración end-to-end con `/generate`.
- Integración opcional con Data/IA.
- Motor de persistencia alternativo si despliegue lo requiere.

---

## Lineamientos de desarrollo

- Mantener módulos y funciones con una única responsabilidad.
- Separar HTTP, aplicación, dominio, persistencia e integraciones externas.
- Evitar dependencias directas desde `application/` hacia implementaciones de `infrastructure/`.
- Usar Ports como contratos estables.
- Usar Adapters para tecnología externa concreta.
- Mantener nombres de módulos en `snake_case` y clases en `CapWords`.
- Manejar errores explícitamente.
- Evitar duplicación de lógica.
- Documentar contratos y decisiones no evidentes.
- Acompañar nuevas funcionalidades con pruebas.
- Mantener `document_id` como identificador canónico entre Backend, OCI, RAG, Agentes, formatos y evaluaciones.
- No permitir que Backend acceda directamente al Vector Store de Agentes.
- No permitir que Agentes acceda directamente a OCI ni a la BD de negocio.
- No versionar credenciales ni configuración sensible.
