# Agentes: arquitectura y contratos internos

Esta guía describe el funcionamiento del paquete `agentes/`: sus componentes, el recorrido de los datos y los contratos entre la API, el RAG y el proveedor generativo. Para la descripción del producto y su arquitectura global, consulta el [README de la raíz](../README.md).

## Navegación

| Si buscas… | Consulta… |
|---|---|
| Qué cubre este servicio y cómo se separan sus recorridos | [Límites del módulo](#límites-del-módulo) |
| Qué flujo usa hoy la API y qué aporta el grafo Sprint 4 | [Arquitectura y recorrido de llamadas](#arquitectura-y-recorrido-de-llamadas) |
| Campos y respuestas de los endpoints | [API HTTP](#api-http) |
| Extracción, chunking, almacenamiento vectorial y ranking | [RAG: ingestión, datos y recuperación](#rag-ingestión-datos-y-recuperación) |
| Corpus congelado y contrato de evaluación de retrieval | [Corpus congelado y contrato de evaluación](#corpus-congelado-y-contrato-de-evaluación) |
| Variables de entorno, arranque local y pruebas | [Configuración y ejecución](#configuración-y-ejecución) y [Pruebas](#pruebas) |
| Archivo responsable de un cambio | [Mapa del código](#mapa-del-código) |

## Límites del módulo

El módulo contiene estos recorridos, que comparten el motor de recuperación, pero tienen objetivos distintos:

1. **Recorrido de aplicación:** recibe documentos por HTTP, indexa sus chunks y permite generar formatos educativos con evidencia de un documento.
2. **Recorrido de evaluación:** carga un corpus congelado desde CSV y produce respuestas bajo el contrato de retrieval `2.0`, para medir recuperación de evidencia.
3. **Grafo interno de generación:** `graph.py` expone funciones para una generación con recuperación compartida y fan-out de formatos, además de un subgrafo que puede recibir feedback para reescribir. Las diferencias entre este grafo y el flujo activo se resumen en [Pendientes técnicos identificados](#pendientes-técnicos-identificados).

La API HTTP usa rutas `/api/v1`. La versión `2.0` corresponde únicamente al contrato de evaluación de retrieval. `AgentV1` es el nombre actual de la clase; no determina la versión de esos contratos.

## Arquitectura y recorrido de llamadas

```text
POST /api/v1/index
  api.index_document
    -> rag.extractor.extract_document
    -> rag.cleaner.clean_text
    -> rag.chunker.create_chunks
    -> rag.embeddings.MultilingualEmbedding
    -> rag.vector_store.VectorStore.add_chunks
    -> ChromaDB

POST /api/v1/generate
  api.generate_formats
    -> construir query (payload.query o texto derivado del contexto pedagógico)
    -> extraer learning_metadata una vez (retrieval + Gemini)
    -> por cada formato solicitado, secuencialmente:
         -> AgentV1.answer (retrieval + Gemini con el esquema del formato)
    -> respuesta con metadatos, resultados y estado HTTP global

Evaluación offline
  generar_lote.generar_lote_resultados
    -> rag.chunks_loader.load_chunks_from_csv
    -> VectorStore.add_chunks
    -> AgentV1.answer_for_evaluation
    -> RetrieverService.retrieve_for_evaluation
    -> rag.contract (contrato 2.0)

Grafo interno (no invocado por api.py)
  graph.compilar_grafo_generacion
    -> investigador (retrieval compartido)
    -> metadatos y procesamiento de formatos en fan-out
    -> subgrafo por formato: redactor -> finalizar
```

El endpoint HTTP `/generate` itera por los formatos en serie: cada resultado es independiente, pero no se genera en paralelo. La extracción de metadatos y la generación de cada formato hacen sus propias búsquedas, todas filtradas por `document_id`.

El grafo interno es distinto del flujo HTTP activo: recupera contexto una vez, despacha metadatos y formatos en paralelo (con límite de concurrencia) y conserva el orden solicitado al ordenar los resultados. El detalle de las integraciones que faltan para completar ese recorrido está en [Pendientes técnicos identificados](#pendientes-técnicos-identificados).

## API HTTP

La aplicación FastAPI se define en `api.py` como `app`. El agente, el servicio de embeddings y el vector store se inicializan al importar ese módulo.

Rutas implementadas:

| Método y ruta | Función |
|---|---|
| `POST /api/v1/index` | Indexa un PDF, Markdown o TXT. |
| `POST /api/v1/generate` | Extrae metadatos y genera formatos mediante el flujo directo de `AgentV1`. |
| `POST /api/v1/evaluate/retrieval` | Evalúa un caso de retrieval bajo el contrato `2.0`. |
| `POST /api/v1/evaluate/retrieval/batch` | Evalúa entre 1 y 100 casos de retrieval de forma independiente. |
| `GET /api/v1/health` | Informa el estado del vector store y si hay una clave configurada; no llama a Gemini. |
| `DELETE /api/v1/documents/{document_id}` | Elimina los chunks indexados del documento. |

### `POST /api/v1/index`

Entrada `multipart/form-data`:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `document_id` | texto | Sí | Identificador utilizado como metadata para aislar las búsquedas y construir IDs de chunks. |
| `file` | archivo | Sí | PDF con texto, Markdown (`.md`) o texto plano (`.txt`). La extensión determina el extractor. |

Procesamiento: el archivo se escribe temporalmente preservando su extensión; el extractor produce uno o más `Document`; la API agrega `document_id` y `source`, limpia y divide el texto, y guarda los chunks en ChromaDB. El temporal se elimina en el bloque `finally`.

Respuesta exitosa:

```json
{
  "document_id": "doc_123",
  "status": "indexed",
  "document_title": "material.pdf",
  "chunks_indexed": 12
}
```

`document_title` usa el nombre del archivo recibido (o `document_id` si no hay nombre) y `chunks_indexed` es la cantidad indexada. Las excepciones durante la indexación se convierten en HTTP 500 con su detalle.

### `POST /api/v1/generate`

Entrada JSON (`GenerateRequest`):

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `document_id` | string | Sí | Documento que restringe retrieval. |
| `formats` | string[] | Sí | Formatos solicitados. Los soportados son `quiz`, `flashcards`, `tldr`, `video_script`; otros producen un resultado `failed` sin detener los demás. |
| `profile` | string | Sí | Perfil destinatario usado en la adaptación del contenido. |
| `niche` | string | Sí | Nicho temático usado en query y metadatos pedagógicos. |
| `detail_level` | string | Sí | Nivel de profundidad solicitado. |
| `learning_objective` | string o `null` | No | Objetivo incorporado a query y prompt cuando está presente. |
| `query` | string o `null` | No | Si es truthy, reemplaza la query derivada usada para retrieval. |

Cuando `query` no está presente o es una cadena vacía, se construye a partir de `niche`, `profile` y `detail_level`; si hay `learning_objective`, también se agrega. Primero se recupera contexto y se genera `learning_metadata`. Después, para cada formato solicitado, `AgentV1.answer` vuelve a recuperar contexto y genera una salida estructurada. Estas operaciones son secuenciales en el endpoint actual.

La respuesta tiene esta forma:

```json
{
  "document_id": "doc_123",
  "overall_status": "success",
  "document_title": "material.pdf",
  "document_description": "Descripción breve del documento.",
  "execution_time_seconds": 1.23,
  "learning_metadata": {
    "key_concepts": ["Concepto"],
    "prerequisites": ["Conocimiento previo"],
    "estimated_time_minutes": 15
  },
  "learning_metadata_status": "success",
  "learning_metadata_error": null,
  "results": [
    {
      "format": "quiz",
      "status": "success",
      "content": {},
      "sources_used": [
        {
          "rank": 1,
          "chunk_id": "doc_123_1_0",
          "document_id": "doc_123",
          "score": 0.75,
          "text": "Fragmento recuperado"
        }
      ],
      "error_message": null,
      "error": null,
      "execution_time_seconds": 0.8
    }
  ]
}
```

`learning_metadata` está a nivel raíz y contiene `key_concepts`, `prerequisites` y `estimated_time_minutes`. `learning_metadata_status` y el campo opcional `learning_metadata_error` informan si la extracción fue `success`, `no_results` o `failed`; ante un fallo, `learning_metadata` usa valores de respaldo, no listas vacías necesariamente. `document_description` puede ser `null`.

Cada elemento de `results` tiene `format`, `status`, `content`, `sources_used`, `error_message`, `error` y `execution_time_seconds`. Los estados por unidad son `success`, `no_results` y `failed`; en un error, `error` contiene `code`, `message`, `retryable`, `http_status`, `upstream_status` y `provider`. Una unidad fallida no interrumpe las demás.

`overall_status` es `success` si todas las unidades (metadatos y formatos) tuvieron éxito, `partial` si hubo éxitos y fallos, y `failed` si todas fallaron. La API responde HTTP 200, 207 o el HTTP de la causa dominante cuando todo falla (por ejemplo, 404 para `NO_CONTEXT`, 422 para `UNSUPPORTED_FORMAT`, 429 para cuota agotada). La respuesta incluye los detalles de las unidades fallidas.

Esquemas de `content` (`generated_schemas.py`):

| Formato | Esquema | Campos principales |
|---|---|---|
| `quiz` | `QuizContent` | `title`, `instructions`, `questions`; cada pregunta incluye `question_id`, `question`, `options`, `correct_answer`, `explanation`. |
| `flashcards` | `FlashcardsContent` | `title`, `instructions`, `cards`; cada tarjeta incluye `card_id`, `front`, `back`. |
| `tldr` | `TLDRContent` | `title`, `summary`, `key_points`, `conclusion`. |
| `video_script` | `VideoScriptContent` | `title`, `estimated_duration_minutes`, `scenes`; cada escena incluye `scene_id`, `title`, `narration`, `visual_description`, `duration_seconds`. |

### Evaluación de retrieval

`POST /api/v1/evaluate/retrieval` recibe `case_id`, `query`, `top_k` (1–50; por defecto 5) y `metadata_filters` opcional. `POST /api/v1/evaluate/retrieval/batch` recibe `cases` con entre 1 y 100 elementos con esos mismos campos. Los modelos rechazan campos adicionales.

Cada resultado conserva el contrato `2.0`: `contract_version`, `case_id`, `query`, `top_k`, `score_type`, `status`, `results` y `error`. Los estados son `success`, `no_results` y `error`; `no_results` es una evaluación válida con resultados vacíos. En lote, `results` mantiene el orden de `cases`, y el resumen incluye `overall_status`, `total`, `succeeded`, `failed` y `execution_time_seconds`. Los errores de caso son `INVALID_INPUT` (422) o `RETRIEVAL_FAILED` (500); los lotes mixtos responden 207.

### Salud y eliminación

`GET /api/v1/health` devuelve `status` (`ok` o `degraded`), `model`, `gemini_key_configured` y `vector_store_ok`; no verifica una llamada al proveedor. `DELETE /api/v1/documents/{document_id}` devuelve `status` (`deleted` o `not_found`) y `chunks_deleted`; cuando no hay chunks, responde HTTP 404.

### Grafo interno y evaluación semántica

`graph.py` ofrece `compilar_grafo_generacion` y `compilar_subgrafo_formato`. En el grafo, el Investigador recupera y filtra contexto por documento una vez; después se despachan metadatos y formatos mediante fan-out, con concurrencia limitada por `GRAPH_MAX_CONCURRENCY` (valor por defecto 3, mínimo 1). El subgrafo de cada formato realiza una sola llamada de generación y finaliza un resultado con la misma forma de `results[]`. Para las integraciones que aún faltan, consulta [Pendientes técnicos identificados](#pendientes-técnicos-identificados).

## RAG: ingestión, datos y recuperación

### Tipos y configuración

`rag/models.py` define `Document(text, metadata)`, `Chunk(id, text, metadata)` y `SearchResult(chunk_id, text, score, metadata)`. `SearchResult.document_id` se lee de metadata y falla explícitamente si no existe; no se infiere del nombre del archivo.

`rag/config.py` concentra los valores por defecto:

| Parámetro | Valor actual | Uso |
|---|---|---|
| `chunk_size` | `900` | Tamaño objetivo del chunk. |
| `chunk_overlap` | `150` | Solapamiento entre chunks consecutivos. |
| `top_k_default` | `5` | Cantidad de resultados finales por defecto. |
| `embedding_model_name` | `paraphrase-multilingual-mpnet-base-v2` | Modelo de embeddings de `sentence-transformers`. |
| `vector_store_path` | `./chroma_db` | Persistencia local de ChromaDB. |
| `collection_name` | `nuevamente_v1` | Colección por defecto. |

### Ingestión de documentos nuevos

`rag.extractor.extract_document(path)` soporta `.pdf`, `.md` y `.txt`. Los PDF se extraen página por página y el resto como un único documento UTF-8. No hay OCR: una página PDF sin texto extraíble produce texto vacío.

`rag.cleaner.clean_text` normaliza Unicode y saltos de línea, sin eliminar espacios internos ni indentación. `rag.chunker.create_chunks` divide cada documento mediante `RecursiveCharacterTextSplitter`; valida que `chunk_overlap < chunk_size`. Los IDs se forman como `{document_id}_{page}_{chunk_index}`.

`rag.pipeline.ingest_file` reúne extracción, limpieza, chunking e indexación para uso desde código. El endpoint HTTP implementa ese flujo directamente y añade el metadata de origen del archivo antes de crear los chunks.

### Vector store y algoritmo de búsqueda

`rag.vector_store.VectorStore` persiste los embeddings en una colección ChromaDB con distancia coseno y crea un Cross-Encoder para reranking. `add_chunks` codifica los textos e inserta/actualiza por ID.

`search(query, top_k, filters)` realiza estos pasos:

1. Codifica la consulta.
2. Recupera hasta `top_k * 3` candidatos semánticos desde ChromaDB, aplicando `filters`.
3. Obtiene los documentos que cumplen el mismo filtro y calcula BM25; conserva hasta `top_k * 3` candidatos con score lexical positivo.
4. Fusiona los rankings por ID con Reciprocal Rank Fusion (`k=60`).
5. Reordena los candidatos fusionados con el Cross-Encoder y devuelve los primeros `top_k` como `SearchResult`. El score expuesto es el score del Cross-Encoder.

`rag.retriever.RetrieverService` valida que la query no esté vacía y que `top_k > 0`. `retrieve` acepta `document_id` y/o filtros de metadata; `retrieve_for_evaluation` requiere `case_id` y convierte errores de entrada o recuperación al contrato de evaluación.

## Corpus congelado y contrato de evaluación

El benchmark tiene que preservar los IDs, textos, límites y metadata acordados. Por ello, `rag.chunks_loader.load_chunks_from_csv` carga directamente columnas `chunk_id`, `document_id` y `chunk_text`, más metadata opcional. No aplicar `clean_text` ni `create_chunks` a este corpus: alteraría los datos evaluados.

`rag.pipeline.ingest_ground_truth_v1(csv_path, vector_store)` carga e indexa el CSV congelado. `generar_lote.py` usa por defecto:

- `Data_IA/data/evaluation/chunks_v1.csv`
- `Data_IA/data/evaluation/ground_truth_v1.csv`

Desde la raíz del repositorio se puede ejecutar el lote con `python -m agentes.generar_lote`. Escribe `agentes/retrieval_results_agentes_v1.json`.

`AgentV1.answer_for_evaluation(case_id, query, top_k=5, metadata_filters=None)` delega a `RetrieverService.retrieve_for_evaluation`. El contrato se construye en `rag/contract.py` y mantiene estas claves en los estados `success`, `no_results` y `error`:

```json
{
  "contract_version": "2.0",
  "case_id": "CASE-001",
  "query": "consulta",
  "top_k": 5,
  "score_type": "cross_encoder",
  "status": "success",
  "results": [],
  "error": null
}
```

Cada resultado exitoso lleva `rank`, `chunk_id`, `document_id`, `score`, `text` y `metadata`. En errores, `error` contiene `code` y `message`; si no hay coincidencias, `results` queda vacío y `error` es `null`.

## Configuración y ejecución

Al importar `agent_v1.py` se cargan `GEMINI_API_KEY` y `GEMINI_MODEL` desde el entorno o desde `.env` en la raíz del repositorio. Son obligatorias para inicializar el cliente Gemini. El modelo concreto se elige mediante `GEMINI_MODEL`; no hay un default en código. `GEMINI_FALLBACK_MODEL` es opcional y agrega un modelo alternativo si se agotan los reintentos del principal. `GEMINI_MAX_RETRIES` controla los reintentos por modelo y tiene default 3.

Para el grafo interno, `GRAPH_MAX_CONCURRENCY` controla el máximo de tareas concurrentes (default 3; mínimo efectivo 1 y default si el valor no es entero). No afecta al endpoint HTTP `/generate`, que es secuencial.

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r agentes\requirements.txt
uvicorn agentes.api:app --reload --port 8001
```

Para macOS/Linux, activar el entorno con `source .venv/bin/activate`. Swagger queda en `http://127.0.0.1:8001/docs`. El `Dockerfile` espera contexto de build en la raíz del repositorio porque copia `agentes/requirements.txt` y `agentes/`.

## Mapa del código

```text
agentes/
├── api.py                    # App FastAPI, modelos de entrada y endpoints HTTP
├── agent_v1.py               # Orquestación de retrieval, prompts y Gemini
├── generated_schemas.py      # Modelos Pydantic de metadatos y formatos
├── graph.py                  # Grafo interno de generación y adaptador del evaluador V2
├── nodes.py                  # Redactor, reglas de revisión y construcción del resultado
├── state.py                  # Estados global/por formato y constructores del grafo
├── errors.py                 # Catálogo de errores y política de status HTTP
├── evaluator_contract.py     # Modelos del contrato V2 de evaluación semántica
├── generar_lote.py           # Runner del benchmark offline
├── Dockerfile                # Imagen del servicio; build context en raíz del repo
├── requirements.txt          # Dependencias Python del módulo
├── retrieval_results_agentes_v1.json # Salida guardada de benchmark
├── rag/
│   ├── config.py             # Configuración por defecto del RAG
│   ├── models.py             # Document, Chunk y SearchResult
│   ├── extractor.py          # PDF, Markdown y TXT
│   ├── cleaner.py            # Normalización conservadora
│   ├── chunker.py            # Chunking de documentos nuevos
│   ├── embeddings.py         # Adaptador sentence-transformers
│   ├── vector_store.py       # ChromaDB, BM25, RRF y Cross-Encoder
│   ├── retriever.py          # Validación y contrato de recuperación
│   ├── chunks_loader.py      # Importación literal del corpus CSV congelado
│   ├── pipeline.py           # Pipelines de ingestión reutilizables
│   └── contract.py           # Respuestas de evaluación retrieval 2.0
└── tests/
    ├── conftest.py
    ├── test_agente.py
    ├── test_api_metadata.py
    ├── test_error_propagation.py
    ├── test_evaluation_endpoints.py
    ├── test_generation_formats.py
    ├── test_graph.py
    ├── test_integration_niche.py
    ├── test_nodes.py
    ├── test_rag.py
    ├── test_retrieval_v2.py
    └── test_state.py
```

### Dónde realizar cambios

Esta sección es un **mapa del código**: indica qué archivos revisar o modificar según el comportamiento que quieras cambiar. No es una lista de tareas pendientes ni implica que haya que hacer esos cambios.

| Necesidad | Punto de entrada |
|---|---|
| Agregar o cambiar una ruta o contrato HTTP | `api.py` y las pruebas de endpoint correspondientes |
| Ajustar el prompt, el contexto o la llamada Gemini | `agent_v1.py` |
| Cambiar la estructura de una salida generada | `generated_schemas.py` y sus pruebas |
| Cambiar el flujo interno del grafo, su concurrencia o el estado | `graph.py`, `nodes.py`, `state.py` |
| Cambiar la validación/traducción del evaluador semántico V2 | `evaluator_contract.py`, `graph.py` |
| Cambiar catálogo de errores o política HTTP global | `errors.py` |
| Cambiar el tamaño/solapamiento de chunks o modelo de embeddings | `rag/config.py` |
| Cambiar estrategia de retrieval, filtros o ranking | `rag/vector_store.py` y `rag/retriever.py` |
| Cambiar ingestión de archivos nuevos | `rag/extractor.py`, `rag/cleaner.py`, `rag/chunker.py` |
| Cambiar la lectura o el contrato del benchmark | `rag/chunks_loader.py`, `rag/contract.py` |

## Pruebas

Ejecutar desde la raíz:

```text
python -m pytest agentes/tests/
```

Las pruebas relevantes se distribuyen por componente: `test_rag.py` cubre primitivas RAG; `test_retrieval_v2.py` y `test_evaluation_endpoints.py` cubren retrieval y sus rutas; `test_api_metadata.py`, `test_generation_formats.py` y `test_error_propagation.py` cubren la API de aplicación; `test_graph.py`, `test_nodes.py` y `test_state.py` cubren el grafo interno y sus contratos; `test_agente.py` integra el agente con el corpus de evaluación.

## Pendientes técnicos identificados

Esta lista resume diferencias observables entre el código actual y un flujo integrado de generación, evaluación semántica y corrección. Es una referencia técnica derivada de la implementación; no sustituye ni confirma el backlog o los acuerdos del equipo.

- **Conectar el grafo a la generación HTTP, si ese es el flujo objetivo.** Actualmente `/api/v1/generate` usa el flujo directo de `AgentV1`; no invoca `compilar_grafo_generacion`. Por eso el endpoint vuelve a recuperar contexto por cada formato y los procesa secuencialmente.
- **Integrar la evaluación semántica y la corrección automática.** `traducir_respuesta_evaluador` valida y traduce una respuesta V2 recibida, y el subgrafo puede consumir `feedback` inyectado; el código de agentes no solicita la evaluación ni encadena evaluador y redactor automáticamente.
- **Definir e implementar la ruta HTTP de revisión, si se requiere.** No existe actualmente un endpoint `/revise` en `api.py`; el subgrafo de formato es una función interna y no está expuesto como endpoint.
- **Conectar el router de revisión al subgrafo, si se requiere reintentar automáticamente.** Aunque `nodes.py` define `ruta_tras_redactor` y lógica para reescrituras, `compilar_subgrafo_formato` compila el recorrido lineal `redactor -> finalizar`; no usa ese router.
