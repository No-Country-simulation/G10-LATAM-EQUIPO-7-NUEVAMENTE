# NuevaMente - Agentes: Agent V1 + RAG Core (Retrieval V2)

Módulo central de ingestión, recuperación de conocimiento (RAG) y orquestación de agentes para el hackathon NuevaMente (G10-LATAM-EQUIPO-7). Integra FastAPI, bases de datos vectoriales (ChromaDB) y los modelos de la familia Gemini mediante el SDK oficial (`google-genai`).

## Novedades: Sprint 3 (Retrieval V2 y Nuevos Formatos)

Durante esta fase, la arquitectura evolucionó para garantizar resultados precisos y mayor resiliencia E2E:

* **Retrieval V2 (Búsqueda Híbrida + Reranking):** Implementación de búsqueda semántica (ChromaDB) combinada con búsqueda lexical (BM25), fusionadas mediante *Reciprocal Rank Fusion* (RRF) y reordenadas con un modelo Cross-Encoder.
* **Contratos V2.0 (Metadata a nivel raíz):** Actualización del contrato de Data/IA y orquestación con Backend, extrayendo metadatos pedagógicos (`key_concepts`, `prerequisites`, `estimated_time_minutes`) en una llamada independiente para unificarlos a nivel raíz del JSON.
* **Inyección Dinámica de Nicho (Contextualización Temática):** El parámetro `niche` del payload se inyecta directamente en la capa de extracción de metadatos, obligando al LLM a pivotar y adaptar los conceptos clave y prerrequisitos estrictamente al dominio solicitado por el usuario (ej. *Ciberseguridad, Finanzas, Tecnología*), evitando respuestas genéricas.
* **Capacidad Atómica y Nuevos Formatos:** Generación paralela soportando `quiz`, `flashcards`, `tldr` y `video_script`. El sistema está protegido por bloques `try/except` con fallback seguro para metadatos.
* **Modelo Ligero de Baja Latencia:** Migración a `gemini-3.5-flash-lite` para mitigar cuellos de botella (Errores 503) y maximizar la velocidad de respuesta.

---

## Estructura del Módulo

    agentes/
    ├── agent_v1.py            # Orquestador principal (Llamada atómica a Metadatos y Formatos)
    ├── api.py                 # Endpoints FastAPI y Contratos Estructurales (Pydantic)
    ├── requirements.txt
    ├── rag/
    │   ├── config.py          # Configuración centralizada (chunk_size, top_k, modelo)
    │   ├── models.py          # Document, Chunk, SearchResult
    │   ├── cleaner.py         # Limpieza conservadora (Filtros Regex para PDFs)
    │   ├── extractor.py       # Extracción de formato .pdf/.md/.txt
    │   ├── chunker.py         # Segmentación para documentos nuevos
    │   ├── embeddings.py      # MultilingualEmbedding (sentence-transformers)
    │   ├── vector_store.py    # VectorStore (ChromaDB + BM25 + CrossEncoder)
    │   ├── retriever.py       # RetrieverService: Gestión de flujos y prefiltrado
    │   └── contract.py        # Builders del contrato de evaluación v2.0
    └── tests/
        ├── test_rag.py        # Suite de pruebas base
        └── test_retrieval_v2.py # Pruebas del motor híbrido con EphemeralClient

---

## Configuración y Despliegue Local

1. Crea un archivo `.env` en la **raíz principal del proyecto**:
    
    GEMINI_API_KEY="api_key_aqui"
    GEMINI_MODEL="gemini-3.5-flash-lite"

2. Instala las dependencias aisladas del módulo:
    
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r agentes/requirements.txt

3. Levanta el servidor usando Uvicorn:
    
    uvicorn agentes.api:app --reload --port 8001
    
    Accede a la interfaz interactiva (Swagger UI) en: http://127.0.0.1:8001/docs

---

## Modos de Carga del Vector Store

### 1. Corpus congelado de Ground Truth (Benchmark)
Uso exclusivo para evaluación de métricas de Data/IA. Preserva exactamente `chunk_id`, texto y límites.

    from agentes.rag.vector_store import VectorStore
    from agentes.rag.embeddings import MultilingualEmbedding
    from agentes.rag.pipeline import ingest_ground_truth_v1

    vector_store = VectorStore(path="./chroma_db", collection_name="benchmark_v2", embedding_service=MultilingualEmbedding())
    ingest_ground_truth_v1("./Data_IA/data/evaluation/chunks_v1.csv", vector_store)

### 2. Documentos nuevos (API)
Uso para contenido dinámico de la plataforma:

    from agentes.rag.pipeline import ingest_file
    ingest_file("manual.pdf", vector_store)

---

## Contratos de Datos y API v1

### 1. Evaluación Data/IA (Contrato V2.0)
El método `answer_for_evaluation()` permite evaluar Recall@K y Precision@K aplicando filtros de metadatos.

    response = agent.answer_for_evaluation(
        case_id="CLD-ES-001-Q01",
        query="¿Qué es Kubernetes?",
        top_k=5,
        metadata_filters={"document_id": "doc_123"}
    )

### 2. Integración Backend (POST /api/v1/generate)
Endpoint de generación. Recibe un JSON con `document_id`, `niche` y los formatos solicitados. Retorna `learning_metadata` a nivel raíz y la generación en `results`.

Ejemplo de respuesta exitosa (status: "success"):

    {
      "document_id": "doc_123",
      "learning_metadata": {
        "key_concepts": ["Concepto 1", "Concepto 2", "Concepto 3"],
        "prerequisites": ["Conocimiento previo fundamental"],
        "estimated_time_minutes": 15
      },
      "results": [
        {
          "format": "quiz",
          "status": "success",
          "content": { "title": "...", "instructions": "...", "questions": [...] },
          "sources_used": [ { "rank": 1, "chunk_id": "...", "score": 4.12, "text": "..." } ],
          "error_message": null
        },
        {
          "format": "flashcards",
          "status": "success",
          "content": { "title": "...", "instructions": "...", "cards": [...] },
          "sources_used": [ { "rank": 1, "chunk_id": "...", "score": 3.84, "text": "..." } ],
          "error_message": null
        }
      ]
    }

---

## Ejecución de Pruebas Automatizadas (QA)

El módulo cuenta con una suite completa de pruebas unitarias y de integración que validan el Vector Store, el filtrado real de metadatos, el reranking, la inyección de nichos y la integridad de los contratos Pydantic.

    python -m pytest agentes/tests/