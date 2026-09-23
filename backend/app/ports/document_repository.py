"""Contrato para la persistencia de documentos."""

from typing import Protocol

from app.domain.document import Document


class DocumentRepositoryError(Exception):
    """Error general al acceder a la persistencia de documentos."""

class DocumentAlreadyExistsError(DocumentRepositoryError):
    """El documento ya existe en el repositorio."""
    
class DocumentRepository(Protocol):
    """Define las operaciones de persistencia requeridas por BackendAPI."""

    def create(self, document: Document) -> Document:
        """Persiste un documento nuevo.

        Args:
            document: Entidad de dominio que será almacenada.

        Returns:
            Documento persistido.
        """
        ...

    def find_by_id(self, document_id: str) -> Document | None:
        """Busca un documento mediante su identificador interno.

        Args:
            document_id: Identificador único del documento.

        Returns:
            Documento encontrado o ``None``.
        """
        ...

    def find_by_sha256(self, sha256: str) -> Document | None:
        """Busca un documento mediante su firma SHA-256.

        Args:
            sha256: Firma hexadecimal SHA-256.

        Returns:
            Documento encontrado o ``None``.
        """
        ...

    def update(self, document: Document) -> Document:
        """Actualiza la información persistida de un documento.

        Args:
            document: Entidad con los cambios que deben persistirse.

        Returns:
            Documento actualizado.
        """
        ...