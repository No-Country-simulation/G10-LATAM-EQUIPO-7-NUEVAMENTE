# NuevaMente — BackendAPI

Backend de **NuevaMente** construido con **FastAPI** y **Pydantic v2**.

Este directorio contiene la API y la lógica de aplicación responsable de recibir documentos, validar solicitudes, gestionar metadata, persistir archivos originales en OCI Object Storage y coordinar la integración con los módulos de RAG y agentes.

El cliente web se encuentra en [`../frontend`](../frontend).

> Todos los comandos de este README se ejecutan desde `backend/`.

---

## Alcance de BackendAPI

BackendAPI administra el flujo comprendido entre la recepción del documento y su entrega a los componentes de RAG y agentes.

```text
Frontend
   ↓
FastAPI
   ↓
Recepción del documento
   ↓
Validación técnica
   ↓
Identificación mediante SHA-256
   ↓
Persistencia de metadata
   ↓
OCI Object Storage
   ↓
Recuperación del documento
   ↓
Contrato de integración
   ↓
RAG / Agentes
```

BackendAPI no implementa directamente:

- extracción de contenido para RAG;
- limpieza y normalización semántica;
- chunking;
- embeddings;
- vector store;
- retrieval semántico;
- prompts pedagógicos;
- LangGraph;
- agentes de generación o revisión.

Estas responsabilidades pertenecen al módulo de **RAG y Agentes**.

---

## Stack

| Capa | Tecnología | Rol |
|---|---|---|
| API | `fastapi` | Framework ASGI y generación de OpenAPI |
| Servidor | `uvicorn[standard]` | Servidor ASGI |
| Uploads | `python-multipart` | Recepción de archivos `multipart/form-data` |
| Validación | `pydantic` v2 | Schemas, validación y serialización |
| Configuración | `pydantic-settings` | Gestión tipada de variables de entorno |
| Variables locales | `python-dotenv` | Carga de configuración desde `.env` |
| Tests | `pytest` | Pruebas automatizadas |
| Calidad | `ruff` | Linting y revisión estática |

### Integraciones previstas

| Componente | Estrategia |
|---|---|
| Persistencia inicial | SQLite |
| Persistencia compartida futura | PostgreSQL / Supabase |
| Archivos originales | OCI Object Storage |
| Identidad del documento | SHA-256 |
| Integración RAG | Puerto / interfaz desacoplada |
| Integración Agentes | Puerto / interfaz desacoplada |

La selección de SQLite, PostgreSQL o Supabase no debe modificar los endpoints ni la lógica de aplicación.

---

## Arquitectura objetivo

```text
backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py
│   │           ├── documents.py
│   │           ├── adaptations.py
│   │           └── processes.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── document.py
│   │   ├── adaptation.py
│   │   └── process.py
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── process.py
│   │   └── enums.py
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── document_service.py
│   │   ├── adaptation_service.py
│   │   └── process_service.py
│   │
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── document_repository.py
│   │   ├── object_storage.py
│   │   ├── rag.py
│   │   └── agents.py
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── persistence/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── sqlite_document_repository.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── local_storage.py
│   │   │   └── oci_object_storage.py
│   │   └── integrations/
│   │       ├── __init__.py
│   │       ├── rag_adapter.py
│   │       └── agents_adapter.py
│   │
│   └── core/
│       ├── __init__.py
│       ├── config.py
│       ├── exceptions.py
│       ├── logging.py
│       └── hashing.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_document_service.py
│   │   ├── test_hashing.py
│   │   ├── test_document_repository.py
│   │   └── test_object_storage.py
│   ├── integration/
│   │   ├── test_documents_api.py
│   │   └── test_oci_storage.py
│   └── test_health.py
│
├── storage/
│   ├── uploads/
│   └── nuevamente.db
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Responsabilidad por capa

| Capa | Responsabilidad |
|---|---|
| `api/` | Endpoints HTTP, códigos de respuesta y coordinación con FastAPI |
| `schemas/` | Contratos externos de entrada y salida |
| `domain/` | Entidades, estados y reglas del dominio |
| `application/` | Casos de uso y coordinación del flujo |
| `ports/` | Contratos hacia BD, OCI, RAG y Agentes |
| `infrastructure/` | Implementaciones concretas de persistencia e integraciones |
| `core/` | Configuración, excepciones, logging y utilidades transversales |
| `tests/` | Pruebas unitarias y de integración |

La dependencia principal de la arquitectura es:

```text
API
 ↓
