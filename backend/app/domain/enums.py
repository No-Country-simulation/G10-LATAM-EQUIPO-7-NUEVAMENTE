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


class GeneratedFormatType(StrEnum):
    """Formatos pedagógicos soportados durante Sprint 2."""

    QUIZ = "quiz"
    FLASHCARDS = "flashcards"


class GeneratedFormatStatus(StrEnum):
    """Estados posibles de una generación solicitada a Agentes."""

    SUCCESS = "success"
    FAILED = "failed"
    NO_RESULTS = "no_results"


class DocumentFormatsStatus(StrEnum):
    """Estado agregado de los formatos expuesto a Frontend."""

    PROCESSING = "processing"
    READY = "ready"
    PARTIAL = "partial"
    ERROR = "error"


class FormatEvaluationStatus(StrEnum):
    """Resultados globales emitidos por Data/IA."""

    APPROVED = "aprobado"
    REQUIRES_REVIEW = "requiere_revision"
    REJECTED = "rechazado"