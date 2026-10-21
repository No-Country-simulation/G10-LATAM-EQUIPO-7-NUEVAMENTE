"""Proyección de evaluaciones del ciclo correspondiente al contenido vigente.

Reutiliza FormatRevisionHistoryService para respetar raíces, revisiones y
regeneraciones. No consulta proveedores ni modifica la persistencia.
"""

from dataclasses import dataclass

from app.application.format_revision_history_service import (
    FormatRevisionHistoryService,
    RevisionHistoryInconsistentError,
)
from app.domain.enums import GeneratedFormatType
from app.domain.format_evaluation import FormatEvaluation
from app.domain.generated_format import GeneratedFormat


@dataclass(frozen=True, slots=True)
class CurrentCycleEvaluations:
    """Evaluación del contenido elegido e historial de su ciclo.

    Attributes:
        evaluation: Última evaluación de la versión elegida; nunca se hereda
            la nota de la versión raíz cuando se muestra una revisión distinta.
        evaluations: Evaluaciones de raíz y revisión del mismo ciclo, ordenadas
            de la más reciente a la más antigua.
    """

    evaluation: FormatEvaluation | None
    evaluations: tuple[FormatEvaluation, ...]


class CurrentCycleEvaluationsService:
    """Asocia los formatos actualmente mostrados con su propio ciclo.

    El último intento de regeneración puede fallar y el contenido vigente
    corresponder a un éxito histórico anterior. Se busca el ciclo al que
    pertenece el `format_id` seleccionado, no el último ciclo de la tabla.
    """

    def __init__(self, history_service: FormatRevisionHistoryService) -> None:
        self._history_service = history_service

    def get_for_formats(
        self,
        *,
        document_id: str,
        formats: tuple[GeneratedFormat, ...],
    ) -> dict[GeneratedFormatType, CurrentCycleEvaluations]:
        """Obtiene las métricas del mismo ciclo que cada formato público.

        Args:
            document_id: Identificador canónico consultado por Frontend.
            formats: Versiones vigentes elegidas por GeneratedFormatQueryService.

        Returns:
            Proyección por tipo de formato, sin mezclar ciclos anteriores.

        Raises:
            RevisionHistoryInconsistentError: La versión elegida no pertenece
                a ningún ciclo persistido o corresponde a otro documento.
            Errores explícitos del historial y de sus repositorios.
        """
        result: dict[GeneratedFormatType, CurrentCycleEvaluations] = {}

        for generated_format in formats:
            if generated_format.document_id != document_id:
                raise RevisionHistoryInconsistentError(
                    "El formato vigente pertenece a otro documento."
                )

            history = self._history_service.get_history(
                document_id,
                generated_format.format_type,
            )
            selected_cycle = next(
                (
                    cycle
                    for cycle in history.cycles
                    if generated_format.format_id
                    in {
                        cycle.original.generated_format.format_id,
                        (
                            cycle.revision.generated_format.format_id
                            if cycle.revision is not None
                            else None
                        ),
                    }
                ),
                None,
            )
            if selected_cycle is None:
                raise RevisionHistoryInconsistentError(
                    "El formato vigente no tiene un ciclo de historial."
                )

            all_evaluations = list(selected_cycle.original.evaluations)
            if selected_cycle.revision is not None:
                all_evaluations.extend(selected_cycle.revision.evaluations)

            newest_first = tuple(
                sorted(
                    all_evaluations,
                    key=lambda evaluation: (
                        evaluation.created_at,
                        evaluation.evaluation_id,
                    ),
                    reverse=True,
                )
            )
            current_version_evaluation = next(
                (
                    item
                    for item in newest_first
                    if item.format_id == generated_format.format_id
                ),
                None,
            )
            result[generated_format.format_type] = CurrentCycleEvaluations(
                evaluation=current_version_evaluation,
                evaluations=newest_first,
            )

        return result
