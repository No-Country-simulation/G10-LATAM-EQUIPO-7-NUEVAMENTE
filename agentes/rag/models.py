from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def document_id(self) -> str:
        """
        Punto 4 del review: document_id NUNCA se infiere del nombre
        de archivo. Debe fijarse explícitamente en metadata al crear
        el Chunk (ver chunks_loader.py). Si falta, es un bug de
        ingestión, no algo que debamos "adivinar" con un fallback.
        """
        document_id = self.metadata.get("document_id")

        if not document_id:
            raise ValueError(
                f"El chunk '{self.chunk_id}' no tiene document_id en su "
                "metadata. document_id debe fijarse explícitamente al "
                "crear el Chunk, nunca inferirse del nombre de archivo."
            )

        return document_id