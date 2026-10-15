"""Caso de uso operacional para revisiones interrumpidas (sin reintentar LLM).

La decisión de intervenir es explícita y externa a la API de generación.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.ports.stale_revision_recovery_port import (
    StaleRevisionCandidate,
    StaleRevisionRecoveryPort,
)

_RECOVERY_REASON = (
    "Revisión interrumpida: el intento permaneció en processing más tiempo "
    "del permitido. Se conserva el original; no se ejecutó otro intento."
)


@dataclass(frozen=True, slots=True)
class StaleRevisionRecoveryReport:
    """Resultado auditable, tanto para vista previa como para ejecución."""

    applied: bool
    cutoff: datetime
    candidates: tuple[StaleRevisionCandidate, ...]
    recovered_ids: tuple[str, ...]


class StaleRevisionRecoveryService:
    """Detecta revisiones vencidas y opcionalmente las cierra en failed.

    No ejecuta Agentes ni Data/IA y nunca elimina el historial. La unicidad
    de revisión por original sigue en manos del índice SQLite existente.
    """

    def __init__(self, *, recovery_port: StaleRevisionRecoveryPort) -> None:
        self._recovery_port = recovery_port

    def execute(
        self,
        *,
        older_than_minutes: int = 60,
        apply: bool = False,
        now: datetime | None = None,
    ) -> StaleRevisionRecoveryReport:
        """Identifica y, si se autoriza, falla reservas processing antiguas.

        Args:
            older_than_minutes: Edad mínima desde updated_at, estrictamente positiva.
            apply: False realiza exclusivamente una vista previa.
            now: Reloj consciente de zona horaria, inyectable para pruebas.

        Raises:
            ValueError: Parámetros inválidos.
            GeneratedFormatRepositoryError: Fallo de lectura o escritura SQLite.
        """
        if isinstance(older_than_minutes, bool) or not isinstance(older_than_minutes, int):
            raise ValueError("older_than_minutes debe ser un entero positivo.")
        if older_than_minutes < 1:
            raise ValueError("older_than_minutes debe ser mayor o igual a 1.")
        if not isinstance(apply, bool):
            raise ValueError("apply debe ser booleano.")
        observed_at = now if now is not None else datetime.now(UTC)
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("now debe incluir zona horaria.")
        observed_at = observed_at.astimezone(UTC)
        cutoff = observed_at - timedelta(minutes=older_than_minutes)
        candidates = self._recovery_port.find_stale(cutoff=cutoff)
        recovered_ids: tuple[str, ...] = ()
        if apply:
            recovered_ids = self._recovery_port.fail_stale(
                cutoff=cutoff,
                failed_at=observed_at,
                error_message=_RECOVERY_REASON,
            )
        return StaleRevisionRecoveryReport(
            applied=apply,
            cutoff=cutoff,
            candidates=candidates,
            recovered_ids=recovered_ids,
        )
