# NuevaMente - Agentes: Agent V1 + RAG Core

Módulo central de ingestión, recuperación de conocimiento (RAG) y orquestación de agentes para el hackathon NuevaMente (G10-LATAM-EQUIPO-7).

## Novedades: Sprint 2 (Integración)

Durante esta fase, el módulo evolucionó para garantizar una conexión robusta con el ecosistema del proyecto:

* **Contratos Estructurados:** Estandarización estricta de las entradas y salidas en `api.py` y `agent_v1.py` para asegurar la interoperabilidad con Backend y Frontend.
* **Procesamiento de Chunks Completos:** Optimización en la orquestación y paso de contexto hacia el LLM.
* **Estabilización del Entorno:** Limpieza profunda de dependencias y aislamiento del módulo para evitar conflictos con la arquitectura de Data/IA.

---

## Estructura del Módulo

```text
agentes/
├── agent_v1.py            # Orquestador principal y ensamblaje de prompts
├── api.py                 # Endpoints FastAPI con los contratos del Sprint 2
├── requirements.txt
├── rag/
│   ├── config.py          # Configuración centralizada (chunk_size, top_k, modelo, rutas)
│   ├── models.py          # Document, Chunk, SearchResult
│   ├── cleaner.py         # Limpieza conservadora (no altera indentación)
│   ├── extractor.py       # Extracción de formato .pdf/.md/.txt para documentos nuevos
│   ├── chunker.py         # Segmentación para documentos nuevos (900/150)
│   ├── chunks_loader.py   # Carga directa de chunks_v1.csv (Ground Truth v1)
│   ├── embeddings.py      # MultilingualEmbedding (sentence-transformers)
│   ├── vector_store.py    # VectorStore (ChromaDB, espacio coseno explícito)
│   ├── retriever.py       # RetrieverService: retrieve() y retrieve_for_evaluation()
│   └── contract.py        # Builders del contrato de retrieval v1.0
└── tests/
    └── test_rag.py

   Modos de Carga del Vector Store
1. Corpus congelado de Ground Truth v1 (chunks_v1.csv)
Uso exclusivo para evaluación contra el Ground Truth de Data/IA:

from agentes.rag.vector_store import VectorStore
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.pipeline import ingest_ground_truth_v1

vector_store = VectorStore(
    path="./chroma_db",
    collection_name="nuevamente_v1",
    embedding_service=MultilingualEmbedding()
)

ingest_ground_truth_v1("./Data_IA/data/evaluation/chunks_v1.csv", vector_store)

Nota: Este método preserva exactamente chunk_id, document_id, texto y límites de cada chunk definidos por Data/IA. Omite los procesos de extractor/cleaner/chunker.

2. Documentos nuevos
Uso para contenido adicional fuera del corpus congelado:

Python
from agentes.rag.pipeline import ingest_file

ingest_file("manual.pdf", vector_store)
Uso del Agente y Contratos de Retrieval (v1.0)
Python
from agentes.agent_v1 import AgentV1

agent = AgentV1(vector_store)

# Ejecución estándar
results = agent.answer(query="¿Qué es Kubernetes?", top_k=5)

# Ejecución para evaluación con Data/IA (Recall@k, Precision@k)
response = agent.answer_for_evaluation(
    case_id="CLD-ES-001-Q01",
    query="¿Qué es Kubernetes?",
    top_k=5
)
El método answer_for_evaluation retorna el siguiente contrato estructurado:

{
  "contract_version": "1.0",
  "case_id": "CLD-ES-001-Q01",
  "query": "¿Qué es Kubernetes?",
  "top_k": 5,
  "score_type": "cosine_similarity",
  "status": "success",
  "results": [
    {
      "rank": 1,
      "chunk_id": "CLD-ES-001_CH_001",
      "document_id": "CLD-ES-001",
      "score": 0.91,
      "text": "Kubernetes es...",
      "metadata": {"categoria": "Cloud/DevOps", "titulo_documento": "..."}
    }
  ]
}

Manejo de excepciones: Si no hay resultados, retorna status: "no_results". En caso de fallo en la búsqueda, retorna status: "error" junto con error.code. El parámetro case_id es obligatorio para mantener la trazabilidad.


Endpoints de Integración (API)
El módulo expone una API local (puerto 8001) mediante FastAPI con los siguientes contratos para la integración con Backend:

POST /api/v1/index: Endpoint multipart/form-data. Recibe el archivo físico (file) y su document_id. Ejecuta el pipeline completo de extracción, limpieza, segmentación e indexación vectorial en ChromaDB.

POST /api/v1/generate: Endpoint de generación atómica. Recibe un JSON con document_id, formatos solicitados (quiz, flashcards), perfil y nivel de detalle. Aplica un proceso de retrieval filtrado estrictamente por documento.

Instalación y Pruebas
Bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest agentes/tests/



# Módulo de Agentes y Pipeline RAG - spring2

Este módulo implementa el núcleo de inteligencia artificial y recuperación de información (RAG) para el proyecto NuevaMente. Integra FastAPI, bases de datos vectoriales (ChromaDB) y el LLM Gemini 3.5 Flash, garantizando capacidad atómica y validación estricta de contratos de datos.

## Arquitectura y Endpoints

### 1. Ingesta e Indexación (`POST /api/v1/index`)
* **Descripción:** Recibe un documento binario mediante `multipart/form-data`, extrae su contenido (soporta PDF, TXT, MD), realiza el *chunking*, procesa embeddings multilingües y guarda los fragmentos en **ChromaDB** vinculados a un `document_id`.

### 2. Generación Atómica Adaptativa (`POST /api/v1/generate`)
* **Descripción:** Recupera los fragmentos más relevantes del RAG, ensambla un prompt dinámico adaptado al usuario (`profile`, `niche`, `detail_level`, `learning_objective`) y se conecta a **Gemini** para generar contenido.
* **Contratos Soportados:** `quiz` y `flashcards`.
* **Capacidad Atómica:** El sistema está protegido mediante bloques `try/except`. Si el modelo falla, no se encuentra la API Key, o la petición es inválida, se devuelve un estado `"status": "error"` controlado con su tipificación, asegurando que la ejecución del pipeline y el servidor nunca se rompan.

## Validación Pydantic Estricta (Contratos Data/IA)
Para asegurar la interoperabilidad con los equipos de Data y Frontend, la salida cruda de Gemini es interceptada y forzada a validarse contra modelos **Pydantic** (`QuizContent` y `FlashcardsContent`). Si la IA omite un campo o genera una estructura incorrecta, Pydantic bloquea la entrega y reporta el error, garantizando el estándar de **Cero Errores de Estructura**.

## Configuración y Despliegue Local

1. Crea un archivo `.env` en la **raíz principal del proyecto** (puedes guiarte con el `.env.example`):
   ```env
   GEMINI_API_KEY="api_key_aqui"
   GEMINI_MODEL="gemini-3.5-flash"
