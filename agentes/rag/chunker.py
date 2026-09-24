from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

from .models import Document, Chunk
from .config import CONFIG


def create_chunks(
    documents: list[Document],
    chunk_size: int = CONFIG.chunk_size,
    chunk_overlap: int = CONFIG.chunk_overlap
) -> list[Chunk]:
    """
    Chunker para documentos NUEVOS, fuera del corpus congelado de
    Ground Truth v1. NUNCA usar esto para reproducir chunks_v1.csv:
    para eso está chunks_loader.load_chunks_from_csv, que carga los
    chunks ya congelados tal cual, sin volver a partirlos.
    """

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap debe ser menor que chunk_size"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""]
    )

    chunks = []

    for document in documents:

        pieces = splitter.split_text(document.text)

        for index, text in enumerate(pieces):

            metadata = dict(document.metadata)
            metadata["chunk_index"] = index

            chunks.append(
                Chunk(
                    id=f"{metadata['source']}_{metadata.get('page', 1)}_{index}",
                    text=text,
                    metadata=metadata
                )
            )

    return chunks