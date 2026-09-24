from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

class ErrorDetail(BaseModel):
    """Estructura para el manejo de errores explícitos."""
    code: str = Field(..., description="Código del error (ej. 'TIMEOUT', 'NO_INDEX').")
    message: str = Field(..., description="Mensaje descriptivo del error.")

class RetrievalResult(BaseModel):
    """Representa un chunk individual recuperado por el sistema RAG."""
    rank: int = Field(
        ...,
        ge=1,
        description="Posición del resultado (1 es el más relevante)."
    )
    chunk_id: str = Field(..., description="ID único del fragmento de texto.")
    document_id: str = Field(..., description="ID del documento de origen.")
    score: float = Field(..., description="Puntaje de similitud (ej. similitud del coseno).")
    text: str = Field(..., description="Texto recuperado que se usará como contexto.")
    metadata: dict = Field(default_factory=dict, description="Metadatos adicionales opcionales.")

class RetrievalContract(BaseModel):
    """Contrato principal que valida la respuesta del módulo de Agentes."""
    contract_version: Literal["1.0"] = Field(..., description="Versión estricta del contrato de integración.")
    case_id: str = Field(..., description="Identificador del caso de prueba (Ground Truth).")
    query: str = Field(..., description="La pregunta original del usuario.")
    top_k: Literal[5] = Field(
        default=5,
        description="Cantidad fija de resultados solicitados por Retrieval Contract v1.",
    )
    score_type: Literal["cosine_similarity"] = Field(..., description="Métrica de distancia utilizada.")
    status: Literal["success", "no_results", "error"] = Field(..., description="Estado de la recuperación.")
    results: List[RetrievalResult] = Field(default_factory=list, description="Lista de fragmentos recuperados.")
    error: Optional[ErrorDetail] = Field(default=None, description="Detalle del error si el status es 'error'.")

@model_validator(mode="after")
def validate_contract_consistency(self):
        """
        Valida reglas semánticas de Retrieval Contract v1.
        """

        if self.status == "success":
            if not self.results:
                raise ValueError(
                    "status='success' requiere al menos un resultado."
                )

            if self.error is not None:
                raise ValueError(
                    "status='success' requiere error=null."
                )

        elif self.status == "no_results":
            if self.results:
                raise ValueError(
                    "status='no_results' requiere results=[]."
                )

            if self.error is not None:
                raise ValueError(
                    "status='no_results' requiere error=null."
                )

        elif self.status == "error":
            if self.results:
                raise ValueError(
                    "status='error' requiere results=[]."
                )

            if self.error is None:
                raise ValueError(
                    "status='error' requiere un objeto error."
                )

        for expected_rank, result in enumerate(
            self.results,
            start=1,
        ):
            if result.rank != expected_rank:
                raise ValueError(
                    f"Se esperaba rank={expected_rank}, "
                    f"pero se recibió rank={result.rank}."
                )

        return self
