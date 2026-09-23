"""Schemas reutilizables y respuestas transversales de la API."""

from datetime import UTC, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Configuración base para los schemas de la API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ErrorDetail(BaseSchema):
    """Detalle individual de un error de la API."""

    code: str = Field(
        description="Identificador estable del error."
    )
    message: str = Field(
        description="Mensaje legible para el cliente."
    )
    field: str | None = Field(
        default=None,
        description="Campo que originó el error, si aplica.",
    )


class ErrorResponse(BaseSchema):
    """Respuesta estándar para errores de la API."""

    detail: str
    errors: list[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class Page(BaseSchema, Generic[T]):
    """Respuesta genérica para colecciones paginadas."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)

    @property
    def pages(self) -> int:
        """Calcula el número total de páginas."""
        return (
            (self.total + self.size - 1) // self.size
            if self.size
            else 0
        )


class HealthResponse(BaseSchema):
    """Estado general del servicio BackendAPI."""

    status: Literal["ok", "degraded"] = "ok"
    service: str
    version: str
    environment: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )