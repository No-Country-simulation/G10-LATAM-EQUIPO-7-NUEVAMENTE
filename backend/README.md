# NuevaMente — BackendAPI

Backend de **NuevaMente**, desarrollado con **FastAPI** y **Pydantic v2**.

BackendAPI gestiona la recepción técnica de documentos, su validación, identificación, persistencia de metadata y estado, almacenamiento del archivo original en OCI Object Storage y los contratos de integración con RAG y Agentes.

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
- Persistencia de metadata y estado mediante una capa de repositorio desacoplada.
- Implementación actual del repositorio mediante SQLite.
- Consulta de metadata mediante `GET /api/v1/documents/{document_id}`.
- Selección centralizada del repositorio mediante `repository_factory.py`.
- Contrato desacoplado de almacenamiento mediante `ObjectStoragePort`.
- Implementación de OCI Object Storage mediante `OCIObjectStorage`.
- Persistencia del archivo original en OCI utilizando la convención `documents/{document_id}/original.ext`.
- Persistencia de `oci_object_name` en la metadata del documento.
- Gestión de estados `VALIDATED → STORING → STORED`.
- Gestión del estado `STORAGE_FAILED` cuando falla Object Storage.
- Eliminación del archivo temporal después del almacenamiento permanente.
- Dominio y estados de documentos y procesos.
- Puertos provisionales para RAG y Agentes.
- Pruebas unitarias y de integración.
- Endpoint legacy `/api/v1/files/upload`, mantenido temporalmente por compatibilidad.

Pendiente de implementación funcional:

- Recuperación de documentos desde OCI Object Storage.
- Cierre del contrato BackendAPI–RAG.
- Integración real con RAG.
- Cierre del contrato BackendAPI–Agentes.
- Integración real con Agentes.
- Endpoints funcionales de adaptaciones y procesos.
- Implementación futura de otro motor de persistencia, por ejemplo PostgreSQL/Supabase, si el despliegue lo requiere.
- Retiro progresivo de la capa legacy asociada a `/files/upload`.

---

## Stack

| Componente | Tecnología |
|---|---|
| API | FastAPI |
| Servidor | Uvicorn |
| Validación | Pydantic v2 |
| Configuración | Pydantic Settings |
| Uploads | python-multipart |
| Persistencia actual | SQLite |
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
| `api/` | Endpoints HTTP y dependencias de FastAPI |
| `schemas/` | Contratos externos de entrada y salida |
| `domain/` | Entidades, estados y reglas del dominio |
| `application/` | Casos de uso y orquestación |
| `ports/` | Contratos hacia persistencia e integraciones |
| `infrastructure/` | Implementaciones concretas |
| `core/` | Configuración, logging, errores y utilidades |
| `rag/` | Espacio reservado para el equipo RAG |
| `agents/` | Espacio reservado para RAG/Agentes |

### Persistencia de metadata

El endpoint HTTP no conoce directamente el motor de base de datos. `DocumentService` depende del contrato `DocumentRepository`.

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

Esto permite incorporar posteriormente otra implementación, por ejemplo PostgreSQL/Supabase, sin modificar los endpoints ni los casos de uso.

### Almacenamiento de objetos

La lógica de aplicación tampoco depende directamente del SDK de OCI.

```text
documents.py
     ↓
DocumentService
     ↓
ObjectStoragePort
     ↑
OCIObjectStorage
     ↓
OCI Object Storage
```

De esta forma, la autenticación y las llamadas específicas al proveedor quedan encapsuladas en `infrastructure/storage/`.

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
│   │   │   ├── repository_factory.py
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
│   ├── fakes.py
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

## Carga, validación, identificación y almacenamiento de documentos

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

### Contrato Frontend → BackendAPI

La solicitud debe enviarse como:

```text
Content-Type: multipart/form-data
Campo: file
```

No se debe enviar el archivo en Base64 ni dentro de JSON.

Ejemplo:

```javascript
const formData = new FormData();
formData.append("file", file);

const response = await fetch(
  "http://localhost:8000/api/v1/documents",
  {
    method: "POST",
    body: formData
  }
);
```

No se debe configurar manualmente el header `Content-Type` al utilizar `FormData`; el navegador agrega automáticamente el `boundary`.

### Validaciones actuales

El flujo valida:

- extensión permitida;
- MIME type declarado compatible con el formato;
- tamaño máximo configurado;
- archivo no vacío;
- nombre apto para almacenamiento temporal.

Los archivos con extensión o MIME no soportado son rechazados con `415 Unsupported Media Type`.

Los archivos vacíos son rechazados con `400 Bad Request`.

Los archivos que superan el tamaño máximo configurado son rechazados con `413 Content Too Large`.

### Flujo actual

