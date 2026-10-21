"""Reconstruye el contrato público de Evaluation V2 para Agentes.

Se parte de la evaluación V2 ya persistida por BackendAPI. La salida contiene
exclusivamente las claves del contrato de Data/IA; no combina scores ni añade
un veredicto inventado. Es equivalente en estructura y valores a la respuesta
normalizada, aunque no representa los bytes HTTP originales.
"""

from dataclasses import asdict

from app.domain.enums import GeneratedFormatType
from app.domain.format_evaluation import FormatEvaluation


class RevisionEvaluationContractError(ValueError):
    """La evaluación persistida no satisface el contrato público V2."""


def build_evaluator_response_v2(
    *,
    document_id: str,
    format_type: GeneratedFormatType,
    evaluation: FormatEvaluation,
) -> dict[str, object]:
    """Construye el JSON V2 necesario para solicitar una sola corrección.

    Args:
        document_id: Identidad del documento fuente, tomada del formato raíz.
        format_type: Tipo pedagógico del formato raíz.
        evaluation: Evaluación V2 persistida de ese formato.

    Returns:
        Objeto serializable como JSON, con las siete claves definidas por
        EvaluationResponseV2 de Data/IA.

    Raises:
        RevisionEvaluationContractError: Evaluación V1, incompleta o sin
            veredicto pedagógico negativo y accionable.
    """
    if not document_id.strip():
        raise RevisionEvaluationContractError("document_id es obligatorio.")
    if evaluation.verdict not in ("requires_revision", "rejected"):
        raise RevisionEvaluationContractError(
            "La revisión solo procede con verdict requires_revision o rejected."
        )
    if evaluation.semantic_evaluation is None:
        raise RevisionEvaluationContractError(
            "Una revisión requiere semantic_evaluation V2."
        )
    if not evaluation.evaluator_version or not evaluation.rubric_version:
        raise RevisionEvaluationContractError(
            "La respuesta V2 requiere evaluator_version y rubric_version."
        )

    return {
        "document_id": document_id,
        "format": format_type.value,
        "verdict": evaluation.verdict,
        "heuristic_scores": (
            asdict(evaluation.heuristic_scores)
            if evaluation.heuristic_scores is not None
            else None
        ),
        "semantic_evaluation": asdict(evaluation.semantic_evaluation),
        "evaluator_version": evaluation.evaluator_version,
        "rubric_version": evaluation.rubric_version,
    }
