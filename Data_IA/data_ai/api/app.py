"""API del servicio de evaluación Data/IA."""

from fastapi import FastAPI

from data_ai.evaluation.reviewer import evaluar_contenido
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
    Evalúa un Quiz o conjunto de Flashcards.

    El request ya llega validado por Pydantic/FastAPI.
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
