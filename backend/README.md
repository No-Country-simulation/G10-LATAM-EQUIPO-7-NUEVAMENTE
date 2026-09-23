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
- Eliminación del archivo temporal después del almacenamiento permanente.
- Dominio y estados de documentos y procesos.
- Endpoint legacy `/api/v1/files/upload`, mantenido temporalmente por compatibilidad.

Pendiente de implementación funcional:

- Conectar `RagAdapter` con el entry point público definitivo que exponga el equipo RAG.
- Registrar la implementación concreta del adapter en el ciclo de vida de la aplicación cuando el entry point real esté disponible.
- Definir, junto con RAG, la semántica exacta de finalización de la indexación antes de activar transiciones automáticas `INDEXING → INDEXED`.
- Implementación futura de otro motor de persistencia, por ejemplo PostgreSQL/Supabase, si el despliegue lo requiere.
- Retiro progresivo de la capa legacy asociada a `/files/upload`.

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
| `ports/` | Contratos hacia persistencia, almacenamiento e integraciones |
| `infrastructure/` | Implementaciones concretas |
| `core/` | Configuración, logging, errores y utilidades |
| `services/` | Compatibilidad temporal con flujos legacy |

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
DocumentService
     ↓
ObjectStoragePort
     ↑
OCIObjectStorage
     ↓
OCI Object Storage
```

De esta forma, la autenticación y las llamadas específicas al proveedor quedan encapsuladas en `infrastructure/storage/`.

El mismo contrato abstrae escritura, recuperación y eliminación de objetos:

```text
upload_file(...)
download_file(...)
delete_object(...)
```

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

La integración se divide en dos fronteras:

```text
Application
    ↓
RagPort
    ↑
RagAdapter
    ↓
entry point público de RAG
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
│   │   ├── rag_integration_service.py
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
│   └── services/
│       └── storage.py                    # compatibilidad legacy
├── tests/
│   ├── conftest.py
│   ├── fakes.py
│   ├── test_health.py
│   ├── unit/
│   │   ├── test_document_service.py
│   │   ├── test_oci_object_storage.py
│   │   ├── test_rag_integration_service.py
│   │   └── test_rag_adapter.py
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

La decisión v1 es explícita: **BackendAPI recupera el archivo desde OCI y entrega el contenido binario completo a RAG**.

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

### Adaptador

`RagAdapter` implementa `RagPort` y traduce `RagDocumentInput` al entry point público de RAG.

Actualmente el adapter depende de una interfaz mínima inyectable:

```text
RagEntryPoint
```

Esto permite probar y cerrar la arquitectura BackendAPI sin acoplarla a una clase interna concreta del otro equipo.

La única pieza pendiente para la integración real es reemplazar esa expectativa por el entry point público definitivo que confirme RAG.

Si RAG cambia internamente su pipeline, Vector Store, Retriever o tecnología de embeddings, esos cambios no deben propagarse a `application/` ni al dominio de BackendAPI.

### Errores

Los fallos del entry point externo se normalizan como:

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

La razón es contractual: hasta que el equipo RAG confirme si su entry point retorna al aceptar el documento o al finalizar realmente la indexación, BackendAPI no debe marcar un documento como `INDEXED` basándose en una suposición.

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

El `FakeRagPort` se utilizó únicamente para validar la frontera BackendAPI–RAG sin depender todavía del entry point real del equipo RAG.

---

## Tests y calidad

Ejecutar:

```bash
python -m ruff check app tests
python -m pytest
```

Estado validado en esta implementación:

```text
Ruff: sin errores
Pytest: suite completa aprobada
```

La suite incluye, además de las pruebas existentes:

- recuperación de documentos almacenados mediante `document_id`;
- preservación exacta del contenido binario recuperado;
- compensación cuando OCI fue exitoso pero falla la persistencia final;
- detección explícita de fallos durante la compensación;
- transformación `RetrievedDocument → RagDocumentInput`;
- preservación del `document_id` canónico al entregar a RAG;
- rechazo de documentos inexistentes o todavía no almacenados;
- traducción de errores RAG a errores de aplicación;
- traducción de `RagDocumentInput` hacia el entry point mediante `RagAdapter`;
- normalización de errores externos mediante `RagError`.

Las pruebas automatizadas utilizan SQLite temporal y dobles de Object Storage/RAG, por lo que no requieren modificar la base local ni ejecutar el módulo RAG real.

Adicionalmente se validó manualmente:

- almacenamiento y recuperación contra OCI Object Storage real;
- compensación controlada ante fallo de persistencia;
- flujo completo `document_id → SQLite → OCI real → RetrievedDocument → RagDocumentInput → FakeRagPort`.

---

## Pendientes de integración

La parte BackendAPI de la tarjeta queda implementada y validada.

Permanece pendiente únicamente:

1. que el equipo RAG confirme su entry point público definitivo;
2. adaptar `RagAdapter` a esa firma concreta;
3. registrar esa implementación real en el ciclo de vida de la aplicación;
4. definir si el retorno del entry point significa “aceptado para indexación” o “indexación terminada” antes de activar `INDEXING`, `INDEXED` e `INDEXING_FAILED`.

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
