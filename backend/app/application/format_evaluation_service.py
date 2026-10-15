"""Caso de uso: evaluar una generación y registrar su resultado histórico."""

from uuid import uuid4

from app.domain.format_evaluation import FormatEvaluation
from app.ports.data_ia_port import (
    DataIAError,
    DataIAEvaluationInput,
    DataIAPort,
    DataIAV2EvaluationResult,
)
from app.ports.format_evaluation_repository_port import FormatEvaluationRepositoryPort
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryPort


class GeneratedFormatNotFoundError(Exception):
    """La generación solicitada no existe."""


class GeneratedFormatNotEvaluationReadyError(Exception):
    """La generación no contiene información suficiente para evaluación."""


class EvaluationResponseMismatchError(Exception):
    """Data/IA respondió por otro documento o formato."""


class FormatEvaluationIntegrationError(Exception):
    """Data/IA no pudo completar la evaluación."""


class FormatEvaluationService:
    """Recupera el contenido, llama a Data/IA y persiste el resultado.

    No altera la generación almacenada ni solicita revisiones. Un fallo de
    evaluación no invalida el contenido previamente generado.
    """

    def __init__(
        self,
        *,
        generated_format_repository: GeneratedFormatRepositoryPort,
        evaluation_repository: FormatEvaluationRepositoryPort,
        data_ia: DataIAPort,
    ) -> None:
        self._generated_format_repository = generated_format_repository
        self._evaluation_repository = evaluation_repository
        self._data_ia = data_ia

    async def evaluate_format(self, format_id: str) -> FormatEvaluation:
        """Evalúa una generación persistida, conservando V1.1 y V2.

        Raises:
            GeneratedFormatNotFoundError: format_id desconocido.
            GeneratedFormatNotEvaluationReadyError: contenido/evidencias inválidos.
            FormatEvaluationIntegrationError: error de Data/IA.
            EvaluationResponseMismatchError: documento o formato discordante.
        """
        generated_format = self._generated_format_repository.find_by_id(format_id)
        if generated_format is None:
            raise GeneratedFormatNotFoundError(
                f"No existe el formato generado {format_id}."
            )

        if not generated_format.is_evaluation_ready:
            raise GeneratedFormatNotEvaluationReadyError(
                "El formato generado no contiene contenido "
                "y evidencias completas para ser evaluado."
            )
        if generated_format.content is None:
            raise GeneratedFormatNotEvaluationReadyError(
                "El contenido generado no está disponible."
            )

        request = DataIAEvaluationInput(
            document_id=generated_format.document_id,
            format_type=generated_format.format_type,
            generated_content=generated_format.content,
            chunks_used=generated_format.chunks_used,
            generation_context=generated_format.generation_context,
        )
        try:
            result = await self._data_ia.evaluate(request)
        except DataIAError as exc:
            raise FormatEvaluationIntegrationError(
                f"Data/IA no pudo evaluar el formato {format_id}."
            ) from exc

        if result.document_id != generated_format.document_id:
            raise EvaluationResponseMismatchError(
                "Data/IA devolvió un document_id diferente al evaluado."
            )
        if result.format_type != generated_format.format_type:
            raise EvaluationResponseMismatchError(
                "Data/IA devolvió un format diferente al solicitado."
            )

        evaluation_id = f"eval_{uuid4().hex}"
        if isinstance(result, DataIAV2EvaluationResult):
            evaluation = FormatEvaluation(
                evaluation_id=evaluation_id,
                format_id=format_id,
                verdict=result.verdict,
                heuristic_scores=result.heuristic_scores,
                semantic_evaluation=result.semantic_evaluation,
                evaluator_version=result.evaluator_version,
                rubric_version=result.rubric_version,
            )
        else:
            evaluation = FormatEvaluation(
                evaluation_id=evaluation_id,
                format_id=format_id,
                status=result.status,
                scores=result.scores,
                unsupported_information=result.unsupported_information,
                observations=result.observations,
                evaluator_version=result.evaluator_version,
                rubric_version=result.rubric_version,
            )

        self._evaluation_repository.create(evaluation)
        return evaluation
