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
                name=collection_name,
                # FIX: sin esto, Chroma usa L2 por defecto y
                # "score = 1 - distance" deja de ser una similitud
                # coseno real. El contrato con Data/IA declara
                # score_type: "cosine_similarity", así que el espacio
                # de la colección tiene que ser coseno explícitamente.
                metadata={"hnsw:space": "cosine"}
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
                    # Con hnsw:space="cosine", distance = 1 - cos_sim,
                    # así que esto sí es cosine_similarity real.
                    score=1 - distance,
                    metadata=(
                        results["metadatas"][0][i]
                    )
                )
            )

        return output