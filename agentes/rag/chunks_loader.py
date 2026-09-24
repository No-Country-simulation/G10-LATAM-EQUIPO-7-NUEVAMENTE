"""
Carga del corpus congelado de Ground Truth v1.

Punto 3 del review de Tara: para que chunk_id, document_id, texto y
límites de cada chunk coincidan EXACTAMENTE con chunks_v1.csv, no
podemos re-generarlos con RecursiveCharacterTextSplitter (900/150).
Los cargamos tal cual, sin pasar por cleaner ni chunker.
"""

import csv
from pathlib import Path

from .models import Chunk

REQUIRED_COLUMNS = {"chunk_id", "document_id", "chunk_text"}


def load_chunks_from_csv(csv_path: str) -> list[Chunk]:

    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró chunks_v1.csv en: {csv_path}"
        )

    chunks = []

    # utf-8-sig: el CSV real trae BOM al inicio.
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"chunks_v1.csv no tiene las columnas requeridas: {missing}"
            )

        for row in reader:
            metadata = {
                "document_id": row["document_id"],
                "categoria": row.get("categoria", ""),
                "titulo_documento": row.get("titulo_documento", ""),
                "chunk_index": row.get("chunk_index", ""),
            }

            chunks.append(
                Chunk(
                    id=row["chunk_id"],
                    text=row["chunk_text"],
                    metadata=metadata
                )
            )

    return chunks