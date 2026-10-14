"""Caso de uso para solicitar UNA corrección pedagógica a Agentes.

La capa de aplicación decide únicamente si la fuente puede revisarse, recupera
sus datos canónicos y delega al puerto. No contiene HTTP, evaluación, política
de reintentos ni escrituras de versiones; esas operaciones corresponden al
orquestador del ciclo y a otras tarjetas de Sprint 4.
"""

from app.domain.generated_format import GeneratedFormat
from app.domain.revision_feedback import RevisionFeedback
from app.ports.agent_revision_port import (
    AgentRevisionError,
    AgentRevisionInput,
    AgentRevisionPort,
    AgentRevisionResult,
)
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryPort


class RevisionSourceNotFoundError(Exception):
    """El format_id solicitado no existe en el repositorio."""


class RevisionSourceNotReadyError(Exception):
    """El intento original no tiene contenido y evidencias completos."""


class RevisionResultMismatchError(Exception):
    """La respuesta no corresponde al documento o tipo solicitado."""


class FormatRevisionIntegrationError(Exception):
    """Agentes no pudo completar la comunicación o incumplió el contrato."""


class FormatRevisionService:
    """Invoca al Agente Revisor a través de su puerto tipado.

    Args:
        generated_format_repository: Repositorio de intentos ya persistidos.
        agent_revision: Puerto para solicitar una revisión a Agentes.

    Importante: una respuesta fallida o un error HTTP no reemplaza el contenido
    previamente válido. Este servicio no realiza operaciones de escritura.
    """

    def __init__(
        self,
        *,
        generated_format_repository: GeneratedFormatRepositoryPort,
        agent_revision: AgentRevisionPort,
    ) -> None:
        self._generated_format_repository = generated_format_repository
        self._agent_revision = agent_revision

    async def request_revision(
        self,
        *,
        format_id: str,
        feedback: RevisionFeedback,
    ) -> AgentRevisionResult:
        """Solicita una sola revisión del formato identificado.

        Args:
            format_id: Identificador persistido de la generación original.
            feedback: Evaluación V2 negativa y accionable, ya normalizada.

        Returns:
            Resultado de Agentes con contenido corregido y evidencias,
            o un resultado terminal fallido sin sustituir la versión original.

        Raises:
            ValueError: format_id vacío.
            RevisionSourceNotFoundError: format_id no encontrado.
            RevisionSourceNotReadyError: versión inicial no revisable.
            FormatRevisionIntegrationError: error externo/de contrato.
            RevisionResultMismatchError: identidad devuelta inconsistente.

        No persiste nuevas versiones ni aplica presupuestos de reintentos.
        """
        if not format_id.strip():
            raise ValueError("format_id debe ser una cadena no vacía.")

        original = self._generated_format_repository.find_by_id(format_id)
        if original is None:
            raise RevisionSourceNotFoundError(
                f"No existe el formato generado {format_id}."
            )

        request = self._build_request(original=original, feedback=feedback)
        try:
            result = await self._agent_revision.revise_format(request)
        except AgentRevisionError as exc:
            raise FormatRevisionIntegrationError(
                f"No fue posible solicitar la revisión del formato {format_id}."
            ) from exc

        if result.document_id != original.document_id:
            raise RevisionResultMismatchError(
                "La revisión devolvió un document_id diferente al solicitado."
            )
        if result.format_type != original.format_type:
            raise RevisionResultMismatchError(
                "La revisión devolvió un format diferente al solicitado."
            )

        return result

    @staticmethod
    def _build_request(
        *,
        original: GeneratedFormat,
        feedback: RevisionFeedback,
    ) -> AgentRevisionInput:
        """Construye el contrato interno sin depender del proveedor HTTP."""
        if not original.is_evaluation_ready or original.content is None:
            raise RevisionSourceNotReadyError(
                "Solo puede revisarse una generación success con contenido "
                "y evidencias completas."
            )

        return AgentRevisionInput(
            document_id=original.document_id,
            format_type=original.format_type,
            current_content=original.content,
            generation_context=original.generation_context,
            chunks_used=original.chunks_used,
            feedback=feedback,
        )
