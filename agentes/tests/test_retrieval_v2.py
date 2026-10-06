import pytest
from unittest.mock import patch
from agentes.rag.models import Chunk
from agentes.rag.vector_store import VectorStore
from agentes.rag.retriever import RetrieverService
import chromadb

# 1. Dependencias Falsas (Sin descargar modelos)
class FakeEmbedding:
    def embed_documents(self, texts): return [[0.1] * 384 for _ in texts]
    def embed_query(self, query): return [0.1] * 384

@pytest.fixture
def vector_store_mock():
    # Parcheamos ChromaDB para que viva en memoria y el Cross-Encoder para que no descargue el modelo
    with patch('chromadb.PersistentClient', return_value=chromadb.EphemeralClient()), \
         patch('agentes.rag.vector_store.CrossEncoder') as mock_ce:
        
        # Simulamos que el CrossEncoder devuelve puntuaciones predecibles (el texto más largo gana)
        mock_ce_instance = mock_ce.return_value
        mock_ce_instance.predict.side_effect = lambda pairs: [float(len(p[1])) for p in pairs]
        
        store = VectorStore(
            path="./fake", 
            collection_name="test_v2_real", 
            embedding_service=FakeEmbedding()
        )
        return store

# 2. Prueba 1: Flujo real de Filtros (Prefiltrado)
def test_real_metadata_filtering(vector_store_mock):
    """Valida que el prefiltrado excluya los chunks que no coinciden con los metadatos"""
    vector_store_mock.add_chunks([
        Chunk(id="chunk_1", text="Texto A", metadata={"document_id": "DOC1", "categoria": "tecnologia"}),
        Chunk(id="chunk_2", text="Texto B", metadata={"document_id": "DOC2", "categoria": "tecnologia"}),
        Chunk(id="chunk_3", text="Texto C", metadata={"document_id": "DOC1", "categoria": "finanzas"})
    ])
    
    # Usamos RetrieverService, que es el que gestiona los filtros según el contrato de Data/IA
    retriever = RetrieverService(vector_store_mock)
    response = retriever.retrieve_for_evaluation(
        case_id="test_filter",
        query="texto", 
        top_k=5, 
        metadata_filters={"document_id": "DOC1", "categoria": "tecnologia"}
    )
    
    assert response["status"] == "success"
    assert len(response["results"]) == 1
    assert response["results"][0]["chunk_id"] == "chunk_1"

# 3. Prueba 2: Comportamiento real de Reranking
def test_real_cross_encoder_reranking(vector_store_mock):
    """Valida que el modelo CrossEncoder reordena los candidatos iniciales basándose en su score"""
    vector_store_mock.add_chunks([
        Chunk(id="corto", text="Corto", metadata={"document_id": "DOC1"}),
        Chunk(id="muy_largo", text="Este es un texto mucho mas largo", metadata={"document_id": "DOC1"}),
    ])
    
    # Búsqueda base sin filtros
    resultados = vector_store_mock.search(query="texto", top_k=2)
    
    assert resultados[0].chunk_id == "muy_largo"
    assert resultados[0].score > resultados[1].score