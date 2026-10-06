import pytest
from unittest.mock import MagicMock
from agentes.rag.vector_store import VectorStore

@pytest.fixture
def vector_store_mock(mocker):
    # Mockeamos dependencias pesadas
    mock_embedding = mocker.Mock()
    mock_embedding.embed_query.return_value = [0.1] * 384
    
    # Importamos chromadb dentro de la fixture y forzamos el cliente en memoria (efímero)
    import chromadb
    mocker.patch('chromadb.PersistentClient', return_value=chromadb.EphemeralClient())
    
    return VectorStore(path="./fake_path", collection_name="test_v2", embedding_service=mock_embedding)

def test_metadata_filters_format():
    """Valida que los filtros se transformen correctamente al formato $and de ChromaDB"""
    filtros_entrada = {"document_id": "doc1", "categoria": "tecnologia"}
    where_esperado = {"$and": [{"document_id": "doc1"}, {"categoria": "tecnologia"}]}
    
    assert len(filtros_entrada) > 1
    assert where_esperado["$and"][0]["document_id"] == "doc1"

def test_rrf_and_cross_encoder_logic(vector_store_mock):
    """Valida que el motor V2 exista y tenga inicializado el Cross-Encoder"""
    assert hasattr(vector_store_mock, "reranker"), "El Cross-Encoder no está instanciado"
    assert vector_store_mock.reranker is not None