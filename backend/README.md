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
- Validación de la respuesta:

```json
{
  "document_id": "doc_123",
  "status": "indexed"
}
```

- Validación de que el `document_id` retornado sea exactamente el solicitado.
- Manejo de timeout, errores HTTP, errores de conexión y respuestas incompatibles.
- Cliente HTTP desacoplado mediante configuración.
- Estados de indexación activos: `STORED → INDEXING → INDEXED`.
- Estado de fallo: `INDEXING → INDEXING_FAILED`.
- Reintento permitido desde `INDEXING_FAILED`.
- Un fallo recuperando OCI no se clasifica como fallo de RAG.
- `RAGIntegrationService` coordina recuperación desde OCI, transición de estados e invocación del puerto.

> La integración con RAG está implementada, pero el flujo público de `POST /api/v1/documents` todavía no dispara automáticamente la indexación. Esa conexión pertenece a la tarjeta final de orquestación.

### Integración HTTP BackendAPI → Agentes

La integración de generación se encuentra implementada mediante la separación:

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

El adapter concreto:

```text
HTTPAgentsAdapter
```

es responsable únicamente de:

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

En desarrollo local puede utilizarse:

```text
http://localhost:8001
```

mientras que en despliegues con Docker puede configurarse, por ejemplo:

```text
http://agents:8001
```

sin modificar código de aplicación.

### Modelo de generación de formatos

Sprint 2 trabaja con dos formatos:

```text
quiz
flashcards
```

BackendAPI dispone de los contratos, integración HTTP y persistencia necesarios para recibir resultados de Agentes.

- `FormatGenerationService` es el único caso de uso de generación.
- El servicio valida que el documento exista y esté `INDEXED`.
- Construye el contexto pedagógico.
- Invoca `AgentsPort`.
- Valida que el `document_id` retornado coincida con el solicitado.
- Valida que Agentes retorne exactamente los formatos solicitados.
- Rechaza formatos duplicados.
- Convierte cada resultado en `GeneratedFormat`.
- Persiste cada generación manteniendo historial.
- Un fallo de comunicación con Agentes se traduce mediante `FormatGenerationIntegrationError`.

Parámetros de contexto:

```text
profile
niche
detail_level
learning_objective opcional
```

Una solicitud puede incluir uno o ambos formatos.

No se permiten formatos duplicados dentro de una misma solicitud.

### Contrato BackendAPI → Agentes

Solicitud HTTP esperada:

```json
{
  "document_id": "doc_123",
  "formats": [
    "quiz",
    "flashcards"
  ],
  "profile": "beginner",
  "niche": "technology",
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

Estados soportados por formato:

```text
success
failed
no_results
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

Agentes debe devolver el contenido usando las estructuras canónicas acordadas entre Backend, Frontend y Data/IA.

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

Agentes devuelve las evidencias completas utilizadas durante retrieval:

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

La frontera se mantiene:

```text
BackendAPI
    → orquestación y persistencia de negocio

Agentes/RAG
    → extracción, retrieval, Vector Store y generación
```

Los `chunks_used` quedan persistidos junto con la generación para conservar trazabilidad y permitir evaluación posterior aun si cambia el Vector Store.

### Consulta pública de formatos generados

BackendAPI expone:

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

Criterio de selección:

```text
si existe al menos una generación exitosa
→ se expone la exitosa más reciente

si nunca existió una generación exitosa
→ se expone el intento más reciente
```

El endpoint utiliza los contratos canónicos:

```text
formats.quiz.content.questions
formats.flashcards.content.cards
```

`correct_answer` se mantiene como texto exacto de una opción.

Cuando el documento existe pero todavía no hay generaciones persistidas:

```json
{
  "document_id": "doc_123",
  "status": "processing",
  "formats": null
}
```

Actualmente BackendAPI no persiste un estado separado que permita distinguir entre:

```text
generación no iniciada
```

y:

```text
generación actualmente en ejecución
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

La persistencia de formatos generados se implementa mediante:

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

La integración HTTP efectiva con Data/IA permanece desacoplada, pero BackendAPI dispone del modelo necesario para incorporarla sin rediseñar generación ni persistencia.

- Contrato interno mediante `DataIAPort`.
- Caso de uso mediante `FormatEvaluationService`.
- Una evaluación pertenece a una generación concreta.
- Relación `GeneratedFormat 1 → N FormatEvaluation`.
- Las evaluaciones anteriores no se sobrescriben.
- Se conserva historial.

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
- no administra documentos persistidos;
- es responsable de extracción, chunking, embeddings, retrieval y generación.

Data/IA:

- evalúa calidad del contenido generado;
- recibe contenido, evidencias y contexto;
- no administra documentos;
- no genera material educativo.

---

## Flujo de almacenamiento

Actualmente `POST /api/v1/documents` implementa:

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
STORED
   ↓
eliminación del temporal
```

