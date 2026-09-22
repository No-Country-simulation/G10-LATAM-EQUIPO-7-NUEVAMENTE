# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI** y **Pydantic v2**.

BackendAPI gestiona la recepción técnica de documentos, su validación, identificación, persistencia de metadata y los contratos de integración con almacenamiento, RAG y Agentes.

El frontend se encuentra en [`../frontend`](../frontend).

> Los comandos de este documento se ejecutan desde `backend/`.

---

## Estado actual

Actualmente están implementados:

- API FastAPI y configuración central.
- Endpoint de salud.
- `POST /api/v1/documents` para cargar documentos mediante `multipart/form-data`.
- Admisión de archivos PDF, Markdown (`.md`) y TXT.
- Validación de extensión y MIME type declarado.
- Rechazo de archivos vacíos.
- Control de tamaño máximo de carga.
- Saneamiento del nombre utilizado para almacenamiento temporal.
- Identificación de documentos mediante SHA-256.
- Detección de contenido duplicado mediante SHA-256.
- Generación de `document_id` para documentos nuevos.
- Recuperación del mismo `document_id` cuando el contenido ya había sido registrado.
- Persistencia SQLite utilizada por el flujo de identificación.
- Dominio y estados de documentos y procesos.
- Puertos para persistencia, Object Storage, RAG y Agentes.
- Pruebas unitarias y de integración.
- Endpoint legacy `/api/v1/files/upload`, mantenido temporalmente por compatibilidad.

Pendiente de implementación funcional:

- Completar el flujo de persistencia de metadata y estados del documento.
- OCI Object Storage.
- Recuperación de documentos desde OCI.
- Integración real con RAG.
- Integración real con Agentes.
- Endpoints funcionales de adaptaciones y procesos.

---

## Stack

| Componente | Tecnología |
|---|---|
| API | FastAPI |
| Servidor | Uvicorn |
| Validación | Pydantic v2 |
| Configuración | Pydantic Settings |
| Uploads | python-multipart |
| Persistencia local | SQLite |
| Testing | pytest / httpx |
| Calidad | Ruff |
| Almacenamiento permanente previsto | OCI Object Storage |

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
| `api/` | Endpoints HTTP, dependencias de FastAPI y composición en el borde HTTP |
| `schemas/` | Contratos externos de entrada y salida |
| `domain/` | Entidades, estados y reglas del dominio |
| `application/` | Casos de uso y orquestación |
| `ports/` | Interfaces hacia persistencia e integraciones |
| `infrastructure/` | Implementaciones concretas |
| `core/` | Configuración, logging, errores y utilidades |
| `rag/` | Espacio reservado para el equipo RAG |
| `agents/` | Espacio reservado para RAG/Agentes |

El endpoint HTTP no conoce directamente la implementación SQLite. `DocumentService` depende de `DocumentRepository`, mientras que `main.py` compone la implementación concreta utilizada por la aplicación.

```text
documents.py
     ↓
DocumentService
     ↓
DocumentRepository
     ↑
SQLiteDocumentRepository
```

---

## Cambios respecto a la arquitectura anterior

La arquitectura inicial concentraba la carga en:

```text
API
 ↓
services/storage.py
 ↓
filesystem
```

La refactorización introduce:

| Antes | Ahora |
|---|---|
| `services/` concentraba almacenamiento | Responsabilidades separadas entre `application/`, `ports/` e `infrastructure/` |
| Endpoints acoplados al almacenamiento | Los casos de uso se delegan progresivamente a `application/` |
| Sin capa de dominio | `domain/` contiene entidades y estados |
| Sin contratos internos | `ports/` define interfaces para BD, almacenamiento, RAG y Agentes |
| Sin repositorio de documentos | `DocumentRepository` + `SQLiteDocumentRepository` |
| Identidad ligada al flujo de carga | SHA-256 identifica el contenido y permite detectar duplicados |
| Sin composición explícita de dependencias | `main.py` inicializa SQLite y `DocumentService` |
| Dependencias construidas dentro del flujo | `api/dependencies.py` expone servicios ya configurados |
| Tests concentrados en raíz | Organización en `unit/` e `integration/` |
| Solo `/files/upload` | `POST /api/v1/documents` valida, identifica y registra documentos |