```text
UploadFile
   ↓
validación de extensión y MIME
   ↓
almacenamiento temporal local
   ├─ saneamiento de nombre
   └─ control de tamaño
   ↓
validación de archivo no vacío
   ↓
SHA-256 del contenido
   ↓
DocumentRepository.find_by_sha256()
   │
   ├─ duplicado almacenado
   │      ↓
   │   recuperar document_id
   │      ↓
   │   duplicate = true
   │      ↓
   │   HTTP 200
   │
   └─ documento nuevo
          ↓
       generar document_id
          ↓
       registrar metadata
          ↓
       VALIDATED
          ↓
       STORING
          ↓
       OCI Object Storage
          ↓
       guardar oci_object_name
          ↓
       STORED
          ↓
       eliminar temporal
          ↓
       HTTP 201
```

### Documento nuevo

Ejemplo de respuesta:

```json
{
  "document_id": "doc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "filename": "documento.txt",
  "status": "stored",
  "duplicate": false
}
```

Código HTTP:

```text
201 Created
```

### Documento duplicado

Ejemplo de respuesta:

```json
{
  "document_id": "doc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "filename": "documento.txt",
  "status": "stored",
  "duplicate": true
}
```

Código HTTP:

```text
200 OK
```

El documento duplicado conserva el mismo `document_id`.

Si el documento ya posee un `oci_object_name`, BackendAPI no vuelve a subir el mismo contenido a Object Storage.

La ruta física del archivo temporal no se expone en el contrato HTTP y el temporal se elimina después del procesamiento.

### Error de Object Storage

Si el registro del documento fue creado pero falla el almacenamiento permanente, BackendAPI:

1. actualiza el estado a `STORAGE_FAILED`;
2. persiste el nuevo estado;
3. elimina el archivo temporal;
4. responde con `502 Bad Gateway`.

---

## Persistencia de metadata y estado

La metadata interna de un documento se guarda en una base de datos separada del archivo original.

Actualmente se persisten:

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

El archivo original no se almacena en SQLite. El original se persiste en OCI Object Storage.

### Contrato de repositorio

La aplicación depende de:

```text
DocumentRepository
```

que define las operaciones necesarias:

```text
create(document)
find_by_id(document_id)
find_by_sha256(sha256)
update(document)
```

La implementación actual es:

```text
SQLiteDocumentRepository
```

El desacoplamiento permite implementar posteriormente:

```text
PostgreSQLDocumentRepository
```

o una integración basada en Supabase, sin cambiar los endpoints ni `DocumentService`.

### Conversión dominio ↔ persistencia

La capa de aplicación trabaja con:

```text
domain.Document
```

La infraestructura convierte esa entidad a:

```text
DocumentRecord
```

mediante:

```text
DocumentRecord.from_domain(document)
```

Al consultar desde SQLite ocurre el proceso inverso:

```text
SQLite Row
   ↓
DocumentRecord.from_row(...)
   ↓
DocumentRecord.to_domain()
   ↓
domain.Document
```

De esta forma, `DocumentService` nunca depende de filas SQLite ni de modelos específicos del motor de base de datos.

### Configuración actual

```env
DATABASE_URL=sqlite:///storage/nuevamente.db
```

La selección del repositorio se realiza a partir de `DATABASE_URL`.

Actualmente solo está implementado SQLite. Si se configura un motor no soportado, BackendAPI genera un error explícito.

---

## Consulta de documentos

El endpoint:

```text
GET /api/v1/documents/{document_id}
```

consulta la metadata y el estado actual de un documento previamente registrado.

Ejemplo:

```json
{
  "document_id": "doc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "filename": "documento.txt",
  "status": "stored",
  "content_type": "text/plain",
  "size_bytes": 68,
  "created_at": "2026-09-22T23:27:00Z",
  "updated_at": "2026-09-22T23:27:00Z"
}
```

Si el documento no existe:

```text
404 Not Found
```

con una respuesta controlada.

---

## Gestión de estados

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

BackendAPI administra actualmente:

```text
RECEIVED → VALIDATED → STORING → STORED
```

La transición hacia `INDEXING` e `INDEXED` corresponderá a la integración con RAG.

Las actualizaciones de estado son responsabilidad de los casos de uso internos y utilizan:

```text
DocumentRepository.update(document)
```

No se expone un endpoint genérico para permitir que el frontend modifique libremente el estado de un documento.

---

## Almacenamiento

### Temporal local

El archivo recibido se escribe temporalmente por bloques, se sanea el nombre utilizado localmente y se controla el tamaño máximo configurado.

Actualmente `POST /documents` reutiliza temporalmente el adaptador `services.storage/save_upload`, que a su vez delega en `infrastructure/storage/LocalFileStorage`.

`services/` permanece como capa de compatibilidad mientras exista el endpoint legacy `/files/upload`. Esta dependencia deberá retirarse progresivamente para evitar mantener dos caminos de carga paralelos.

### OCI Object Storage

El contrato de almacenamiento permanente se define mediante:

```text
ObjectStoragePort
```

La implementación concreta actual es:

```text
infrastructure/storage/oci_object_storage.py
```

con:

```text
OCIObjectStorage
```

El adapter utiliza OCI Python SDK para interactuar con el bucket configurado.

Convención de objetos:

```text
documents/{document_id}/original.pdf
documents/{document_id}/original.md
documents/{document_id}/original.txt
```

