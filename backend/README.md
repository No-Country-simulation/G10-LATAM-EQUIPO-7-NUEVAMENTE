# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI** y **Pydantic v2**.

BackendAPI concentra la recepción y gestión técnica de documentos, la persistencia de metadata y los contratos de integración con los módulos de RAG y Agentes.

El frontend del proyecto se encuentra en [`../frontend`](../frontend).

> Todos los comandos de este documento se ejecutan desde `backend/`.

---

## Estado actual

La arquitectura base del backend está organizada por responsabilidades.

Actualmente están implementados:

- API FastAPI y configuración central.
- Endpoint de salud.
- Endpoint legacy de carga local de archivos.
- Almacenamiento temporal local.
- Identificación de documentos mediante SHA-256.
- Dominio y estados de documentos y procesos.
- Persistencia de documentos mediante SQLite.
- Casos de uso para documentos, adaptaciones y procesos.
- Puertos para persistencia, Object Storage, RAG y Agentes.
- Schemas Pydantic.
- Pruebas unitarias y de integración.

Se encuentran preparados, pero aún no implementados completamente:

- `POST /api/v1/documents`.
- Endpoints de adaptaciones y procesos.
- OCI Object Storage.
- Integración real con RAG.
- Integración real con Agentes.

El endpoint `/api/v1/files/upload` se mantiene temporalmente por compatibilidad.

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

BackendAPI utiliza separación entre API, aplicación, dominio, contratos e infraestructura.

```text
API
 ↓
Application
 ↓
Ports
 ↑
Infrastructure implementa los Ports
```

Esto permite cambiar tecnologías de persistencia, almacenamiento o integraciones sin acoplar los casos de uso a implementaciones concretas.

### Responsabilidad de cada capa

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

La arquitectura inicial concentraba la mayor parte del flujo de carga en:

```text
API
 ↓
services/storage.py
 ↓
filesystem
```

Además, los endpoints dependían directamente del servicio de almacenamiento y el backend no contaba con capas explícitas para dominio, casos de uso, contratos o infraestructura.

La refactorización introduce los siguientes cambios:

| Antes | Ahora |
|---|---|
| `services/` concentraba lógica de almacenamiento | La lógica se separa entre `application/`, `ports/` e `infrastructure/` |
| Los endpoints dependían directamente del almacenamiento | Los endpoints delegarán los casos de uso a `application/` |
| No existía una capa de dominio | `domain/` contiene entidades, estados y reglas |
| No existían contratos internos | `ports/` define interfaces para BD, almacenamiento, RAG y Agentes |
| El almacenamiento local estaba acoplado al servicio | `LocalFileStorage` queda encapsulado en `infrastructure/storage/` |
| No existía repositorio de documentos | `DocumentRepository` y `SQLiteDocumentRepository` separan contrato e implementación |
| La identidad del documento dependía del flujo de carga | Se incorpora SHA-256 para identificar contenido y detectar duplicados |
| Las pruebas estaban concentradas en la raíz | Se organizan en `unit/` e `integration/` |
| `schemas/health.py` y otros contratos estaban dispersos | Los schemas se reorganizan por recurso y contratos comunes |

La carpeta `services/` permanece únicamente como compatibilidad temporal del endpoint legacy y será retirada cuando `POST /api/v1/documents` sustituya completamente `/api/v1/files/upload`.

---

## Estructura actual

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── health.py
│   │           ├── documents.py
│   │           ├── adaptations.py
│   │           ├── processes.py
│   │           └── files.py              # legacy temporal
│   │
│   ├── schemas/
│   │   ├── common.py
│   │   ├── document.py
│   │   ├── adaptation.py
│   │   ├── process.py
│   │   └── file.py                       # legacy temporal
│   │
│   ├── domain/
│   │   ├── document.py
│   │   ├── process.py
│   │   └── enums.py
│   │
│   ├── application/
│   │   ├── document_service.py
│   │   ├── adaptation_service.py
│   │   └── process_service.py
│   │
│   ├── ports/
│   │   ├── document_repository.py
│   │   ├── object_storage.py
│   │   ├── rag.py
│   │   └── agents.py
│   │
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
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── hashing.py
│   │
│   ├── services/
│   │   └── storage.py                    # compatibilidad legacy
│   │
│   ├── rag/
│   └── agents/
│
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── unit/
│   └── integration/
│
├── storage/                               # local, ignorado por Git
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Gestión de documentos