El endpoint actualmente finaliza después de la persistencia en OCI.

La conexión automática:

```text
STORED
→ RAG
→ INDEXED
```

pertenece a la tarjeta final de orquestación.

---

## Flujo de indexación disponible

`RAGIntegrationService` ya implementa:

```text
document_id
   ↓
DocumentService.retrieve_document()
   ↓
OCI
   ↓
bytes originales
   ↓
STORED → INDEXING
   ↓
RAGPort
   ↑
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

Ante fallo:

```text
INDEXING → INDEXING_FAILED
```

---

## Flujo de generación disponible

Para un documento previamente `INDEXED`:

```text
document_id
   ↓
FormatGenerationService
   ↓
AgentsPort
   ↑
HTTPAgentsAdapter
   ↓
POST /api/v1/generate
   ↓
results[]
   ├── Quiz
   └── Flashcards
   ↓
validación de contrato
   ↓
GeneratedFormat
   ↓
GeneratedFormatRepositoryPort
   ↑
SQLiteGeneratedFormatRepositoryAdapter
   ↓
SQLite
```

La generación ya se encuentra completamente implementada a nivel de aplicación e infraestructura.

Todavía no existe un endpoint público que dispare esta operación desde Frontend. Esa exposición forma parte de la tarjeta final de orquestación.

---

## Validaciones realizadas

### BackendAPI → RAG

La integración real de indexación fue validada previamente end-to-end utilizando un documento persistido en OCI.

Flujo comprobado:

```text
document_id
→ metadata SQLite
→ OCI
→ RAGIntegrationService
→ HTTPRAGAdapter
→ POST /api/v1/index
→ RAG / Chroma
→ HTTP 200
→ INDEXING → INDEXED
```

### BackendAPI → Agentes

El adapter HTTP fue validado mediante pruebas automatizadas para:

- request canónico;
- Quiz exitoso;
- Flashcards exitosas;
- `learning_objective` opcional;
- `no_results`;
- mapeo de `sources_used`;
- contenido canónico inválido;
- errores HTTP;
- timeout.

También se implementó una prueba de integración que atraviesa:

```text
FormatGenerationService
→ HTTPAgentsAdapter
→ POST /api/v1/generate simulado
→ AgentGenerationResult
→ GeneratedFormat
→ SQLiteGeneratedFormatRepositoryAdapter
→ SQLite
→ find_by_document_id()
```

La prueba utiliza el adapter HTTP real de BackendAPI y persistencia SQLite real. Únicamente se sustituye el servidor externo de Agentes mediante `httpx.MockTransport`.

Esto valida conjuntamente:

```text
Application
+
Port
+
HTTP Adapter
+
Domain
+
Persistence Adapter
+
SQLite
```

La prueba end-to-end contra el servicio real de Agentes puede ejecutarse cuando el contrato de su rama Sprint 2 se encuentre disponible en el entorno compartido correspondiente.

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
│   │   ├── test_documents_api.py
│   │   ├── test_document_formats_api.py
│   │   └── test_agents_generation_integration.py
│   └── unit/
│       ├── test_application_wiring.py
│       ├── test_document_service.py
│       ├── test_document_indexing_state.py
│       ├── test_document_schemas.py
│       ├── test_documents_list_api.py
│       ├── test_rag_integration_service.py
│       ├── test_http_rag_adapter.py
│       ├── test_http_agents_adapter.py
│       ├── test_format_generation_service.py
│       ├── test_generated_format_query_service.py
│       └── test_generated_format_repository.py
├── storage/
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

Actualmente este endpoint:

```text
valida
→ registra
→ persiste en OCI
→ retorna
```

No dispara todavía la indexación automática.

### Listar documentos

```text
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
      "created_at": "2026-09-30T12:00:00Z",
      "updated_at": "2026-09-30T12:05:00Z"
    }
  ]
}
```

### Consultar detalle

```text
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
  "created_at": "2026-09-30T12:00:00Z",
  "updated_at": "2026-09-30T12:05:00Z",
  "title": null,
  "summary": null,
  "estimated_time": null
}
```

`formats_status` no forma parte de este contrato.

### Consultar formatos

```text
GET /api/v1/documents/{document_id}/formats
```

Sin formatos:

```json
{
  "document_id": "doc_123",
  "status": "processing",
  "formats": null
}
```

Con resultados disponibles:

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

La generación sigue siendo actualmente un caso de uso interno de BackendAPI. No existe todavía un endpoint público de generación.

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

No versionar credenciales ni claves privadas.

---

## Ejecución local

Desde `backend/`:

```bash
python -m venv .venv
```

Activar el entorno e instalar dependencias:

```bash
pip install -r requirements-dev.txt
```

Levantar BackendAPI:

```bash
python -m uvicorn app.main:app --reload
```

Backend:

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
Pytest: 102 passed
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
- inicialización de `FormatGenerationService` en el lifespan;
- generación mediante `FormatGenerationService`;
- persistencia SQLite de los resultados recibidos vía HTTP;
- lectura posterior de esos resultados desde SQLite;
- contexto pedagógico de generación;
- persistencia y reconstrucción de `chunks_used`;
- historial de generaciones;
- persistencia de generaciones fallidas;
- rechazo de `format_id` duplicado;
- rechazo de referencias a documentos inexistentes;
- consulta pública de formatos;
- estados `processing`, `ready`, `partial` y `error`;
- conservación de éxito previo frente a reintento fallido;
- contrato de detalle de documento;
- separación entre listado, detalle y formatos.

---

## Estado de la integración Sprint 2

Actualmente las piezas están disponibles de forma independiente:

```text
Carga
POST /documents
    ↓
