from .cleaner import clean_text
from .extractor import extract_document
from .chunker import create_chunks


def ingest_file(
    path: str,
    vector_store
) -> dict:

    documents = extract_document(
        path
    )

    for document in documents:
        document.text = clean_text(
            document.text
        )

    chunks = create_chunks(
        documents
    )

    vector_store.add_chunks(
        chunks
    )

    return {
        "documents": len(documents),
        "chunks": len(chunks)
    }