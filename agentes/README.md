Markdown
# NuevaMente - Agentes: Orquestación con LangGraph y RAG Core = Arquitectura Multiagente

Módulo central de ingestión, recuperación de conocimiento (RAG) y orquestación de agentes para el hackathon NuevaMente (G10-LATAM-EQUIPO-7). Integra FastAPI, bases de datos vectoriales (ChromaDB), los modelos de la familia Gemini mediante el SDK oficial (`google-genai`) y flujos de estado con LangGraph.

## Novedades: Sprint 4 (LangGraph, Map-Reduce y Manejo de Errores)

La arquitectura evolucionó hacia un sistema de grafos de estado para garantizar concurrencia, resiliencia y corrección autónoma:

* **Arquitectura Map-Reduce con LangGraph:** Transición de cadenas secuenciales a un grafo global. Un nodo Investigador extrae contexto y hace un *fan-out* paralelo para generar formatos simultáneamente, reduciendo drásticamente el tiempo total de ejecución E2E.
* **Subgrafo de Revisión Activo:** Cada formato tiene su propio ciclo de vida aislado (Atomicidad). El flujo incluye un enrutamiento condicional inteligente: si el Evaluador detecta falta de respaldo, el Revisor activa un nodo de **Nueva Evidencia** para hacer una segunda búsqueda en ChromaDB antes de re-escribir.
* **Contratos HTTP Estrictos y Propagación de Errores:** Respeto estricto del contrato con Backend. Los errores se propagan sin enmascararse, devolviendo `404` (NO_CONTEXT), `429` (RESOURCE_EXHAUSTED) o `503` (PROVIDER_UNAVAILABLE) en fallos totales, y reservando `207 Multi-Status` solo para resultados parciales genuinos.
* **Manejo de Estado Dual (`AgentState` y `FormatState`):** Memoria compartida donde las fallas de la API (ej. cuota) se aíslan y reportan instantáneamente, mientras que los fallos de salida del modelo activan reintentos automáticos configurables.

## Novedades Previas: Sprint 3 (Retrieval V2)
* **Búsqueda Híbrida + RRF:** Búsqueda semántica combinada con lexical (BM25) y Cross-Encoder.
* **Inyección Dinámica de Nicho:** El parámetro `niche` adapta los conceptos clave y prerrequisitos estrictamente al dominio solicitado.

El módulo contiene estos recorridos, que comparten el motor de recuperación, pero tienen objetivos distintos:

