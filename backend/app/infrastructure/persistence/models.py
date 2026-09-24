"""Modelos y conversiones utilizadas por la persistencia."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.domain.document import Document
from app.domain.enums import DocumentStatus


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """Representación persistible de un documento."""

    document_id: str
    original_filename: str
    sha256: str
    content_type: str | None
    size_bytes: int
    status: str
    oci_object_name: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentRecord":
        """Convierte una entidad de dominio en un registro persistible."""
        return cls(
            document_id=document.document_id,
            original_filename=document.original_filename,
            sha256=document.sha256,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            status=document.status.value,
            oci_object_name=document.oci_object_name,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "DocumentRecord":
        """Construye un registro a partir de una fila SQLite."""
        return cls(
            document_id=row["document_id"],
            original_filename=row["original_filename"],
            sha256=row["sha256"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            status=row["status"],
            oci_object_name=row["oci_object_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_domain(self) -> Document:
        """Convierte el registro persistido en una entidad de dominio."""
        return Document(
            document_id=self.document_id,
            original_filename=self.original_filename,
            sha256=self.sha256,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            status=DocumentStatus(self.status),
            oci_object_name=self.oci_object_name,
            created_at=datetime.fromisoformat(self.created_at),
            updated_at=datetime.fromisoformat(self.updated_at),
        )