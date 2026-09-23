from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

from .models import Document, Chunk


def create_chunks(
    documents: list[Document],
    chunk_size: int = 900,
    chunk_overlap: int = 150
) -> list[Chunk]:

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap debe ser menor que chunk_size"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            " ",
            ""
        ]
    )

    chunks = []

    for document in documents:

        cleaned = splitter.split_text(
            document.text
        )

        for index, text in enumerate(
            cleaned
        ):

            metadata = dict(
                document.metadata
            )

            metadata["chunk_index"] = index

            chunks.append(
                Chunk(
                    id=(
                        f"{metadata['source']}"
                        f"_{metadata.get('page', 1)}"
                        f"_{index}"
                    ),
                    text=text,
                    metadata=metadata
                )
            )

    return chunks