"""API del servicio de evaluación Data/IA."""

from fastapi import FastAPI

from data_ai.evaluation.evaluation_v2_service import (
    evaluate_content_v2,
)
from data_ai.evaluation.reviewer import evaluar_contenido
from data_ai.evaluation.semantic_evaluator import (
    SemanticEvaluator,
)
from data_ai.evaluation.unavailable_semantic_provider import (
    UnavailableSemanticProvider,
)
from data_ai.schemas.evaluation_v2 import (
    EvaluationResponseV2,
)
from data_ai.schemas.format_evaluation import (
    EvaluationRequest,
    EvaluationResponse,
)

app = FastAPI(
    title="NuevaMente Data/IA Evaluation API",
    version="0.2.0",
    description=(
        "Servicio de Data/IA para validar y evaluar "
        "formatos educativos generados."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    """Comprueba que el servicio Data/IA esté disponible."""
    return {"status": "ok"}


@app.post(
    "/evaluate",
    response_model=EvaluationResponse,
    summary="Solicitar evaluación de un formato generado",
)
def evaluate_format(
    request: EvaluationRequest,
) -> EvaluationResponse:
    """
    Evalúa contenido generado mediante el contrato V1.1.

    Este endpoint se conserva para compatibilidad con Backend.
    """

    result = evaluar_contenido(
        generated_content=request.generated_content,
        chunks_used=request.chunks_used,
        generation_context=request.generation_context,
    )

    return EvaluationResponse(
        document_id=request.document_id,
        format=request.format,
        status=result.status,
        scores=result.scores,
        informacion_no_respaldada=(
            result.informacion_no_respaldada
        ),
        observaciones=result.observaciones,
    )


@app.post(
    "/evaluate/v2",
    response_model=EvaluationResponseV2,
    summary="Solicitar evaluación mediante Evaluation Contract V2",
)
def evaluate_format_v2(
    request: EvaluationRequest,
) -> EvaluationResponseV2:
    """Evalúa contenido utilizando el flujo interno Evaluation V2.

    Mientras no exista un provider semántico real configurado,
    SemanticEvaluator utiliza UnavailableSemanticProvider.

    Esto permite exponer el contrato V2 sin fabricar scores
    semánticos ni afectar el endpoint V1.1.
    """

    semantic_evaluator = SemanticEvaluator(
        UnavailableSemanticProvider()
    )

    return evaluate_content_v2(
        document_id=request.document_id,
        content_format=request.format,
        generated_content=request.generated_content,
        chunks_used=request.chunks_used,
        generation_context=request.generation_context,
        semantic_evaluator=semantic_evaluator,
    )