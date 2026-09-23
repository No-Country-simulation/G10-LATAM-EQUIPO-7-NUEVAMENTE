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
        # NOTA: usa metadata["source"] como document_id por ahora.
        # Pendiente de confirmar contra chunks_v1.csv / Ground Truth v1
        # si el formato de documento_id debe ser distinto (ej. "CLD-ES-001"
        # en vez del nombre de archivo).
        return self.metadata.get("document_id", self.metadata.get("source", ""))