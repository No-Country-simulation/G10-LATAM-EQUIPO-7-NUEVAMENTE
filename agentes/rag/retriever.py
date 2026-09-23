import chromadb
from .models import Chunk, SearchResult


class VectorStore:

    def __init__(
        self,
        path: str,
        collection_name: str,
        embedding_service
    ):

        self.embedding_service = (
            embedding_service
        )

        self.client = (
            chromadb.PersistentClient(
                path=path
            )
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name
            )
        )

    def add_chunks(
        self,
        chunks: list[Chunk]
    ):

        if not chunks:
            return

        texts = [
            chunk.text
            for chunk in chunks
        ]

        ids = [
            chunk.id
            for chunk in chunks
        ]

        metadata = [
            chunk.metadata
            for chunk in chunks
        ]

        embeddings = (
            self.embedding_service
            .embed_documents(texts)
        )

        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadata,
            embeddings=embeddings
        )

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> list[SearchResult]:

        embedding = (
            self.embedding_service
            .embed_query(query)
        )

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances"
            ]
        )

        output = []

        for i, chunk_id in enumerate(
            results["ids"][0]
        ):

            distance = (
                results["distances"][0][i]
            )

            output.append(
                SearchResult(
                    chunk_id=chunk_id,
                    text=(
                        results["documents"][0][i]
                    ),
                    score=1 - distance,
                    metadata=(
                        results["metadatas"][0][i]
                    )
                )
            )

        return output


class RetrieverService:
    """
    Servicio de recuperación que implementa el contrato de JSON acordado 
    con el equipo de Data/IA para el cálculo de métricas (Recall@3, Precision, etc.).
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def retrieve(self, query: str, case_id: str, top_k: int = 5) -> dict:
        """
        Servicio de recuperación actualizado: case_id ya no tiene valor por defecto
        para evitar duplicidades y obligar a enviarlo desde las pruebas.
        """
        try:
            raw_results = self.vector_store.search(query=query, top_k=top_k)
            
            if not raw_results:
                return {
                    "contract_version": "1.0",
                    "case_id": case_id,
                    "query": query,
                    "top_k": top_k,
                    "score_type": "cosine_similarity",
                    "status": "no_results",
                    "results": [],
                    "error": None
                }

            formatted_results = []
            for rank, res in enumerate(raw_results, start=1):
                # Aseguramos que use el ID canónico que viene en los metadatos
                doc_id = res.metadata.get("document_id", res.metadata.get("source", "unknown"))
                
                formatted_results.append({
                    "rank": rank,
                    "chunk_id": res.chunk_id, # Asegúrate que este ID coincida con el formato de su CSV
                    "document_id": doc_id,
                    "score": round(res.score, 4),
                    "text": res.text,
                    "metadata": res.metadata
                })

            return {
                "contract_version": "1.0",
                "case_id": case_id, # <--- Obligatorio aquí también
                "query": query,
                "top_k": top_k,
                "score_type": "cosine_similarity",
                "status": "success",
                "results": formatted_results,
                "error": None
            }

        except Exception as e:
            return {
                "contract_version": "1.0",
                "case_id": case_id,
                "query": query,
                "top_k": top_k,
                "score_type": "cosine_similarity",
                "status": "error",
                "results": [],
                "error": {
                    "code": "RETRIEVAL_FAILED",
                    "message": str(e)
                }
            }