`services/`, `files.py` y `schemas/file.py` permanecen únicamente como compatibilidad temporal y serán retirados cuando el flujo de `/documents` sustituya completamente al endpoint legacy.

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
│   │           ├── processes.py
│   │           └── files.py              # legacy
│   ├── schemas/
│   │   ├── common.py
│   │   ├── document.py
│   │   ├── adaptation.py
│   │   ├── process.py
│   │   └── file.py                       # legacy
│   ├── domain/
│   │   ├── document.py
│   │   ├── process.py
│   │   └── enums.py
│   ├── application/
│   │   ├── document_service.py
│   │   ├── adaptation_service.py
│   │   └── process_service.py
│   ├── ports/
│   │   ├── document_repository.py
│   │   ├── object_storage.py
│   │   ├── rag.py
│   │   └── agents.py
│   ├── infrastructure/
│   │   ├── persistence/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── sqlite_document_repository.py
│   │   ├── storage/
│   │   │   ├── local_storage.py
│   │   │   └── oci_object_storage.py
│   │   └── integrations/
│   │       ├── rag_adapter.py
│   │       └── agents_adapter.py
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── hashing.py
│   ├── services/
│   │   └── storage.py                    # compatibilidad legacy
│   ├── rag/
│   └── agents/
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── unit/
│   └── integration/
├── storage/                               # local, ignorado por Git
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Carga, validación e identificación de documentos

El endpoint:

```text
POST /api/v1/documents
```

recibe un archivo mediante `multipart/form-data`.

Formatos admitidos:

```text
.pdf
.md
.txt
```

### Validaciones actuales

El flujo valida:

- extensión permitida;
- MIME type declarado compatible con el formato;
- tamaño máximo configurado;
- archivo no vacío;
- nombre de archivo apto para almacenamiento temporal.

Los archivos con extensión o MIME no soportado son rechazados con `415 Unsupported Media Type`.

Los archivos vacíos son rechazados con `400 Bad Request`.

Los archivos que superan el tamaño máximo configurado son rechazados con `413 Content Too Large`.

### Flujo actual

```text
UploadFile
   ↓
validación de extensión y MIME
   ↓
LocalFileStorage
   ├─ saneamiento de nombre temporal
   └─ control de tamaño
   ↓
validación de archivo no vacío
   ↓
SHA-256 del contenido
   ↓
DocumentRepository.find_by_sha256()
   │
   ├─ existe → recuperar document_id → duplicate = true → HTTP 200
   │
   └─ no existe → generar document_id → registrar → VALIDATED → HTTP 201
```

### Documento nuevo

```json
{
  "document_id": "doc_69f7bfab0d9d410690662cc6a376d509",
  "filename": "manual.txt",
  "status": "validated",
  "duplicate": false
}
```

Código HTTP:

```text
201 Created
```

### Documento duplicado

```json
{
  "document_id": "doc_69f7bfab0d9d410690662cc6a376d509",
  "filename": "manual.txt",
  "status": "validated",
  "duplicate": true
}
```

Código HTTP:

```text
200 OK
```

El documento duplicado conserva el mismo `document_id`.

La ruta física del archivo temporal no se expone en el contrato HTTP. Cuando una carga corresponde a contenido ya registrado, la nueva copia temporal se elimina.

---

## Gestión de documentos

La identidad de un documento se determina mediante **SHA-256 de su contenido**, no por su nombre.

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

Estados de error:

```text
VALIDATION_FAILED
STORAGE_FAILED
INDEXING_FAILED
```

BackendAPI administra principalmente:

```text
RECEIVED → VALIDATED → STORING → STORED
```

La tarjeta actual de validación e identificación deja el documento en:

```text
VALIDATED
```

### Persistencia

```text
Application
     ↓
DocumentRepository
     ↑
SQLiteDocumentRepository
     ↓
SQLite
```

La base local se configura en:

```text
storage/nuevamente.db
```

SQLite permite actualmente conservar la relación entre SHA-256 y `document_id`, necesaria para reconocer contenido duplicado entre solicitudes.