1. **Recorrido de aplicación:** recibe documentos por HTTP, indexa sus chunks y permite generar formatos educativos con evidencia de un documento.
2. **Recorrido de evaluación:** carga un corpus congelado desde CSV y produce respuestas bajo el contrato de retrieval `2.0`, para medir recuperación de evidencia.
3. **Grafo interno de generación:** `graph.py` expone funciones para una generación con recuperación compartida y fan-out de formatos, además de un subgrafo que puede recibir feedback para reescribir. Las diferencias entre este grafo y el flujo activo se resumen en [Pendientes técnicos identificados](#pendientes-técnicos-identificados).

    agentes/
    ├── rag/                           # RAG Core (Motor de Ingesta y Recuperación)
    │   ├── chunker.py                 # Segmentación de documentos en fragmentos[cite: 11]
    │   ├── chunks_loader.py           # Utilidad para carga estructurada de fragmentos[cite: 11]
    │   ├── cleaner.py                 # Limpieza de texto y aplicación de filtros regex[cite: 11]
    │   ├── config.py                  # Configuración centralizada (chunk_size, top_k, modelo)[cite: 11]
    │   ├── contract.py                # Builders y tipificación del contrato de evaluación[cite: 11]
    │   ├── embeddings.py              # Servicio de generación de embeddings (MultilingualEmbedding)[cite: 11]
    │   ├── extractor.py               # Lógica de extracción de texto desde archivos (.pdf, .md, .txt)[cite: 11]
    │   ├── models.py                  # Modelos de datos del RAG (Document, Chunk, SearchResult)[cite: 11]
    │   ├── pipeline.py                # Flujos de ingesta (ej. ingest_file, ingest_ground_truth_v1)[cite: 11]
    │   ├── retriever.py               # Motor de búsqueda (Retrieval híbrido y prefiltrado)[cite: 11]
    │   └── vector_store.py            # Gestión e interfaz de la base de datos vectorial (ChromaDB)[cite: 11]
    ├── tests/                         # Suite de pruebas automatizadas (pytest)
    │   ├── conftest.py                # Fixtures globales y configuración de pytest
    │   ├── test_agente.py             # Pruebas generales del agente
    │   ├── test_api_metadata.py       # Extracción y fallback de metadatos pedagógicos
    │   ├── test_api_revise.py         # Flujos de corrección y nueva evidencia
    │   ├── test_error_propagation.py  # Suite de fallos HTTP y recuperación de estado
    │   ├── test_evaluation_endpoints.py # Tests de los endpoints de evaluación Data/IA
    │   ├── test_generation_formats.py # Generación atómica de quiz, flashcards, tldr y scripts
    │   ├── test_graph.py              # Pruebas del orquestador Map-Reduce de LangGraph
    │   ├── test_integration_niche.py  # Pruebas de inyección dinámica de dominios
    │   ├── test_nodes.py              # Validación aislada de nodos
    │   ├── test_rag.py                # Suite de pruebas base del RAG
    │   ├── test_retrieval_v2.py       # Pruebas del motor híbrido y ChromaDB
    │   └── test_state.py              # Pruebas de transición de AgentState y FormatState
    ├── agent_v1.py                    # Orquestador base e integrador de Gemini
    ├── api.py                         # Endpoints FastAPI y Contratos HTTP/Pydantic
    ├── chunks_v1.csv                  # Datos de particiones para pruebas y evaluación
    ├── Dockerfile                     # Configuración para despliegue en contenedores
    ├── errors.py                      # Tipificación y mapeo de excepciones/códigos HTTP
    ├── evaluator_contract.py          # Contratos de evaluación semántica V2 (Data/IA)
    ├── generar_lote.py                # Script utilitario para procesamiento por lotes
    ├── generated_schemas.py           # Esquemas Pydantic para los formatos (Flashcards, Quiz, etc.)
    ├── generated_schemas_propuesta.py # Propuestas y borradores de esquemas
    ├── graph.py                       # Grafos de LangGraph (Map-Reduce y Subgrafos de formato)
    ├── ground_truth_v1.csv            # Dataset de referencia (Ground Truth) para métricas RAG
    ├── nodes.py                       # Nodos individuales del grafo (Revisor, Redactor, etc.)
    ├── README.md                      # Documentación técnica del módulo
    └── requirements.txt               # Dependencias del entorno

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

1. Crea un archivo `.env` en la **raíz principal del proyecto**:
    
    ```env
    GEMINI_API_KEY="api_key_aqui"
    GEMINI_MODEL="gemini-3.5-flash-lite"
    GRAPH_MAX_CONCURRENCY=3
    ```

2. Instala las dependencias aisladas del módulo:
    
    ```bash
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r agentes/requirements.txt
    ```

3. Levanta el servidor usando Uvicorn:
    
    ```bash
    uvicorn agentes.api:app --reload --port 8001
    ```
    Accede a la interfaz interactiva (Swagger UI) en: http://127.0.0.1:8001/docs

El endpoint HTTP `/generate` itera por los formatos en serie: cada resultado es independiente, pero no se genera en paralelo. La extracción de metadatos y la generación de cada formato hacen sus propias búsquedas, todas filtradas por `document_id`.

## Contratos de Datos y API v1

### 1. Integración Backend (POST `/api/v1/generate`)
Endpoint de generación orquestado por LangGraph. Genera `learning_metadata` a nivel raíz y la generación concurrente en `results`. Respeta los códigos `404`, `429`, `503` para fallos totales, y `207` para resultados mixtos.

### 2. Revisión Continua (POST `/api/v1/revise`)
Recibe feedback desde el evaluador de Data/IA e invoca el subgrafo. Si se detectan afirmaciones sin contexto, el grafo va a ChromaDB por nueva evidencia automáticamente.

### 3. Evaluación Data/IA (Contrato V2.0)
Endpoints de evaluación (`/evaluate/retrieval` y `/evaluate/retrieval/batch`) para testear el performance del híbrido RAG.

Las pruebas relevantes se distribuyen por componente: `test_rag.py` cubre primitivas RAG; `test_retrieval_v2.py` y `test_evaluation_endpoints.py` cubren retrieval y sus rutas; `test_api_metadata.py`, `test_generation_formats.py` y `test_error_propagation.py` cubren la API de aplicación; `test_graph.py`, `test_nodes.py` y `test_state.py` cubren el grafo interno y sus contratos; `test_agente.py` integra el agente con el corpus de evaluación.

## Pendientes técnicos identificados

El módulo cuenta con una suite que valida el comportamiento end-to-end del grafo, inyección de nichos y propagación correcta de los códigos HTTP ante caídas de red o cuota.

- **Conectar el grafo a la generación HTTP, si ese es el flujo objetivo.** Actualmente `/api/v1/generate` usa el flujo directo de `AgentV1`; no invoca `compilar_grafo_generacion`. Por eso el endpoint vuelve a recuperar contexto por cada formato y los procesa secuencialmente.
- **Integrar la evaluación semántica y la corrección automática.** `traducir_respuesta_evaluador` valida y traduce una respuesta V2 recibida, y el subgrafo puede consumir `feedback` inyectado; el código de agentes no solicita la evaluación ni encadena evaluador y redactor automáticamente.
- **Definir e implementar la ruta HTTP de revisión, si se requiere.** No existe actualmente un endpoint `/revise` en `api.py`; el subgrafo de formato es una función interna y no está expuesto como endpoint.
- **Conectar el router de revisión al subgrafo, si se requiere reintentar automáticamente.** Aunque `nodes.py` define `ruta_tras_redactor` y lógica para reescrituras, `compilar_subgrafo_formato` compila el recorrido lineal `redactor -> finalizar`; no usa ese router.