Application
 ↓
Ports
 ↓
Infrastructure
```

La capa de aplicación no debe depender directamente de SQLite, Supabase, OCI ni de una implementación concreta de RAG.

---

## Flujo de documentos

### 1. Recepción

Los documentos serán recibidos inicialmente mediante:

```http
POST /api/v1/documents
Content-Type: multipart/form-data
```

Formatos previstos:

- PDF;
- Markdown (`.md`);
- texto plano (`.txt`).

### 2. Validación e identificación

BackendAPI validará:

- extensión;
- MIME type;
- tamaño;
- contenido no vacío;
- nombre de archivo seguro.

Cada documento será identificado mediante:

```text
SHA-256(contenido)
```

La firma permitirá detectar contenido duplicado independientemente del nombre del archivo.

### 3. Metadata

Cada documento almacenará como mínimo:

```text
document_id
original_filename
sha256
content_type
size_bytes
status
oci_object_name
created_at
updated_at
```

El modelo interno puede contener más información que la respuesta pública expuesta por la API.

---

## Estados del documento

Flujo principal:

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

### Responsabilidad por módulo

```text
BackendAPI
RECEIVED
→ VALIDATED
→ STORING
→ STORED

RAG
STORED
→ INDEXING
→ INDEXED
```

---

## Persistencia

Durante el desarrollo puede utilizarse SQLite:

```text
FastAPI
   ↓
DocumentRepository
   ↓
SQLite
```

La arquitectura debe permitir una migración posterior a PostgreSQL o Supabase:

```text
FastAPI
   ↓
DocumentRepository
   ↓