La ampliación del manejo de metadata y estados forma parte del siguiente paso del backend.

---

## Almacenamiento

### Temporal local

`LocalFileStorage` escribe los archivos por bloques, sanea el nombre utilizado para almacenamiento temporal y controla el tamaño máximo configurado.

### OCI Object Storage

Existe `ObjectStoragePort` y el módulo:

```text
infrastructure/storage/oci_object_storage.py
```

La implementación concreta con OCI está pendiente.

Convención prevista:

```text
documents/{document_id}/original.pdf
documents/{document_id}/original.md
documents/{document_id}/original.txt
```

---

## RAG y Agentes

BackendAPI define contratos desacoplados mediante:

```text
RagPort
AgentsPort
```

Los adapters se ubican en:

```text
infrastructure/integrations/
```

BackendAPI no implementa directamente extracción de texto, chunking, embeddings, vector store, retrieval semántico, prompts ni orquestación de agentes.

---

## Endpoints

| Método | Ruta | Estado |
|---|---|---|
| `GET` | `/` | Implementado |
| `GET` | `/api/v1/health` | Implementado |
| `POST` | `/api/v1/documents` | Implementado: carga, valida, identifica y detecta duplicados |
| `POST` | `/api/v1/files/upload` | Implementado — legacy |

### Respuestas de `POST /api/v1/documents`

| Código | Significado |
|---|---|
| `200` | Documento previamente registrado |
| `201` | Documento nuevo registrado |
| `400` | Documento vacío o inválido |
| `413` | Documento demasiado grande |
| `415` | Formato o MIME type no soportado |
| `422` | Error de validación de la petición |

Los routers de adaptaciones y procesos existen, pero todavía no exponen operaciones funcionales.

Próximos contratos:

```text
GET  /api/v1/documents/{document_id}
POST /api/v1/adaptations
GET  /api/v1/processes/{process_id}
```

---

## Configuración

Crear `.env` a partir de `.env.example`.

```env
PROJECT_NAME="NuevaMente API"
ENVIRONMENT=local
DEBUG=true

API_V1_PREFIX=/api/v1

HOST=0.0.0.0
PORT=8000

BACKEND_CORS_ORIGINS=http://localhost:3000

MAX_UPLOAD_SIZE_MB=10
UPLOAD_DIR=storage/uploads

DATABASE_URL=sqlite:///storage/nuevamente.db

OCI_NAMESPACE=
OCI_BUCKET_NAME=
OCI_REGION=
```

Las credenciales reales y archivos locales no deben almacenarse en Git.

---

## Instalación

### Windows PowerShell

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt

Copy-Item .env.example .env

uvicorn app.main:app --reload
```

### Linux / macOS

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements-dev.txt

cp .env.example .env

uvicorn app.main:app --reload
```

Servicios locales:

```text
API:     http://localhost:8000
Swagger: http://localhost:8000/docs
```

Swagger y OpenAPI se deshabilitan cuando `ENVIRONMENT=production`.

---

## Tests y calidad

```bash
python -m pytest
python -m ruff check app tests
```

La suite incluye pruebas de:

- dominio;
- schemas;
- hashing;
- servicios de aplicación;
- repositorio SQLite;
- almacenamiento local;
- salud del servicio;
- carga de PDF, Markdown y TXT;
- extensión no soportada;
- MIME type incompatible;
- archivo vacío;
- límite de tamaño;
- identificación mediante `document_id`;
- detección de duplicados;
- compatibilidad del endpoint legacy.

Las pruebas de integración utilizan una base SQLite temporal para evitar modificar la base local de desarrollo.

---

## Lineamientos de desarrollo

- Mantener módulos y funciones con una responsabilidad clara.
- Separar HTTP, aplicación, dominio, persistencia e integraciones.
- Evitar dependencias directas de `application/` hacia implementaciones concretas de `infrastructure/`.
- Usar `ports/` como contratos entre capas.
- Encapsular integraciones externas.
- Manejar errores explícitamente.
- Evitar duplicación y abstracciones innecesarias.
- Documentar contratos y decisiones relevantes.
- Acompañar nuevas funcionalidades con pruebas.
