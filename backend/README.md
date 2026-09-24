# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI** y **Pydantic v2**.

BackendAPI gestiona la recepción técnica de documentos, su validación, identificación, persistencia de metadata y estado, almacenamiento y recuperación del archivo original en OCI Object Storage, y la frontera de integración con el módulo RAG.

La extracción de contenido, limpieza, chunking, embeddings, Vector Store, retrieval semántico y procesamiento mediante agentes pertenecen a los módulos RAG/Agentes y no forman parte de la implementación interna de BackendAPI.

El frontend se encuentra en [`../frontend`](../frontend).

> Los comandos de este documento se ejecutan desde `backend/`.

---

## Estado actual

Actualmente están implementados:

- API FastAPI y configuración central.
- Endpoint de salud.
- `POST /api/v1/documents` para cargar documentos mediante `multipart/form-data`.
- `GET /api/v1/documents/{document_id}` para consultar metadata y estado.
- Admisión de archivos PDF, Markdown (`.md`) y TXT.
- Validación de extensión y MIME type declarado.
- Rechazo de archivos vacíos.
- Control de tamaño máximo de carga.
- Almacenamiento temporal desacoplado mediante `TemporaryStoragePort`.
- Implementación local del almacenamiento temporal mediante `LocalFileStorage`.
- Lectura del upload por bloques para evitar cargar el documento completo en memoria durante el staging local.
- Eliminación del archivo temporal después del almacenamiento permanente o cuando ocurre un fallo.
- Identificación de documentos mediante SHA-256.
- Detección de contenido duplicado mediante SHA-256.
- Generación de `document_id` para documentos nuevos.
- Recuperación del mismo `document_id` cuando el contenido ya había sido registrado.
- Persistencia de metadata y estado mediante una capa de repositorio desacoplada.
- Implementación actual del repositorio mediante SQLite.
- Selección centralizada del repositorio mediante `repository_factory.py`.
- Contrato desacoplado de almacenamiento persistente mediante `ObjectStoragePort`.
- Implementación de OCI Object Storage mediante `OCIObjectStorage`.
- Persistencia del archivo original en OCI utilizando la convención `documents/{document_id}/original.ext`.
- Persistencia de `oci_object_name` en la metadata del documento.
- Recuperación interna del archivo original desde OCI mediante `document_id`.
- Resolución del flujo `document_id → metadata → oci_object_name → contenido binario`.
- Representación del documento recuperado mediante `RetrievedDocument`.
- Manejo explícito de documentos inexistentes, documentos sin objeto persistente y fallos durante la recuperación desde Object Storage.
- Gestión de estados `VALIDATED → STORING → STORED`.
- Gestión del estado `STORAGE_FAILED` cuando falla el almacenamiento en Object Storage.
- Estrategia de compensación cuando la carga a OCI finaliza correctamente pero falla la persistencia final de `oci_object_name` / `STORED`.
- Eliminación compensatoria del objeto OCI para evitar objetos huérfanos cuando la actualización final en BD falla.
- Error explícito `DocumentStorageConsistencyError` cuando no puede garantizarse la consistencia entre Object Storage y persistencia.
- Contrato BackendAPI–RAG v1 mediante `RagDocumentInput` y `RagPort`.
- Entrega de `document_id`, `filename`, `content_type` y `content: bytes` al límite de integración con RAG.
- Orquestación de recuperación desde OCI y entrega a RAG mediante `RagIntegrationService`.
- Adaptador `RagAdapter` desacoplado del código interno del módulo RAG.
- Preservación del `document_id` canónico generado por BackendAPI durante la entrega a RAG.
- Manejo explícito de fallos de integración mediante `RagError` y `RagIntegrationError`.
- Pruebas unitarias de la integración BackendAPI–RAG mediante dobles controlados.
- Dominio y estados de documentos y procesos.
- Eliminación completa del endpoint anterior `/api/v1/files/upload` y de su capa de compatibilidad asociada.

Pendiente de implementación funcional:

- Implementar el transporte HTTP definitivo para la integración BackendAPI–RAG, manteniendo el contrato `document_id`, `filename`, `content_type` y `content`.
- Adaptar `RagAdapter` al endpoint HTTP público que exponga el equipo RAG.
- Registrar la implementación concreta del adapter en el ciclo de vida de la aplicación cuando el endpoint de RAG esté disponible.
- Definir, junto con RAG, la semántica exacta de finalización de la indexación antes de activar transiciones automáticas `INDEXING → INDEXED`.
- Implementar funcionalmente el flujo de adaptación pedagógica en el sprint correspondiente.
- Implementación futura de otro motor de persistencia, por ejemplo PostgreSQL/Supabase, si el despliegue lo requiere.

Los componentes internos de RAG y Agentes son responsabilidad de sus respectivos módulos y equipos.

---