PostgreSQL / Supabase
```

sin modificar los endpoints ni los casos de uso.

Los archivos de base de datos local deben permanecer fuera del control de versiones:

```gitignore
storage/*.db
storage/*.db-shm
storage/*.db-wal
```

---

## OCI Object Storage

Los documentos originales se almacenarán permanentemente en OCI Object Storage.

El almacenamiento local se utilizará únicamente como soporte temporal durante la recepción y validación.

```text
UploadFile
   ↓
archivo temporal
   ↓
validación
   ↓
SHA-256
   ↓
metadata
   ↓
OCI Object Storage
   ↓
eliminación del temporal cuando corresponda
```

Convención inicial de objetos:

```text
documents/{document_id}/original.pdf
documents/{document_id}/original.md
documents/{document_id}/original.txt
```

La configuración de OCI debe provenir de variables de entorno. Las credenciales no deben almacenarse en Git.

---

## Recuperación de documentos desde OCI

BackendAPI permitirá recuperar físicamente un documento previamente almacenado.

```text
document_id
    ↓
DocumentRepository
    ↓
oci_object_name
    ↓
OCI Object Storage
    ↓
archivo original
```

En este proyecto se distingue entre:

- **Recuperación desde OCI**: obtención física del archivo original.
- **Retrieval RAG**: búsqueda semántica de chunks dentro del vector store.

---

## Contrato provisional con RAG

Mientras se define el contrato definitivo entre módulos se utilizará una interfaz mínima y desacoplada.

```python
class RagDocumentInput:
    document_id: str
    filename: str
    content_type: str
    content: bytes
```

Este contrato podrá evolucionar sin modificar la capa HTTP, la persistencia o la integración con OCI.

BackendAPI es responsable de entregar un documento válido y recuperable.

RAG es responsable de:

```text
extracción de contenido
→ limpieza
→ chunking
→ embeddings
→ vector store
→ indexación
```

---

## Contrato provisional con Frontend

### Carga de documento

```http
POST /api/v1/documents
```

Respuesta inicial:

```json
{
  "document_id": "doc_a83f1234",
  "filename": "manual_oci.pdf",
  "status": "stored"
}
```

Detalles internos como SHA-256, rutas locales o credenciales de OCI no forman parte del contrato público salvo que exista una necesidad explícita.

---

## Endpoints

### Implementados actualmente

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Información del servicio |
| `GET` | `/api/v1/health` | Estado del servicio |
| `POST` | `/api/v1/files/upload` | Endpoint inicial de carga |

### Arquitectura objetivo

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/documents` | Registrar y almacenar un documento |
| `GET` | `/api/v1/documents/{document_id}` | Consultar metadata y estado |
| `POST` | `/api/v1/adaptations` | Solicitar una adaptación educativa |
| `GET` | `/api/v1/processes/{process_id}` | Consultar el estado de un proceso |

`/api/v1/files/upload` podrá mantenerse temporalmente durante la refactorización hasta ser sustituido por `/api/v1/documents`.

---

## Puesta en marcha

```bash
cd backend

python3 -m venv .venv

# Linux / macOS
source .venv/bin/activate

pip install -r requirements-dev.txt

cp .env.example .env

uvicorn app.main:app --reload
```

En Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Servicios locales:

```text
API:     http://localhost:8000
Swagger: http://localhost:8000/docs
```

Swagger y OpenAPI se deshabilitan automáticamente cuando `ENVIRONMENT=production`.

---

## Configuración

La configuración se administra mediante `.env`.

Ejemplo:

```env
PROJECT_NAME=NuevaMente API
ENVIRONMENT=local

BACKEND_CORS_ORIGINS=http://localhost:3000

MAX_UPLOAD_SIZE_MB=10
UPLOAD_DIR=storage/uploads

DATABASE_URL=sqlite:///storage/nuevamente.db

OCI_NAMESPACE=
OCI_BUCKET_NAME=
OCI_REGION=
```

Las credenciales reales no deben incluirse en el repositorio.

---

## Tests y calidad

```bash
pytest
ruff check .
ruff check --fix .
```

Organización prevista:

```text
tests/
├── unit/
└── integration/
```

Las pruebas unitarias no deben depender de servicios externos reales.

OCI, RAG y Agentes deben poder reemplazarse mediante mocks o adapters de prueba.

---

## Convenciones de desarrollo

### Separación de responsabilidades

No se debe mezclar en un mismo módulo:

- lógica HTTP;
- lógica de aplicación;
- acceso a datos;
- OCI;
- RAG;
- agentes.

### Contratos

Los schemas Pydantic representan los contratos externos de la API.

Los contratos internos con infraestructura y otros módulos se definen mediante `ports`.

### Manejo de errores

Las respuestas de error utilizan `ErrorResponse` con:

```text
detail
errors[]
timestamp
```

Esto aplica, entre otros, a:

```text
404
413
422
500
```

### Integraciones externas

Toda integración externa debe estar encapsulada.

Ejemplos:

```text
DocumentRepository
ObjectStoragePort
RagPort
AgentsPort
```

---

## Roadmap de BackendAPI

### Sprint 1

```text
Refactorizar estructura base
Implementar POST /documents
Validar documentos
Calcular SHA-256
Definir Document
Persistencia local
Swagger y tests
```

### Sprint 2

```text
Integrar OCI Object Storage
Detectar duplicados
Actualizar estados
Recuperar documentos desde OCI
Integración inicial con RAG mediante adapter
```

### Sprint 3

```text
Implementar POST /adaptations
Integrar RAG y Agentes
Persistir resultados
Administrar estados de proceso
Integrar con frontend
```

### Sprint 4

```text
Pruebas end-to-end
Observabilidad
Docker
Despliegue
Hardening
Documentación final
```

---

## Nota sobre versiones

El proyecto utiliza Python 3.14.

Para esta versión se requiere:

```text
pydantic >= 2.12
```

debido a compatibilidad y disponibilidad de wheels.

---

## Principio arquitectónico

BackendAPI debe evolucionar sin quedar acoplado a una tecnología específica:

```text
SQLite        → PostgreSQL / Supabase
Local Storage → OCI Object Storage
Mock RAG      → RAG real
Mock Agents   → LangGraph
```

Los cambios de infraestructura no deben obligar a modificar los contratos HTTP ni la lógica principal de aplicación.
