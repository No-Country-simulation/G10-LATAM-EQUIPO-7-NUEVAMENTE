"""Enumeraciones utilizadas por el dominio de NuevaMente."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Estados posibles durante el ciclo de vida de un documento."""

    RECEIVED = "received"
    VALIDATED = "validated"
    STORING = "storing"
    STORED = "stored"
    INDEXING = "indexing"
    INDEXED = "indexed"

    VALIDATION_FAILED = "validation_failed"
    STORAGE_FAILED = "storage_failed"
    INDEXING_FAILED = "indexing_failed"


class ProcessStatus(StrEnum):
    """Estados generales de un proceso de adaptación."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"