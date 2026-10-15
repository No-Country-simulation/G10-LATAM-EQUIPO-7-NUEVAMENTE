"""Consulta de ciclos de generación, correcciones y evaluaciones persistidas.

Un ciclo comienza con una generación raíz (revision_of_format_id=None) y
puede contener una única revisión. La consulta no realiza llamadas externas ni
modifica estado: solo agrupa datos provenientes de los repositorios.
"""

from dataclasses import dataclass

from app.domain.enums import GeneratedFormatType
from app.domain.format_evaluation import FormatEvaluation
from app.domain.generated_format import GeneratedFormat
from app.ports.document_repository_port import DocumentRepositoryPort
from app.ports.format_evaluation_repository_port import FormatEvaluationRepositoryPort
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryPort


class RevisionHistoryDocumentNotFoundError(Exception):
    """No existe el documento solicitado."""


class RevisionHistoryInconsistentError(Exception):
    """El historial persistido viola el contrato de un ciclo de revisión."""


@dataclass(frozen=True, slots=True)
class RevisionHistoryItem:
    """Una versión con sus evaluaciones ordenadas cronológicamente."""

    generated_format: GeneratedFormat
    evaluations: tuple[FormatEvaluation, ...]


@dataclass(frozen=True, slots=True)
class FormatRevisionCycle:
    """Generación raíz, posible corrección y evaluación vigente del ciclo."""

    original: RevisionHistoryItem
    revision: RevisionHistoryItem | None
    latest_evaluation: FormatEvaluation | None


@dataclass(frozen=True, slots=True)
class FormatRevisionHistory:
    """Historial completo de un documento para un formato pedagógico."""

    document_id: str
    format_type: GeneratedFormatType
    cycles: tuple[FormatRevisionCycle, ...]


class FormatRevisionHistoryService:
    """Agrupa generaciones y evaluaciones respetando los límites de cada ciclo."""

    def __init__(
        self,
        *,
        document_repository: DocumentRepositoryPort,
        generated_format_repository: GeneratedFormatRepositoryPort,
        evaluation_repository: FormatEvaluationRepositoryPort,
    ) -> None:
        self._documents = document_repository
        self._formats = generated_format_repository
        self._evaluations = evaluation_repository

    def get_history(
        self, document_id: str, format_type: GeneratedFormatType
    ) -> FormatRevisionHistory:
        """Devuelve ciclos nuevos primero, sin reutilizar evaluaciones antiguas.

        Raises:
            RevisionHistoryDocumentNotFoundError: Documento inexistente.
            RevisionHistoryInconsistentError: Referencias corruptas en persistencia.
            Errores explícitos de los repositorios correspondientes.
        """
        if self._documents.find_by_id(document_id) is None:
            raise RevisionHistoryDocumentNotFoundError(
                f"No existe el documento {document_id}."
            )

        history = [
            item for item in self._formats.find_by_document_id(document_id)
            if item.format_type == format_type
        ]
        roots = [item for item in history if item.revision_of_format_id is None]
        revisions = [item for item in history if item.revision_of_format_id is not None]
        by_root: dict[str, GeneratedFormat] = {}
        for revision in revisions:
            root_id = revision.revision_of_format_id
            if root_id in by_root:
                raise RevisionHistoryInconsistentError(
                    f"El formato {root_id} tiene más de una corrección."
                )
            by_root[root_id] = revision

        root_ids = {item.format_id for item in roots}
        if any(root_id not in root_ids for root_id in by_root):
            raise RevisionHistoryInconsistentError(
                "Existe una corrección sin su generación raíz."
            )

        def item_with_evaluations(item: GeneratedFormat) -> RevisionHistoryItem:
            evaluations = self._evaluations.find_by_format_id(item.format_id)
            ordered = tuple(sorted(
                evaluations,
                key=lambda e: (e.created_at, e.evaluation_id),
            ))
            return RevisionHistoryItem(item, ordered)

        cycles: list[FormatRevisionCycle] = []
        for root in sorted(
            roots,
            key=lambda item: (item.created_at, item.updated_at, item.format_id),
            reverse=True,
        ):
            original = item_with_evaluations(root)
            child = by_root.get(root.format_id)
            revision = item_with_evaluations(child) if child else None
            # Solo una evaluación de la corrección puede ser la vigente si
            # existe la corrección. Nunca heredamos la nota del original.
            current = revision if revision is not None else original
            latest = current.evaluations[-1] if current.evaluations else None
            cycles.append(FormatRevisionCycle(original, revision, latest))

        return FormatRevisionHistory(document_id, format_type, tuple(cycles))
