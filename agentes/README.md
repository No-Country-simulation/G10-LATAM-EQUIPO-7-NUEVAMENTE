# Agentes: arquitectura y contratos internos

Esta guía describe el funcionamiento del paquete `agentes/`: sus componentes, el recorrido de los datos y los contratos entre la API, el RAG y el proveedor generativo. Para la descripción del producto y su arquitectura global, consulta el [README de la raíz](../README.md).

## Navegación

| Si buscas… | Consulta… |
|---|---|
| Qué cubre este servicio y cómo se separan sus recorridos | [Límites del módulo](#límites-del-módulo) |
| Cómo se conectan indexación, generación y evaluación | [Arquitectura y recorrido de llamadas](#arquitectura-y-recorrido-de-llamadas) |
| Campos y respuestas de los endpoints | [API HTTP](#api-http) |
| Extracción, chunking, almacenamiento vectorial y ranking | [RAG: ingestión, datos y recuperación](#rag-ingestión-datos-y-recuperación) |
| Corpus congelado y contrato de evaluación de retrieval | [Corpus congelado y contrato de evaluación](#corpus-congelado-y-contrato-de-evaluación) |
| Variables de entorno, arranque local y pruebas | [Configuración y ejecución](#configuración-y-ejecución) y [Pruebas](#pruebas) |
| Archivo responsable de un cambio | [Mapa del código](#mapa-del-código) |

## Límites del módulo

El módulo tiene dos recorridos que comparten el motor de recuperación, pero tienen objetivos distintos:

1. **Recorrido de aplicación:** recibe documentos por HTTP, indexa sus chunks y permite generar formatos educativos con evidencia de un documento.
2. **Recorrido de evaluación:** carga un corpus congelado desde CSV y produce respuestas bajo el contrato de retrieval `2.0`, para medir recuperación de evidencia.

La API HTTP de aplicación usa rutas `/api/v1`. La versión `2.0` corresponde únicamente al contrato de evaluación de retrieval. `AgentV1` es el nombre actual de la clase de generación; no determina la versión de esos contratos.

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
    -> AgentV1.extract_learning_metadata
         -> RetrieverService.retrieve
         -> VectorStore.search
         -> Gemini con LearningMetadata
    -> por cada formato solicitado, secuencialmente:
         -> AgentV1.answer
         -> RetrieverService.retrieve
         -> VectorStore.search
         -> Gemini con el esquema Pydantic de ese formato
    -> respuesta con learning_metadata y resultados por formato

Evaluación offline
  generar_lote.generar_lote_resultados
    -> rag.chunks_loader.load_chunks_from_csv
    -> VectorStore.add_chunks
    -> AgentV1.answer_for_evaluation
    -> RetrieverService.retrieve_for_evaluation
    -> rag.contract (contrato 2.0)
```

El endpoint de generación itera por los formatos en serie: la independencia es por resultado, no una ejecución paralela. Cada búsqueda aplica `document_id` como filtro de metadata. La generación usa el texto de los chunks recuperados como contexto, y conserva esos chunks en `sources_used`.

## API HTTP

La aplicación FastAPI se define en `api.py` como `app`. El agente, el servicio de embeddings y el vector store se inicializan al importar ese módulo.

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
  "status": "indexed"
}
```

Las excepciones durante la indexación se convierten en HTTP 500 con su detalle. La ingestión actual no devuelve conteos de páginas o chunks.

### `POST /api/v1/generate`

Entrada JSON (`GenerateRequest`):

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `document_id` | string | Sí | Documento que restringe retrieval. |
| `formats` | string[] | Sí | Formatos a generar: `quiz`, `flashcards`, `tldr`, `video_script`. |
| `profile` | string | Sí | Perfil destinatario usado en la adaptación del contenido. |
| `niche` | string | Sí | Nicho temático usado en query y metadatos pedagógicos. |
| `detail_level` | string | Sí | Nivel de profundidad solicitado. |
| `learning_objective` | string o `null` | No | Objetivo incorporado a query y prompt cuando está presente. |
| `query` | string o `null` | No | Si es truthy, reemplaza la query derivada usada para retrieval. |

Cuando no se proporciona `query`, se construye a partir de `niche`, `profile` y `detail_level`; si hay `learning_objective`, también se agrega. Primero se hace una llamada de retrieval y generación a Gemini para `learning_metadata`. Después, por cada formato solicitado, se vuelve a recuperar contexto y se genera una salida estructurada.

La respuesta tiene esta forma:

```json
{
  "document_id": "doc_123",
  "learning_metadata": {
    "key_concepts": ["Concepto"],
    "prerequisites": ["Conocimiento previo"],
    "estimated_time_minutes": 15
  },
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
      "error_message": null
    }
  ]
}
```

`learning_metadata` está a nivel raíz. Si su extracción falla o no encuentra resultados, la API devuelve listas vacías y tiempo `0`. Cada resultado de formato es independiente: estados posibles incluyen `success`, `no_results` y `failed`; un formato no soportado produce `failed` sin detener los formatos siguientes. Los errores de generación quedan en `error_message`.

Esquemas de `content` (`generated_schemas.py`):

| Formato | Esquema | Campos principales |
|---|---|---|
| `quiz` | `QuizContent` | `title`, `instructions`, `questions`; cada pregunta incluye `question_id`, `question`, `options`, `correct_answer`, `explanation`. |
| `flashcards` | `FlashcardsContent` | `title`, `instructions`, `cards`; cada tarjeta incluye `card_id`, `front`, `back`. |
| `tldr` | `TLDRContent` | `title`, `summary`, `key_points`, `conclusion`. |
| `video_script` | `VideoScriptContent` | `title`, `estimated_duration_minutes`, `scenes`; cada escena incluye `scene_id`, `title`, `narration`, `visual_description`, `duration_seconds`. |

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

Al importar `agent_v1.py` se cargan `GEMINI_API_KEY` y `GEMINI_MODEL` desde el entorno o desde `.env` en la raíz del repositorio. Son obligatorias para inicializar el cliente Gemini. El modelo concreto se elige mediante `GEMINI_MODEL`; no hay un default en código.

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
    ├── test_generation_formats.py
    ├── test_rag.py
    └── test_retrieval_v2.py
```

### Dónde realizar cambios

| Necesidad | Punto de entrada |
|---|---|
| Agregar o cambiar una ruta o contrato HTTP | `api.py` |
| Ajustar el prompt, el contexto o la llamada Gemini | `agent_v1.py` |
| Cambiar la estructura de una salida generada | `generated_schemas.py` y sus pruebas |
| Cambiar el tamaño/solapamiento de chunks o modelo de embeddings | `rag/config.py` |
| Cambiar estrategia de retrieval, filtros o ranking | `rag/vector_store.py` y `rag/retriever.py` |
| Cambiar ingestión de archivos nuevos | `rag/extractor.py`, `rag/cleaner.py`, `rag/chunker.py` |
| Cambiar la lectura o el contrato del benchmark | `rag/chunks_loader.py`, `rag/contract.py` |

## Pruebas

Ejecutar desde la raíz:

```text
python -m pytest agentes/tests/
```

Las pruebas relevantes se distribuyen por componente: `test_rag.py` cubre primitivas RAG y el contrato; `test_retrieval_v2.py` cubre filtros y reranking; `test_api_metadata.py` valida metadatos de la API; `test_generation_formats.py` cubre schemas, endpoints y generación; `test_agente.py` integra el agente con el corpus de evaluación.
