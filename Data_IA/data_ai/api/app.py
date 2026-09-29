"""
API del servicio de evaluación Data/IA.

Sprint 2:
- Expone POST /evaluate.
- Valida automáticamente EvaluationRequest con Pydantic/FastAPI.
- Deja preparada la integración de la lógica de evaluación de calidad.
- Mientras el evaluator real no esté conectado, responde HTTP 501 para
  payloads válidos.

Ejecución:
    python -m uvicorn data_ai.api.app:app --reload
"""

from fastapi import FastAPI, HTTPException

from data_ai.schemas.format_evaluation import (
    EvaluationRequest,
    EvaluationResponse,
)

app = FastAPI(
    title="NuevaMente Data/IA Evaluation API",
    version="0.1.0",
    description=(
        "Servicio de Data/IA para validar y evaluar formatos educativos "
        "generados durante Sprint 2."
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
def evaluate_format(request: EvaluationRequest) -> EvaluationResponse:
    """
    Recibe un Quiz o conjunto de Flashcards junto con los chunks usados
    como evidencia.

    FastAPI + Pydantic validan el contrato antes de entrar a esta función.
    La lógica de calidad se integrará aquí cuando el reviewer/evaluator
    esté disponible.
    """

    # Punto de integración futuro:
    #
    # result = quality_evaluator.evaluate(
    #     generated_content=request.generated_content,
    #     chunks_used=request.chunks_used,
    # )
    #
    # return EvaluationResponse(
    #     document_id=request.document_id,
    #     format=request.format,
    #     status=result.status,
    #     scores=result.scores,
    #     informacion_no_respaldada=result.informacion_no_respaldada,
    #     observaciones=result.observaciones,
    # )

    raise HTTPException(
        status_code=501,
        detail={
            "code": "QUALITY_EVALUATOR_NOT_IMPLEMENTED",
            "message": (
                "El contrato de entrada es válido, pero la lógica de "
                "evaluación de calidad todavía no ha sido integrada."
            ),
            "document_id": request.document_id,
            "format": request.format,
        },
    )