SQLite + OCI
    ↓
STORED
```

```text
Indexación
RAGIntegrationService
    ↓
HTTPRAGAdapter
    ↓
POST /api/v1/index
    ↓
INDEXED
```

```text
Generación
FormatGenerationService
    ↓
HTTPAgentsAdapter
    ↓
POST /api/v1/generate
    ↓
GeneratedFormat
    ↓
SQLite
```

```text
Consulta
GET /documents/{document_id}/formats
    ↓
GeneratedFormatQueryService
    ↓
Quiz / Flashcards
```

Las piezas están desacopladas y probadas.

Lo que todavía falta es conectarlas dentro de un único flujo coordinado.

---

## Última tarjeta funcional: orquestación

La siguiente tarjeta debe unir las capacidades existentes sin duplicar lógica:

```text
Frontend
   ↓
BackendAPI
   ↓
POST /documents
   ↓
OCI
   ↓
RAG /index
   ↓
INDEXED
   ↓
Agentes /generate
   ↓
Quiz + Flashcards
   ↓
SQLite
   ↓
GET /documents/{id}/formats
```

La implementación deberá reutilizar:

```text
DocumentService
RAGIntegrationService
FormatGenerationService
```

y no trasladar lógica de negocio a los endpoints.

También deberá cerrar el contrato público necesario para proporcionar:

```text
profile
niche
detail_level
formats
learning_objective?
```

sin inventar valores silenciosamente dentro del Backend.

Actualmente Frontend dispone de parámetros equivalentes a:

```text
target_profile
niche_context
output_format
```

pero `detail_level` todavía debe resolverse explícitamente dentro del contrato Frontend → Backend.

Esta tarjeta también deberá definir el comportamiento ante:

- fallo de indexación;
- generación parcial;
- `no_results`;
- error de un único formato;
- reintento de un formato fallido;
- documentos duplicados previamente indexados;
- documentos almacenados pero todavía no indexados.

---

## Pendientes posteriores / complementarios

### Data/IA

El modelo interno está preparado mediante:

```text
DataIAPort
FormatEvaluationService
FormatEvaluationRepositoryPort
```

La integración HTTP concreta dependerá del endpoint funcional disponible en Data/IA.

### Metadata enriquecida

Los campos:

```text
title
summary
estimated_time
```

ya forman parte del contrato de detalle, pero actualmente permanecen en `null`.

### Persistencia alternativa

SQLite es el motor actual de desarrollo. Un motor adicional puede incorporarse mediante nuevos adapters sin modificar los casos de uso.

---

## Lineamientos de desarrollo

- Mantener módulos y funciones con una única responsabilidad.
- Separar HTTP, aplicación, dominio, persistencia e integraciones externas.
- Evitar dependencias directas desde `application/` hacia implementaciones de `infrastructure/`.
- Usar Ports como contratos estables.
- Usar Adapters para tecnologías externas.
- Mantener nombres de módulos en `snake_case` y clases en `CapWords`.
- Manejar errores explícitamente.
- Evitar duplicación de lógica.
- Documentar contratos y decisiones no evidentes.
- Acompañar funcionalidades con pruebas automatizadas.
- Mantener `document_id` como identificador canónico entre Backend, OCI, RAG, Agentes, formatos y evaluaciones.
- No permitir que Backend acceda directamente al Vector Store de Agentes.
- No permitir que Agentes acceda directamente a OCI ni a la BD de negocio.
- Mantener configuraciones de RAG y Agentes desacopladas aunque compartan despliegue.
- No versionar credenciales ni configuración sensible.