Instala las dependencias limpias del módulo:

Bash
pip install -r requirements.txt
Levanta el servidor usando Uvicorn:

Bash
uvicorn agentes.api:app --reload --port 8001
Accede a la interfaz interactiva (Swagger) en:
http://127.0.0.1:8001/docs


Contrato de Datos (API v1)
El endpoint /api/v1/generate cumple estrictamente con el contrato esperado por Backend #41 y Frontend #44.

Ejemplo de respuesta exitosa (status: "success"):

JSON
{
  "document_id": "doc_123",
  "results": [
    {
      "format": "quiz",
      "status": "success",
      "content": { ... JSON validado por Pydantic ... },
      "sources_used": [ { "rank": 1, "chunk_id": "...", "text": "..." } ],
      "error_message": null
    }
  ]
}


Ejemplo de respuesta fallida con capacidad atómica (status: "failed" o "no_results"):

JSON
{
  "document_id": "doc_123",
  "results": [
    {
      "format": "quiz",
      "status": "failed",
      "content": null,
      "sources_used": [],
      "error_message": "Error crítico en el pipeline o generación..."
    }
  ]
}


Ejecución de Pruebas Automatizadas
El módulo cuenta con 13 pruebas unitarias e integración que validan el Vector Store, el Chunking, la similitud coseno y la integridad del contrato Pydantic.

Bash
python -m pytest agentes/tests/