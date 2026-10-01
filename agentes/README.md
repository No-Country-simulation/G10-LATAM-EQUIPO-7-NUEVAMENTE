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