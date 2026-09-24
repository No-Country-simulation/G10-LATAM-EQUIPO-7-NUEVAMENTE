import pytest

from agentes.rag.models import Chunk, SearchResult
from agentes.rag.cleaner import clean_text
from agentes.rag.chunks_loader import load_chunks_from_csv
from agentes.rag.vector_store import VectorStore
from agentes.rag.retriever import RetrieverService
from agentes.rag.contract import build_no_results_response, build_error_response


class FakeEmbeddingService:
    """Embeddings deterministas para pruebas, sin descargar el modelo real."""

    VOCAB = {
        "kubernetes": [1.0, 0.0, 0.0],
        "docker": [0.0, 1.0, 0.0],
    }

    def _vector_for(self, text: str) -> list[float]:
        text = text.lower()
        for word, vector in self.VOCAB.items():
            if word in text:
                return vector
        return [0.1, 0.1, 0.1]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._vector_for(query)


@pytest.fixture
def vector_store(tmp_path):
    store = VectorStore(
        path=str(tmp_path / "chroma"),
        collection_name="test_collection",
        embedding_service=FakeEmbeddingService(),
    )
    store.add_chunks([
        Chunk(
            id="doc1_CH_001",
            text="Kubernetes es un orquestador de contenedores.",
            metadata={"document_id": "doc1"}
        ),
        Chunk(
            id="doc2_CH_001",
            text="Docker permite empaquetar aplicaciones.",
            metadata={"document_id": "doc2"}
        ),
    ])
    return store


@pytest.fixture
def empty_vector_store(tmp_path):
    return VectorStore(
        path=str(tmp_path / "chroma_empty"),
        collection_name="empty_collection",
        embedding_service=FakeEmbeddingService(),
    )


# --- Vector Store y similitud coseno ---

def test_vector_store_uses_cosine_space(vector_store):
    assert vector_store.collection.metadata.get("hnsw:space") == "cosine"


def test_search_returns_best_match_first(vector_store):
    results = vector_store.search(query="¿Qué es Kubernetes?", top_k=2)
    assert results[0].chunk_id == "doc1_CH_001"
    assert results[0].score > results[1].score


# --- document_id canónico (punto 4) ---

def test_search_result_document_id_requires_metadata():
    result = SearchResult(chunk_id="x", text="y", score=0.5, metadata={})
    with pytest.raises(ValueError):
        _ = result.document_id


# --- Cleaner conservador (punto 9) ---

def test_cleaner_preserves_indentation():
    code = "def f():\n    return 1\n"
    assert clean_text(code) == code


# --- Validaciones de entrada (punto 8) ---

def test_retriever_rejects_empty_query(vector_store):
    retriever = RetrieverService(vector_store)
    with pytest.raises(ValueError):
        retriever.retrieve(query="   ")


def test_retriever_rejects_invalid_top_k(vector_store):
    retriever = RetrieverService(vector_store)
    with pytest.raises(ValueError):
        retriever.retrieve(query="kubernetes", top_k=0)


def test_retrieve_for_evaluation_requires_case_id(vector_store):
    retriever = RetrieverService(vector_store)
    with pytest.raises(ValueError):
        retriever.retrieve_for_evaluation(case_id="", query="kubernetes")


# --- Integración AgentV1 / RetrieverService y contrato success/no_results ---

def test_retrieve_for_evaluation_success_shape(vector_store):
    retriever = RetrieverService(vector_store)
    response = retriever.retrieve_for_evaluation(
        case_id="CASE-001", query="kubernetes", top_k=2
    )
    assert response["status"] == "success"
    assert response["contract_version"] == "1.0"
    assert response["results"][0]["rank"] == 1
    assert response["results"][0]["document_id"] == "doc1"


def test_retrieve_for_evaluation_no_results(empty_vector_store):
    retriever = RetrieverService(empty_vector_store)
    response = retriever.retrieve_for_evaluation(
        case_id="CASE-002", query="kubernetes", top_k=5
    )
    assert response["status"] == "no_results"
    assert response["results"] == []


def test_build_no_results_response_shape():
    response = build_no_results_response("CASE-003", "query", 5)
    assert response["status"] == "no_results"
    assert response["results"] == []


def test_build_error_response_shape():
    response = build_error_response(
        "CASE-004", "query", 5, "RETRIEVAL_FAILED", "boom"
    )
    assert response["status"] == "error"
    assert response["error"] == {"code": "RETRIEVAL_FAILED", "message": "boom"}


# --- Compatibilidad con chunks_v1.csv (punto 3) ---

def test_load_chunks_from_csv(tmp_path):
    csv_content = (
        "chunk_id,document_id,categoria,titulo_documento,chunk_index,"
        "char_count,chunk_text\n"
        "AI-ES-001_CH_001,AI-ES-001,IA,Titulo,1,10,\"Texto de prueba\"\n"
    )
    csv_path = tmp_path / "chunks_v1.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    chunks = load_chunks_from_csv(str(csv_path))

    assert len(chunks) == 1
    assert chunks[0].id == "AI-ES-001_CH_001"
    assert chunks[0].metadata["document_id"] == "AI-ES-001"
    assert chunks[0].text == "Texto de prueba"
    