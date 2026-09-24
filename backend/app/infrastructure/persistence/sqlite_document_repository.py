"""Implementación SQLite del repositorio de documentos."""

import sqlite3

from app.domain.document import Document
from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.models import DocumentRecord
from app.ports.document_repository import (
    DocumentAlreadyExistsError,
    DocumentRepositoryError,
)


class SQLiteDocumentRepository:
    """Persiste documentos utilizando SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def create(self, document: Document) -> Document:
        """Persiste un documento nuevo."""
        record = DocumentRecord.from_domain(document)

        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO documents (
                        document_id,
                        original_filename,
                        sha256,
                        content_type,
                        size_bytes,
                        status,
                        oci_object_name,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.document_id,
                        record.original_filename,
                        record.sha256,
                        record.content_type,
                        record.size_bytes,
                        record.status,
                        record.oci_object_name,
                        record.created_at,
                        record.updated_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DocumentAlreadyExistsError(
                f"El documento {document.document_id} ya existe."
            ) from exc
        except sqlite3.Error as exc:
            raise DocumentRepositoryError(
                "No fue posible crear el documento."
            ) from exc

        return document

    def find_by_id(self, document_id: str) -> Document | None:
        """Busca un documento por identificador."""
        return self._find_one(
            "SELECT * FROM documents WHERE document_id = ?",
            (document_id,),
        )

    def find_by_sha256(self, sha256: str) -> Document | None:
        """Busca un documento por su firma SHA-256."""
        return self._find_one(
            "SELECT * FROM documents WHERE sha256 = ?",
            (sha256,),
        )

    def update(self, document: Document) -> Document:
        """Actualiza la metadata persistida de un documento."""
        record = DocumentRecord.from_domain(document)

        try:
            with self._database.connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE documents
                    SET
                        original_filename = ?,
                        sha256 = ?,
                        content_type = ?,
                        size_bytes = ?,
                        status = ?,
                        oci_object_name = ?,
                        updated_at = ?
                    WHERE document_id = ?
                    """,
                    (
                        record.original_filename,
                        record.sha256,
                        record.content_type,
                        record.size_bytes,
                        record.status,
                        record.oci_object_name,
                        record.updated_at,
                        record.document_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise DocumentRepositoryError(
                        f"No existe el documento {document.document_id}."
                    )

        except DocumentRepositoryError:
            raise
        except sqlite3.Error as exc:
            raise DocumentRepositoryError(
                "No fue posible actualizar el documento."
            ) from exc

        return document

    def _find_one(
        self,
        query: str,
        parameters: tuple[str, ...],
    ) -> Document | None:
        try:
            with self._database.connect() as connection:
                row = connection.execute(
                    query,
                    parameters,
                ).fetchone()
        except sqlite3.Error as exc:
            raise DocumentRepositoryError(
                "No fue posible consultar documentos."
            ) from exc

        if row is None:
            return None

        return DocumentRecord.from_row(row).to_domain()