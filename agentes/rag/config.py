"""
Configuración centralizada del módulo RAG (punto 7 del review).
Cambiar acá, no dentro de las clases, cuando haya que ajustar
chunk_size, modelo de embeddings, top_k, rutas, etc.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RagConfig:
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k_default: int = 5
    embedding_model_name: str = "paraphrase-multilingual-mpnet-base-v2"
    vector_store_path: str = "./chroma_db"
    collection_name: str = "nuevamente_v1"
    chunks_v1_csv_path: str = "./Data_IA/data/evaluation/chunks_v1.csv"


CONFIG = RagConfig()