## Stack

| Componente | Tecnología |
|---|---|
| API | FastAPI |
| Servidor | Uvicorn |
| Validación | Pydantic v2 |
| Configuración | Pydantic Settings |
| Uploads | python-multipart |
| Staging temporal | Sistema de archivos local |
| Persistencia de metadata | SQLite |
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
Application / Ports
 ↑
Infrastructure implementa los Ports
```

| Capa | Responsabilidad |
|---|---|
| `api/` | Endpoints HTTP y composición de dependencias de FastAPI |
| `schemas/` | Contratos externos de entrada y salida |
| `domain/` | Entidades, estados y reglas del dominio |
| `application/` | Casos de uso y orquestación |
| `ports/` | Contratos hacia persistencia, almacenamiento e integraciones |
| `infrastructure/` | Implementaciones concretas |
| `core/` | Configuración, logging, errores y utilidades |

### Flujo de carga de documentos

El flujo principal de carga es:

```text
Frontend
   ↓
POST /api/v1/documents
   ↓
UploadFile
   ↓
TemporaryStoragePort
   ↑
LocalFileStorage
   ↓
archivo temporal
   ↓
DocumentService.register_document()
   ├── SHA-256
   ├── detección de duplicados
   ├── document_id
   └── metadata → SQLite
   ↓
DocumentService.store_document()
   ↓
ObjectStoragePort
   ↑
OCIObjectStorage
   ↓
OCI Object Storage
   ↓
actualización de metadata en SQLite
   ↓
eliminación del temporal
```

El archivo local es únicamente un staging temporal. No constituye almacenamiento persistente.

### Almacenamiento temporal

El endpoint HTTP no depende directamente de una implementación concreta de almacenamiento temporal.

```text
documents.py
     ↓
TemporaryStoragePort
     ↑
LocalFileStorage
     ↓
storage/uploads/
```

`TemporaryStoragePort` define el contrato requerido por la API y `LocalFileStorage` implementa actualmente ese contrato mediante el sistema de archivos local.

Esta separación permite cambiar la estrategia de staging sin modificar el contrato HTTP de documentos.

### Persistencia de metadata

El endpoint HTTP tampoco conoce directamente el motor de base de datos. `DocumentService` depende del contrato `DocumentRepository`.

```text
documents.py
     ↓
DocumentService
     ↓
DocumentRepository
     ↑
SQLiteDocumentRepository
     ↓
SQLite
```

La selección concreta del repositorio se centraliza en:

```text
infrastructure/persistence/repository_factory.py
```

La configuración por defecto es:

```text
DATABASE_URL=sqlite:///storage/nuevamente.db
```

La tabla `documents` persiste:

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

El contenido binario del documento **no se almacena en SQLite**.

Esto permite incorporar posteriormente otra implementación, por ejemplo PostgreSQL/Supabase, sin modificar endpoints ni casos de uso.

### Almacenamiento persistente de objetos

La lógica de aplicación no depende directamente del SDK de OCI.

```text
DocumentService
     ↓
ObjectStoragePort
     ↑
OCIObjectStorage
     ↓
OCI Object Storage
```

El contrato abstrae escritura, recuperación y eliminación de objetos:

```text
upload_file(...)
download_file(...)
delete_object(...)
```

Los documentos se almacenan utilizando la convención:

```text
documents/{document_id}/original.ext
```

De esta forma, la autenticación y las llamadas específicas a OCI quedan encapsuladas en `infrastructure/storage/`.

### Separación entre metadata y archivo

```text
SQLite
────────────────────────────────
document_id
filename
sha256
content_type
size_bytes
status
oci_object_name
timestamps
        │
        │ referencia
        ▼
OCI Object Storage
────────────────────────────────
documents/{document_id}/original.ext
        │
        └── contenido binario original
```

SQLite conserva la información necesaria para localizar y gestionar el documento. OCI conserva el archivo original.

### Recuperación de documentos

La recuperación física de un documento es responsabilidad de BackendAPI.

```text
document_id
     ↓
DocumentService
     ↓
DocumentRepository.find_by_id()
     ↓
Document
     ↓
oci_object_name
     ↓
ObjectStoragePort.download_file()
     ↑
OCIObjectStorage
     ↓
OCI Object Storage
     ↓
bytes
     ↓
RetrievedDocument
```

`RetrievedDocument` conserva:

```text
document_id
filename
content_type
content
```

El `document_id` es el identificador canónico generado por BackendAPI y debe conservarse cuando el documento sea entregado posteriormente al módulo RAG.

La recuperación es actualmente un caso de uso interno. No se expone un endpoint HTTP para descargar el archivo, ya que su propósito es preparar el documento para integraciones internas posteriores.

### Integración BackendAPI–RAG

La frontera lógica actual es:

```text
Application
    ↓
