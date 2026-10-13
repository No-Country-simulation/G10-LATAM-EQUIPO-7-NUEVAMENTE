"""Pruebas HTTP de exposición de metadatos pedagógicos."""

import hashlib

from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.domain.learning_metadata import LearningMetadata
from app.infrastructure.persistence.repository_factory import (
    create_document_repository,
)


def test_document_detail_exposes_learning_metadata(
    client: TestClient,
    api_prefix: str,
) -> None:
    """GET /documents/{id} expone metadata persistida a nivel documento."""
    content = b"contenido con metadata pedagogica"

    document = Document(
        document_id="doc_learning_metadata",
        original_filename="manual.txt",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
        status=DocumentStatus.INDEXED,
        oci_object_name=(
            "documents/doc_learning_metadata/original.txt"
        ),
        learning_metadata=LearningMetadata(
            key_concepts=(
                "RAG",
                "Embeddings",
                "Vector Store",
            ),
            prerequisites=(
                "Fundamentos de Python",
            ),
            estimated_time_minutes=18,
        ),
    )

    repository = (
        create_document_repository(
            settings.DATABASE_URL
        )
    )

    repository.create(
        document
    )

    response = client.get(
        f"{api_prefix}/documents/"
        f"{document.document_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["document_id"] == (
        document.document_id
    )
    assert "estimated_time" not in body

    assert body["learning_metadata"] == {
        "key_concepts": [
            "RAG",
            "Embeddings",
            "Vector Store",
        ],
        "prerequisites": [
            "Fundamentos de Python",
        ],
        "estimated_time_minutes": 18,
    }
