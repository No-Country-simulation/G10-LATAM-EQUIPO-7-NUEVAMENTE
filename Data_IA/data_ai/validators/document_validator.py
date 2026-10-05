"""Validación de metadatos del documento recibido.

Importante:
Data/IA valida el contrato de entrada. La extracción, limpieza, chunking,
embeddings y Vector Store pertenecen al equipo de Agentes.
"""

from pathlib import Path


ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}


def validate_document_metadata(filename: str, size_bytes: int | None = None) -> None:
    """Valida datos mínimos del documento.

    Args:
        filename: Nombre del archivo recibido.
        size_bytes: Tamaño opcional del archivo en bytes.

    Raises:
        ValueError: Si faltan datos o el formato no es admitido.
    """
    if not filename or not filename.strip():
        raise ValueError("filename es obligatorio.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Formato no soportado: {extension}. "
            f"Permitidos: {sorted(ALLOWED_EXTENSIONS)}"
        )

    if size_bytes is not None and size_bytes <= 0:
        raise ValueError("El archivo debe tener un tamaño mayor que 0 bytes.")