RagPort
    ↑
RagAdapter
    ↓
transporte HTTP hacia RAG (pendiente de implementación)
```

`RagIntegrationService` es responsable de:

```text
document_id
    ↓
DocumentService.retrieve_document()
    ↓
RetrievedDocument
    ↓
RagDocumentInput
    ↓
RagPort.index_document()
```

BackendAPI no accede a componentes internos de RAG como `RetrieverService`, `VectorStore`, chunkers, modelos de embeddings o pipelines internos.

El equipo RAG confirmó como válida la información del contrato v1; el transporte acordado será mediante solicitud HTTP y se implementará en el sprint correspondiente.

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
│   │   ├── adaptation.py
│   │   └── process.py
│   ├── domain/
│   │   ├── document.py
│   │   ├── process.py
│   │   └── enums.py
│   ├── application/
│   │   ├── document_service.py
│   │   ├── rag_integration_service.py
│   │   ├── adaptation_service.py
│   │   └── process_service.py
│   ├── ports/
│   │   ├── document_repository.py
│   │   ├── temporary_storage.py
│   │   ├── object_storage.py
│   │   ├── rag.py
│   │   └── agents.py
│   ├── infrastructure/
│   │   ├── persistence/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── repository_factory.py
│   │   │   └── sqlite_document_repository.py
│   │   ├── storage/
│   │   │   ├── local_storage.py
│   │   │   └── oci_object_storage.py
│   │   └── integrations/
│   │       ├── rag_adapter.py
│   │       └── agents_adapter.py
│   └── core/
│       ├── config.py
│       ├── exceptions.py
│       ├── logging.py
│       └── hashing.py
├── tests/
│   ├── conftest.py
│   ├── fakes.py
│   ├── test_health.py
│   ├── unit/
│   │   ├── test_document_service.py
│   │   ├── test_local_storage.py
│   │   ├── test_oci_object_storage.py
│   │   ├── test_rag_integration_service.py
│   │   └── test_rag_adapter.py
│   └── integration/
│       └── test_documents_api.py
├── storage/                               # local, ignorado por Git
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Endpoints actuales

### Salud

```text
GET /api/v1/health
```

Permite verificar que BackendAPI se encuentra disponible.

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

Para un documento nuevo devuelve `201 Created`:

```json
{
  "document_id": "doc_e7a935bc87ff",
  "filename": "manual.pdf",
  "status": "stored",
  "duplicate": false
}
```

Si el contenido ya estaba registrado, reutiliza el `document_id` y devuelve `200 OK`:

```json
{
  "document_id": "doc_e7a935bc87ff",
  "filename": "manual.pdf",
  "status": "stored",
  "duplicate": true
}
```

### Consultar documento

```text
GET /api/v1/documents/{document_id}
```

Devuelve la metadata registrada del documento:

```json
{
  "document_id": "doc_e7a935bc87ff",
  "filename": "manual.pdf",
  "status": "stored",
  "content_type": "application/pdf",
  "size_bytes": 12345,
  "created_at": "2026-09-24T20:00:00+00:00",
  "updated_at": "2026-09-24T20:00:01+00:00"
}
```

---

## Contrato BackendAPI–RAG v1

El contrato utilizado por BackendAPI para entregar un documento a RAG es:

```python
@dataclass(frozen=True, slots=True)
class RagDocumentInput:
    document_id: str
    filename: str
    content_type: str | None
    content: bytes
```

La decisión v1 es explícita: **BackendAPI recupera el archivo desde OCI y entrega a RAG el contenido binario completo junto con su identidad canónica**.

Por tanto, RAG no necesita recibir ni conocer:

```text
oci_object_name
bucket
namespace
credenciales OCI
OCI Python SDK
```

Tampoco se incluyen en este contrato `sha256` ni estados internos de Backend, ya que no forman parte de la información necesaria para iniciar el procesamiento RAG.

### `document_id` canónico

El `document_id` entregado a RAG es siempre el generado por BackendAPI.

RAG debe preservar este identificador durante su procesamiento. BackendAPI no utiliza el nombre del archivo ni `source` como identificador alternativo.

### Orquestación

`RagIntegrationService` implementa el caso de uso:

```text
document_id
    ↓
DocumentService.retrieve_document()
    ↓
RetrievedDocument
    ↓
RagDocumentInput
    ↓
