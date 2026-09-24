# NuevaMente - Agentes: Agent V1 + RAG Core

Módulo de ingestión, recuperación de conocimiento y contrato de
retrieval v1.0 para el hackathon **NuevaMente** (G10-LATAM-EQUIPO-7).

## Estructura real

```text
agentes/
├── agent_v1.py
├── requirements.txt
├── rag/
│   ├── config.py         # configuración centralizada (chunk_size, top_k, modelo, rutas)
│   ├── models.py         # Document, Chunk, SearchResult
│   ├── cleaner.py         # limpieza conservadora (no toca indentación)
│   ├── extractor.py       # extrae .pdf/.md/.txt para documentos NUEVOS
│   ├── chunker.py         # chunking para documentos NUEVOS (900/150)
│   ├── chunks_loader.py   # carga chunks_v1.csv tal cual (Ground Truth v1)
│   ├── embeddings.py      # MultilingualEmbedding (sentence-transformers)
│   ├── vector_store.py    # VectorStore (ChromaDB, espacio coseno explícito)
│   ├── retriever.py       # RetrieverService: retrieve() y retrieve_for_evaluation()
│   └── contract.py        # builders del contrato de retrieval v1.0
└── tests/
    └── test_rag.py
```

No existen `agent/agent_v1.py` ni `api/files.py` — esas rutas quedaron
del README original y no corresponden a la estructura real.

## Dos formas de cargar el Vector Store

**1. Corpus congelado de Ground Truth v1 (`chunks_v1.csv`)** — usar
siempre que se necesite evaluar contra el Ground Truth de Data/IA:

```python
from agentes.rag.vector_store import VectorStore
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.pipeline import ingest_ground_truth_v1

vector_store = VectorStore(
    path="./chroma_db",
    collection_name="nuevamente_v1",
    embedding_service=MultilingualEmbedding()
)

ingest_ground_truth_v1("./Data_IA/data/evaluation/chunks_v1.csv", vector_store)
```

Esto preserva exactamente `chunk_id`, `document_id`, texto y límites
de cada chunk tal como los definió Data/IA. **No pasa por
extractor/cleaner/chunker.**

**2. Documentos nuevos**, fuera del corpus congelado (para v2 o
contenido adicional):

```python
from agentes.rag.pipeline import ingest_file

ingest_file("manual.pdf", vector_store)
```

## Uso del Agente y el contrato de retrieval v1.0

```python
from agentes.agent_v1 import AgentV1

agent = AgentV1(vector_store)

# Uso normal (dentro del propio agente)
results = agent.answer(query="¿Qué es Kubernetes?", top_k=5)

# Para evaluación con Data/IA (Recall@k, Precision@k)
response = agent.answer_for_evaluation(
    case_id="CLD-ES-001-Q01",
    query="¿Qué es Kubernetes?",
    top_k=5
)
```

`answer_for_evaluation` devuelve el contrato acordado:

```json
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
```

Si no hay resultados: `status: "no_results"`, `results: []`.
Si falla la búsqueda vectorial: `status: "error"` con `error.code` /
`error.message`. `case_id` es obligatorio — no tiene valor por
defecto, para evitar IDs duplicados en las corridas de evaluación.

## Instalación y pruebas

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest agentes/tests/
```

## Pendiente / próximos pasos

- **Integración con Backend**: falta adaptar la ingestión para
  recibir el documento y su `document_id` desde Backend (quien lo
  recupera de OCI Object Storage), y habilitar retrieval filtrado
  por `document_id`.
- Confirmar con Data/IA si, además de `chunks_v1.csv`, habrá un
  `chunks_v2.csv` cuando se agreguen documentos nuevos fuera del
  corpus congelado.