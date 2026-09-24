"""Entidad de dominio que representa un proceso de NuevaMente."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.enums import ProcessStatus


@dataclass(slots=True)
class Process:
    """Proceso asociado a la transformación de un documento.

    El modelo se mantiene deliberadamente reducido mientras se define
    el contrato definitivo con los módulos de RAG y Agentes.

    Attributes:
        process_id: Identificador único del proceso.
        document_id: Documento sobre el cual se ejecuta el proceso.
        status: Estado actual.
        error_message: Descripción del error cuando el proceso falla.
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
        completed_at: Fecha de finalización, cuando aplique.
    """

    process_id: str
    document_id: str

    status: ProcessStatus = ProcessStatus.PENDING
    error_message: str | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida los identificadores mínimos del proceso."""
        if not self.process_id.strip():
            raise ValueError("process_id no puede estar vacío.")

        if not self.document_id.strip():
            raise ValueError("document_id no puede estar vacío.")

    def mark_processing(self) -> None:
        """Marca el proceso como iniciado."""
        self.status = ProcessStatus.PROCESSING
        self.updated_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        """Marca el proceso como completado."""
        now = datetime.now(UTC)

        self.status = ProcessStatus.COMPLETED
        self.updated_at = now
        self.completed_at = now
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """Marca el proceso como fallido y registra su causa."""
        if not error_message.strip():
            raise ValueError("error_message no puede estar vacío.")

        now = datetime.now(UTC)

        self.status = ProcessStatus.FAILED
        self.error_message = error_message
        self.updated_at = now
        self.completed_at = now