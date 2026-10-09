"""Pruebas de estabilidad de metadata pedagógica del documento."""

import hashlib

from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.domain.learning_metadata import LearningMetadata


def build_document(
    *,
    learning_metadata: LearningMetadata | None = None,
) -> Document:
    """Construye un documento válido con metadata opcional."""
    content = b"contenido de prueba"

    return Document(
        document_id="doc_metadata_stability",
        original_filename="manual.txt",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
        status=DocumentStatus.INDEXED,
        learning_metadata=learning_metadata,
    )


def build_metadata(
    *,
    key_concept: str,
    prerequisite: str,
    estimated_time_minutes: int,
) -> LearningMetadata:
    """Construye metadata pedagógica útil para las pruebas."""
    return LearningMetadata(
        key_concepts=(
            key_concept,
        ),
        prerequisites=(
            prerequisite,
        ),
        estimated_time_minutes=(
            estimated_time_minutes
        ),
    )


def test_assigns_learning_metadata_when_document_has_none() -> None:
    """La primera respuesta válida queda asociada al documento."""
    document = build_document()

    metadata = build_metadata(
        key_concept="RAG",
        prerequisite="APIs REST",
        estimated_time_minutes=12,
    )

    document.assign_learning_metadata(
        metadata
    )

    assert (
        document.learning_metadata
        == metadata
    )


def test_regeneration_does_not_replace_existing_useful_metadata() -> None:
    """Una nueva generación de formatos conserva metadata ya establecida."""
    original_metadata = build_metadata(
        key_concept="BackendAPI",
        prerequisite="Fundamentos de APIs",
        estimated_time_minutes=5,
    )

    regenerated_metadata = build_metadata(
        key_concept="BackendAPI",
        prerequisite=(
            "Arquitecturas basadas en microservicios"
        ),
        estimated_time_minutes=7,
    )

    document = build_document(
        learning_metadata=(
            original_metadata
        )
    )

    original_updated_at = (
        document.updated_at
    )

    document.assign_learning_metadata(
        regenerated_metadata
    )

    assert (
        document.learning_metadata
        == original_metadata
    )

    assert (
        document.updated_at
        == original_updated_at
    )


def test_valid_metadata_replaces_empty_fallback() -> None:
    """Una regeneración puede recuperar metadata si antes hubo fallback."""
    document = build_document(
        learning_metadata=(
            LearningMetadata.empty()
        )
    )

    recovered_metadata = build_metadata(
        key_concept="Persistencia OCI",
        prerequisite="Almacenamiento en la nube",
        estimated_time_minutes=10,
    )

    document.assign_learning_metadata(
        recovered_metadata
    )

    assert (
        document.learning_metadata
        == recovered_metadata
    )


def test_empty_fallback_does_not_replace_existing_useful_metadata() -> None:
    """Un fallback posterior no degrada metadata útil ya persistida."""
    original_metadata = build_metadata(
        key_concept="RAG",
        prerequisite="Fundamentos de Python",
        estimated_time_minutes=15,
    )

    document = build_document(
        learning_metadata=(
            original_metadata
        )
    )

    document.assign_learning_metadata(
        LearningMetadata.empty()
    )

    assert (
        document.learning_metadata
        == original_metadata
    )


def test_reassigning_same_metadata_is_idempotent() -> None:
    """Asignar exactamente la misma metadata no altera updated_at."""
    metadata = build_metadata(
        key_concept="Flashcards",
        prerequisite="Lectura básica",
        estimated_time_minutes=8,
    )

    document = build_document(
        learning_metadata=metadata
    )

    original_updated_at = (
        document.updated_at
    )

    document.assign_learning_metadata(
        metadata
    )

    assert (
        document.learning_metadata
        == metadata
    )

    assert (
        document.updated_at
        == original_updated_at
    )
