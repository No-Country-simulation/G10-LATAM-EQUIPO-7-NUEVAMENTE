"""Puerto explícito para inspeccionar y finalizar revisiones abandonadas.

No expone operaciones de generación ni invoca servicios externos.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StaleRevisionCandidate:
    """Identidad y último cambio de una revisión aún en processing."""

    format_id: str
    original_format_id: str
    document_id: str
    updated_at: datetime


class StaleRevisionRecoveryPort(Protocol):
    """Lecturas y actualización atómica de revisiones processing vencidas."""

    def find_stale(self, *, cutoff: datetime) -> tuple[StaleRevisionCandidate, ...]:
        """Consulta candidatos sin modificar la base de datos."""
        ...

    def fail_stale(
        self, *, cutoff: datetime, failed_at: datetime, error_message: str
    ) -> tuple[str, ...]:
        """Marca solo candidatos vigentes como failed y devuelve los IDs cambiados."""
        ...
