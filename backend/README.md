# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI** y **Pydantic v2**.

BackendAPI gestiona la recepción técnica de documentos, su identificación, persistencia de metadata y los contratos de integración con almacenamiento, RAG y Agentes.

El frontend se encuentra en [`../frontend`](../frontend).

> Los comandos de este documento se ejecutan desde `backend/`.

---

## Estado actual

Actualmente están implementados:

- API FastAPI y configuración central.
- Endpoint de salud.
- `POST /api/v1/documents` para cargar documentos mediante `multipart/form-data`.
- Admisión de archivos PDF, Markdown (`.md`) y TXT.
- Rechazo de extensiones no soportadas.
- Almacenamiento temporal local por bloques con límite de tamaño.
- Identificación de documentos mediante SHA-256 en la capa de aplicación.
- Dominio y estados de documentos y procesos.
- Persistencia de documentos mediante SQLite.
- Puertos para persistencia, Object Storage, RAG y Agentes.
- Pruebas unitarias y de integración.
- Endpoint legacy `/api/v1/files/upload`, mantenido temporalmente por compatibilidad.

Pendiente de implementación funcional:

- Integrar `POST /api/v1/documents` con identificación y persistencia del documento.
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
| `api/` | Endpoints HTTP y FastAPI |
| `schemas/` | Contratos externos de entrada y salida |
| `domain/` | Entidades, estados y reglas del dominio |
| `application/` | Casos de uso y orquestación |
| `ports/` | Interfaces hacia persistencia e integraciones |
| `infrastructure/` | Implementaciones concretas |
| `core/` | Configuración, logging, errores y utilidades |
| `rag/` | Espacio reservado para el equipo RAG |
| `agents/` | Espacio reservado para RAG/Agentes |

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
| Identidad ligada al flujo de carga | SHA-256 para identificar contenido y detectar duplicados |
| Tests concentrados en raíz | Organización en `unit/` e `integration/` |
| Solo `/files/upload` | Nuevo `POST /api/v1/documents` para documentos |

`services/`, `files.py` y `schemas/file.py` permanecen únicamente como compatibilidad temporal y serán retirados cuando el flujo de `/documents` sustituya completamente al endpoint legacy.

---

## Estructura actual

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
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

## Carga de documentos

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

Los archivos con extensiones no soportadas son rechazados con `415 Unsupported Media Type`.

Flujo actual:

```text
UploadFile
   ↓
validación de extensión
   ↓
LocalFileStorage
   ↓
storage/uploads/
   ↓
respuesta HTTP 201
```

La respuesta expone:

```json
{
  "filename": "uuid_nombre_saneado.txt",
  "original_filename": "nombre_original.txt",
  "content_type": "text/plain",
  "size_bytes": 123
}
```

La ruta física del archivo temporal no se expone en el contrato HTTP.

El siguiente paso del flujo será conectar este endpoint con la identificación SHA-256 y la persistencia de metadata.

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

---

## Almacenamiento

### Temporal local

`LocalFileStorage` escribe los archivos por bloques, sanea el nombre y controla el tamaño máximo configurado.

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
| `POST` | `/api/v1/documents` | Implementado |
| `POST` | `/api/v1/files/upload` | Implementado — legacy |

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

La suite incluye pruebas de dominio, schemas, hashing, servicios de aplicación, SQLite, almacenamiento local, salud, carga de documentos y compatibilidad legacy.

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