RagPort.index_document()
```

El servicio no conoce la implementación interna del módulo RAG.

### Transporte

El contrato de datos está definido y validado desde BackendAPI. El equipo RAG confirmó la estructura propuesta y acordó que la integración entre módulos se realizará mediante una solicitud HTTP.

La implementación concreta del cliente HTTP y del endpoint público de RAG corresponde al siguiente sprint.

### Adaptador

`RagAdapter` implementa `RagPort` y mantiene desacoplada la capa de aplicación del mecanismo concreto de comunicación con RAG.

Cuando el endpoint HTTP definitivo esté disponible, únicamente la capa de integración deberá adaptarse al transporte concreto.

Si RAG cambia internamente su pipeline, Vector Store, Retriever o tecnología de embeddings, esos cambios no deben propagarse a `application/` ni al dominio de BackendAPI.

### Errores

Los fallos de integración se normalizan como:

```text
RagError
```

y la capa de aplicación los traduce a:

```text
RagIntegrationError
```

Esto evita que errores específicos del módulo RAG se propaguen directamente por la lógica de aplicación.

### Estados de indexación

BackendAPI ya define:

```text
INDEXING
INDEXED
INDEXING_FAILED
```

pero la integración v1 todavía no activa estas transiciones automáticamente.

La razón es contractual: hasta que el endpoint HTTP de RAG defina si su respuesta significa “solicitud aceptada” o “indexación finalizada”, BackendAPI no debe marcar un documento como `INDEXED` basándose en una suposición.

---

## Configuración local

Crear `.env` a partir de:

```text
.env.example
```

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
```

No versionar credenciales ni claves privadas.

---

## Ejecución local

Desde `backend/`:

```bash
python -m venv .venv
```

Activar el entorno virtual e instalar dependencias:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Levantar el servidor:

```bash
python -m uvicorn app.main:app --reload
```

BackendAPI quedará disponible en:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## Validación manual BackendAPI → RAG

La frontera se validó manualmente utilizando un documento real previamente almacenado en OCI Object Storage.

El flujo probado fue:

```text
document_id real
    ↓
SQLite
    ↓
oci_object_name
    ↓
OCI Object Storage real
    ↓
contenido binario
    ↓
RetrievedDocument
    ↓
RagIntegrationService
    ↓
RagDocumentInput
    ↓
FakeRagPort
```

La validación confirmó que el contrato recibido por el puerto conserva correctamente:

```text
document_id
filename
content_type
content
```

y que los bytes entregados corresponden al documento recuperado físicamente desde OCI.

El `FakeRagPort` se utilizó únicamente para validar la frontera BackendAPI–RAG sin depender todavía del endpoint HTTP real del equipo RAG.

---

## Tests y calidad

Ejecutar:

```bash
python -m ruff check app tests
python -m pytest
```

Estado validado después de retirar la capa anterior de carga:

```text
Ruff: sin errores
Pytest: 55 passed
```

La suite cubre, entre otros:

- carga de documentos PDF, Markdown y TXT;
- validación de extensión y MIME type;
- rechazo de documentos vacíos;
- control de tamaño máximo;
- almacenamiento temporal por bloques;
- eliminación del temporal;
- cálculo de SHA-256;
- detección de duplicados;
- persistencia de metadata;
- almacenamiento persistente mediante Object Storage;
- consulta de metadata por `document_id`;
- recuperación de documentos almacenados;
- preservación exacta del contenido binario recuperado;
- compensación cuando OCI fue exitoso pero falla la persistencia final;
- detección explícita de fallos durante la compensación;
- transformación `RetrievedDocument → RagDocumentInput`;
- preservación del `document_id` canónico al entregar a RAG;
- rechazo de documentos inexistentes o todavía no almacenados;
- traducción de errores RAG a errores de aplicación;
- traducción de `RagDocumentInput` hacia el adapter;
- normalización de errores externos mediante `RagError`.

Las pruebas automatizadas utilizan SQLite temporal y dobles de Object Storage/RAG, por lo que no requieren modificar la base local ni conectarse a OCI real.

Adicionalmente se validó manualmente:

- almacenamiento y recuperación contra OCI Object Storage real;
- compensación controlada ante fallo de persistencia;
- flujo completo `document_id → SQLite → OCI real → RetrievedDocument → RagDocumentInput → FakeRagPort`;
- disponibilidad correcta de Swagger después de retirar `/api/v1/files/upload`.

---

## Pendientes de integración

La responsabilidad actual de BackendAPI para el sprint queda implementada y validada.

Permanece pendiente para los siguientes ciclos:

1. implementar la comunicación HTTP BackendAPI → RAG;
2. adaptar `RagAdapter` al endpoint público definitivo de RAG;
3. registrar esa implementación real en el ciclo de vida de la aplicación;
4. definir la semántica de la respuesta de RAG antes de activar `INDEXING`, `INDEXED` e `INDEXING_FAILED`;
5. implementar el flujo de adaptación pedagógica cuando corresponda al planning del sprint.

BackendAPI no implementará extracción, limpieza, chunking, embeddings, Vector Store, retrieval ni lógica de agentes.

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
- Mantener los contratos entre BackendAPI y los módulos externos explícitos y versionables.
- No incorporar credenciales, claves privadas ni configuración sensible al repositorio.