La identidad de un documento se determina mediante el hash **SHA-256 de su contenido**, no mediante su nombre.

El dominio contempla el siguiente ciclo de vida:

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

Los estados asociados a indexación corresponden a la integración con RAG.

### Persistencia

Actualmente existe una implementación de `DocumentRepository` sobre SQLite:

```text
Application
     ↓
DocumentRepository
     ↑
SQLiteDocumentRepository
     ↓
SQLite
```

La base local se configura por defecto en:

```text
storage/nuevamente.db
```

El directorio `/storage/` está excluido del control de versiones.

---

## Almacenamiento

### Local

`LocalFileStorage` permite guardar temporalmente archivos por bloques y controlar el tamaño máximo configurado.

El flujo legacy utiliza:

```text
POST /files/upload
        ↓
services/storage.py
        ↓
LocalFileStorage
        ↓
storage/uploads/
```

### OCI Object Storage

Existe el contrato `ObjectStoragePort` y el módulo:

```text
infrastructure/storage/oci_object_storage.py
```

La integración concreta con OCI todavía está pendiente.

La convención prevista para documentos originales es:

```text
documents/{document_id}/original.pdf
documents/{document_id}/original.md
documents/{document_id}/original.txt
```

---

## Integración con RAG y Agentes

BackendAPI define contratos desacoplados mediante:

```text
RagPort
AgentsPort
```

y mantiene adapters separados en:

```text
infrastructure/integrations/
```

Los contratos son provisionales mientras se completa la integración entre equipos.

BackendAPI no implementa directamente extracción de texto, chunking, embeddings, vector store, retrieval semántico, prompts, LangGraph ni generación/revisión mediante agentes.

Estas responsabilidades corresponden al módulo de **RAG y Agentes**.

---

## Endpoints

### Disponibles actualmente

| Método | Ruta | Estado |
|---|---|---|
| `GET` | `/` | Implementado |
| `GET` | `/api/v1/health` | Implementado |
| `POST` | `/api/v1/files/upload` | Implementado — legacy |

Los routers para documentos, adaptaciones y procesos ya existen, pero todavía no exponen operaciones funcionales.

### Próximos contratos

```text
POST /api/v1/documents
GET  /api/v1/documents/{document_id}

POST /api/v1/adaptations

GET  /api/v1/processes/{process_id}
```

Estos contratos pueden evolucionar mientras se completa la integración con Frontend, OCI, RAG y Agentes.

---

## Configuración

Crear `.env` a partir de `.env.example`.

Variables principales:

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

Ejecutar:

```bash
python -m pytest
python -m ruff check app tests
```

La suite está organizada en:

```text
tests/
├── unit/
├── integration/
└── test_health.py
```

Actualmente existen pruebas para dominio, schemas, hashing, casos de uso, SQLite, almacenamiento local, salud y el endpoint legacy de archivos.

---

## Lineamientos de desarrollo

- Mantener módulos y funciones con una responsabilidad clara.
- Separar HTTP, lógica de aplicación, dominio, persistencia e integraciones.
- Evitar que `application/` dependa directamente de implementaciones concretas de `infrastructure/`.
- Usar `ports/` como contratos entre aplicación e infraestructura.
- Mantener las integraciones externas encapsuladas.
- Manejar errores explícitamente.
- Evitar duplicación y abstracciones innecesarias.
- Documentar contratos y decisiones técnicas relevantes.
- Acompañar nuevas funcionalidades con pruebas.

El objetivo es poder evolucionar de:

```text
SQLite        → PostgreSQL / Supabase
Local Storage → OCI Object Storage
Ports         → integraciones reales de RAG y Agentes
```

sin modificar innecesariamente la lógica de aplicación ni los contratos HTTP.
