from .cleaner import clean_text
from .extractor import extract_document
from .chunker import create_chunks
from .chunks_loader import load_chunks_from_csv


def ingest_file(path: str, vector_store) -> dict:
    """
    Pipeline para documentos NUEVOS, fuera del corpus congelado de
    Ground Truth v1. No usar para reproducir chunks_v1.csv.
    """

    documents = extract_document(path)

    for document in documents:
        document.text = clean_text(document.text)

    chunks = create_chunks(documents)

    vector_store.add_chunks(chunks)

    return {"documents": len(documents), "chunks": len(chunks)}


def ingest_ground_truth_v1(csv_path: str, vector_store) -> dict:
    """
    Carga el corpus congelado de Retrieval v1 directamente desde
    chunks_v1.csv (acordado con Data/IA), sin extractor/cleaner/chunker,
    para preservar exactamente chunk_id, document_id y límites de texto.
    """

    chunks = load_chunks_from_csv(csv_path)
    vector_store.add_chunks(chunks)

    return {"chunks": len(chunks)}