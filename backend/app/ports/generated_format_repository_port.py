"""Puerto de persistencia de formatos generados."""

from typing import Protocol

from app.domain.generated_format import (
    GeneratedFormat,
)


class GeneratedFormatRepositoryError(
    Exception
):
    """Error general de persistencia de formatos."""


class GeneratedFormatAlreadyExistsError(
    GeneratedFormatRepositoryError
):
    """El formato generado ya existe."""


class GeneratedFormatDocumentNotFoundError(
    GeneratedFormatRepositoryError
):
    """El documento asociado al formato no existe."""


class GeneratedFormatRepositoryPort(
    Protocol
):
    """Operaciones requeridas para persistir generaciones."""

    def create(
        self,
        generated_format: GeneratedFormat,
    ) -> GeneratedFormat:
        """Persiste una generación."""
        ...

    def find_by_id(
        self,
        format_id: str,
    ) -> GeneratedFormat | None:
        """Busca una generación por identificador."""
        ...

    def find_by_document_id(
        self,
        document_id: str,
    ) -> list[GeneratedFormat]:
        """Obtiene el historial de generaciones de un documento."""
        ...