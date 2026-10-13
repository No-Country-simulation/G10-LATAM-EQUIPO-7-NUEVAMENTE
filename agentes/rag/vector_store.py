import chromadb
from rank_bm25 import BM25Okapi
import re
from sentence_transformers import CrossEncoder

from .models import Chunk, SearchResult
from .config import CONFIG

class VectorStore:

    def __init__(
        self,
        path: str = CONFIG.vector_store_path,
        collection_name: str = CONFIG.collection_name,
        embedding_service=None
    ):
        self.embedding_service = embedding_service
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Instanciamos un modelo Cross-Encoder ligero y rápido para el reranking
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)

    def add_chunks(self, chunks: list[Chunk]):
        if not chunks:
            return

        texts = [chunk.text for chunk in chunks]
        ids = [chunk.id for chunk in chunks]
        metadata = [chunk.metadata for chunk in chunks]

        embeddings = self.embedding_service.embed_documents(texts)

        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadata,
            embeddings=embeddings
        )

    def search(self, query: str, top_k: int = CONFIG.top_k_default, filters: dict = None) -> list[SearchResult]:
        embedding = self.embedding_service.embed_query(query)
        
        # Ampliamos la red inicial para tener buenos candidatos antes de filtrar con el Cross-Encoder
        candidate_k = top_k * 3

        # ==========================================
        # FASE 1: Contextualización (Filtros metadata)
        # ==========================================
        where_clause = None
        if filters:
            if len(filters) == 1:
                where_clause = filters
            else:
                where_clause = {"$and": [{k: v} for k, v in filters.items()]}

        # ==========================================
        # FASE 2: Retrieval Híbrido (Vectorial + Lexical)
        # ==========================================
        
        # 1. Búsqueda Vectorial
        vector_data = self.collection.query(
            query_embeddings=[embedding],
            n_results=candidate_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        # 2. Búsqueda Lexical (BM25)
        all_filtered_data = self.collection.get(
            where=where_clause,
            include=["documents", "metadatas"]
        )

        bm25_results = []
        if all_filtered_data and all_filtered_data["documents"]:
            tokenized_corpus = [re.findall(r'\w+', doc.lower()) for doc in all_filtered_data["documents"]]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = re.findall(r'\w+', query.lower())
            
            doc_scores = bm25.get_scores(tokenized_query)
            top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:candidate_k]
            
            for i in top_indices:
                if doc_scores[i] > 0:
                    bm25_results.append({
                        "chunk_id": all_filtered_data["ids"][i],
                        "text": all_filtered_data["documents"][i],
                        "metadata": all_filtered_data["metadatas"][i]
                    })

        # 3. Fusión RRF (Reciprocal Rank Fusion)
        rrf_scores = {}
        k_rrf = 60

        if vector_data and vector_data["ids"] and vector_data["ids"][0]:
            for rank, chunk_id in enumerate(vector_data["ids"][0]):
                if chunk_id not in rrf_scores:
                    rrf_scores[chunk_id] = {
                        "rrf_score": 0,
                        "text": vector_data["documents"][0][rank],
                        "metadata": vector_data["metadatas"][0][rank]
                    }
                rrf_scores[chunk_id]["rrf_score"] += 1.0 / (k_rrf + rank + 1)

        for rank, res in enumerate(bm25_results):
            chunk_id = res["chunk_id"]
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {
                    "rrf_score": 0,
                    "text": res["text"],
                    "metadata": res["metadata"]
                }
            rrf_scores[chunk_id]["rrf_score"] += 1.0 / (k_rrf + rank + 1)

        # Obtenemos los mejores candidatos híbridos
        hybrid_candidates = sorted(rrf_scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True)[:candidate_k]

        if not hybrid_candidates:
            return []

        # ==========================================
        # FASE 3: Reranking con Cross-Encoder
        # ==========================================
        
        # Preparamos los pares [pregunta, texto_del_chunk] para el modelo
        cross_inp = [[query, data["text"]] for _, data in hybrid_candidates]
        
        # El Cross-Encoder predice la relevancia real (logits) de cada par
        cross_scores = self.reranker.predict(cross_inp)

        # Emparejamos los scores con los candidatos y reordenamos
        for idx, (chunk_id, data) in enumerate(hybrid_candidates):
            data["cross_score"] = float(cross_scores[idx])

        # Orden final absoluto basado en el Cross-Encoder, limitando al top_k solicitado
        final_reranked = sorted(hybrid_candidates, key=lambda x: x[1]["cross_score"], reverse=True)[:top_k]

        output = []
        for chunk_id, data in final_reranked:
            output.append(
                SearchResult(
                    chunk_id=chunk_id,
                    text=data["text"],
                    score=data["cross_score"], # Enviamos el score del reranker para evaluación
                    metadata=data["metadata"]
                )
            )

        return output