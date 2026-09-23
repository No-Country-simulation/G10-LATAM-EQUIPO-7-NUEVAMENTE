"""Schemas para la carga de archivos."""

from pydantic import Field

from app.schemas.common import BaseSchema


class UploadedFile(BaseSchema):
    filename: str = Field(description="Nombre saneado con el que se almacenó el archivo.")
    original_filename: str
    content_type: str | None = None
    size_bytes: int = Field(ge=0)
    path: str = Field(description="Ruta donde quedó almacenado el archivo.")