El valor se persiste en:

```text
oci_object_name
```

El bucket, namespace, región y perfil de autenticación se obtienen desde configuración externa y no están acoplados al código de aplicación.

La integración fue validada manualmente contra un bucket OCI configurado para el proyecto mediante una operación real `PUT`, obteniendo respuesta exitosa del servicio y persistiendo posteriormente el `oci_object_name` y estado `STORED` en la base de datos local.

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

### Contratos provisionales

El contrato `RagDocumentInput` continúa siendo provisional. Actualmente contempla el contenido binario del documento, pero la integración definitiva BackendAPI–RAG deberá decidir si RAG recibe:

- el contenido binario completo; o
- una referencia al documento almacenado (`document_id` / referencia de Object Storage) y lo recupera desde allí.

El contrato de adaptación también permanece provisional. Los parámetros definitivos deberán acordarse con Frontend y Agentes antes de cerrar esa integración.

---

## Endpoints

| Método | Ruta | Estado |
|---|---|---|
| `GET` | `/` | Implementado |
| `GET` | `/api/v1/health` | Implementado |
| `POST` | `/api/v1/documents` | Implementado: valida, identifica, persiste metadata y almacena original en OCI |
| `GET` | `/api/v1/documents/{document_id}` | Implementado: consulta metadata y estado |
| `POST` | `/api/v1/files/upload` | Implementado — legacy |

### Respuestas de `POST /api/v1/documents`

| Código | Significado |
|---|---|
| `200` | Documento previamente registrado |
| `201` | Documento nuevo registrado y almacenado |
| `400` | Documento vacío o inválido |
| `413` | Documento demasiado grande |
| `415` | Formato o MIME type no soportado |
| `422` | Error de validación de la petición |
| `502` | Error al almacenar el documento en Object Storage |

### Respuestas de `GET /api/v1/documents/{document_id}`

| Código | Significado |
|---|---|
| `200` | Documento encontrado |
| `404` | Documento no encontrado |

Los routers de adaptaciones y procesos existen, pero todavía no exponen operaciones funcionales.

Próximos contratos:

```text
POST /api/v1/adaptations
GET  /api/v1/processes/{process_id}
```

---

## Configuración

Crear `.env` a partir de `.env.example`.

Ejemplo:

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
OCI_CONFIG_FILE=~/.oci/config
OCI_CONFIG_PROFILE=DEFAULT
```

### Autenticación OCI en desarrollo local

El SDK puede utilizar un archivo de configuración externo, normalmente:

```text
~/.oci/config
```

Ejemplo conceptual:

```ini
[DEFAULT]
user=...
fingerprint=...
tenancy=...
region=...
key_file=/ruta/a/clave_privada.pem
```

También se pueden utilizar perfiles separados:

```ini
[NUEVAMENTE]
user=...
fingerprint=...
tenancy=...
region=...
key_file=/ruta/a/clave_privada.pem
```

y seleccionar el perfil mediante:

```env
OCI_CONFIG_PROFILE=NUEVAMENTE
```

### Seguridad

No se deben almacenar en Git:

- `.env` real;
- claves privadas `.pem`;
- archivo local `~/.oci/config`;
- base SQLite local;
- archivos temporales cargados.

El repositorio ya ignora `.env` y `storage/`. Las credenciales OCI deben permanecer fuera del proyecto.

---

## Instalación

### Windows PowerShell

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements-dev.txt

Copy-Item .env.example .env

python -m uvicorn app.main:app --reload
```

### Linux / macOS

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements-dev.txt

cp .env.example .env

python -m uvicorn app.main:app --reload
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
python -m ruff check app tests
python -m pytest
```

Estado actual validado:

```text
41 passed
```

La suite incluye pruebas de:

- dominio;
- schemas;
- hashing;
- servicios de aplicación;
- repositorio SQLite;
- creación de documentos;
- consulta por `document_id`;
- consulta por SHA-256;
- actualización de metadata y estado;
- selección del repositorio mediante factory;
- motor de base de datos no soportado;
- almacenamiento local;
- salud del servicio;
- carga de PDF, Markdown y TXT;
- extensión no soportada;
- MIME type incompatible;
- archivo vacío;
- límite de tamaño;
- identificación mediante `document_id`;
- detección de duplicados;
- almacenamiento mediante un `FakeObjectStorage`;
- eliminación del temporal después del almacenamiento;
- prevención de una segunda carga al detectar un duplicado ya almacenado;
- fallo simulado de Object Storage y respuesta `502`;
- respuesta `404` para documentos inexistentes;
- compatibilidad del endpoint legacy.

Las pruebas automatizadas utilizan una base SQLite temporal y dobles de prueba para Object Storage. Por tanto, la suite no requiere conectarse a OCI ni modifica la base local de desarrollo.

La conexión real con OCI debe validarse separadamente como prueba de integración manual o en un entorno de integración controlado.

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
- Mantener los contratos entre BackendAPI, RAG y Agentes explícitos y versionables.
- No incorporar credenciales, claves privadas ni configuración sensible al repositorio.
