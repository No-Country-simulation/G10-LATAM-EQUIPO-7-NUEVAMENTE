"""Orquesta una sola corrección por generación y la reevaluación V2.

Responsabilidades: decidir elegibilidad, reservar una única versión mediante
SQLite, llamar al caso de uso del revisor, persistir la respuesta y reevaluar.
La generación original nunca se modifica. El índice único de persistencia
impide reservas duplicadas incluso si dos procesos compiten.
"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.application.format_evaluation_feedback_mapper import build_revision_feedback
from app.application.format_evaluation_service import (
    EvaluationResponseMismatchError,
    FormatEvaluationIntegrationError,
    FormatEvaluationService,
    GeneratedFormatNotEvaluationReadyError,
    GeneratedFormatNotFoundError,
)
from app.application.format_revision_service import (
    FormatRevisionIntegrationError,
    FormatRevisionService,
    RevisionResultMismatchError,
    RevisionSourceNotFoundError,
    RevisionSourceNotReadyError,
)
from app.domain.enums import GeneratedFormatStatus
from app.domain.format_evaluation import FormatEvaluation
from app.domain.generated_format import GeneratedFormat
from app.ports.format_evaluation_repository_port import FormatEvaluationRepositoryError
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
    GeneratedFormatRepositoryPort,
)


class FormatAutoRevisionError(Exception):
    """Agentes no pudo completar un intento ya reservado de revisión."""


class FormatAutoReevaluationError(Exception):
    """La nueva versión se persistió, pero su evaluación no se completó."""


class FormatAutoRevisionService:
    """Coordina un solo intento automático de corrección por versión raíz.

    La reserva PROCESSING se registra antes del HTTP para impedir que un
    fallo o una petición concurrente provoquen una segunda corrección.
    Los errores externos se persisten como FAILED y se comunican al caller.
    """

    def __init__(
        self,
        *,
        generated_format_repository: GeneratedFormatRepositoryPort,
        format_revision_service: FormatRevisionService,
        format_evaluation_service: FormatEvaluationService,
    ) -> None:
        self._formats = generated_format_repository
        self._revisor = format_revision_service
        self._evaluator = format_evaluation_service

    async def revise_if_required(
        self,
        *,
        original: GeneratedFormat,
        evaluation: FormatEvaluation,
    ) -> GeneratedFormat | None:
        """Persiste y evalúa una corrección; devuelve None cuando no aplica.

        Raises:
            ValueError: evaluación de otra versión o intento no original.
            GeneratedFormatRepositoryError: fallo al reservar o actualizar SQLite.
            FormatAutoRevisionError: error del revisor tras reservar el intento.
            FormatAutoReevaluationError: la nueva versión existe, pero su
                evaluación falló (sin invalidar el contenido correcto).
        """
        if original.revision_of_format_id is not None:
            raise ValueError("Una corrección no puede iniciar otra corrección.")
        if evaluation.format_id != original.format_id:
            raise ValueError("La evaluación no corresponde a la versión original.")
        if not original.is_evaluation_ready:
            return None

        feedback = build_revision_feedback(evaluation)
        if feedback is None:
            return None

        history = self._formats.find_by_document_id(original.document_id)
        if any(item.revision_of_format_id == original.format_id for item in history):
            return None

        reservation = GeneratedFormat(
            format_id=f"fmt_rev_{uuid4().hex}",
            document_id=original.document_id,
            format_type=original.format_type,
            status=GeneratedFormatStatus.PROCESSING,
            generation_context=original.generation_context,
            revision_of_format_id=original.format_id,
        )
        # Índice UNIQUE parcial en SQLite: solo una reserva por generación raíz.
        self._formats.create(reservation)

        try:
            agent_result = await self._revisor.request_revision(
                format_id=original.format_id,
                feedback=feedback,
            )
        except (
            FormatRevisionIntegrationError,
            RevisionResultMismatchError,
            RevisionSourceNotFoundError,
            RevisionSourceNotReadyError,
        ) as exc:
            self._formats.update(
                replace(
                    reservation,
                    status=GeneratedFormatStatus.FAILED,
                    error_message=f"La revisión automática falló: {exc}",
                    updated_at=datetime.now(UTC),
                )
            )
            raise FormatAutoRevisionError(
                f"No fue posible revisar el formato {original.format_id}."
            ) from exc

        completed = replace(
            reservation,
            status=agent_result.status,
            content=agent_result.content,
            chunks_used=agent_result.chunks_used,
            error_message=(
                agent_result.error_message
                or (agent_result.error.message if agent_result.error is not None else None)
            ),
            updated_at=datetime.now(UTC),
        )
        self._formats.update(completed)

        if completed.status == GeneratedFormatStatus.SUCCESS:
            try:
                await self._evaluator.evaluate_format(completed.format_id)
            except (
                EvaluationResponseMismatchError,
                FormatEvaluationIntegrationError,
                GeneratedFormatNotEvaluationReadyError,
                GeneratedFormatNotFoundError,
                FormatEvaluationRepositoryError,
                GeneratedFormatRepositoryError,
                RuntimeError,
            ) as exc:
                # No alterar una versión pedagógica exitosa por falla de Data/IA.
                raise FormatAutoReevaluationError(
                    f"La versión {completed.format_id} existe, "
                    "pero no fue posible reevaluarla."
                ) from exc

        return completed
