from sentence_transformers import SentenceTransformer

from .config import CONFIG


class MultilingualEmbedding:

    def __init__(self, model_name: str = CONFIG.embedding_model_name):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        embedding = self.model.encode(query, normalize_embeddings=True)
        return embedding.tolist()