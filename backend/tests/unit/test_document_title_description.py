"""Pruebas de estabilidad del título y la descripción del documento."""

import hashlib

from app.domain.document import Document
from app.domain.enums import DocumentStatus


def build_document(
    *,
    document_title: str | None = None,
    document_description: str | None = None,
) -> Document:
    """Construye un documento válido con título/descripción opcionales."""
    content = b"contenido de prueba"

    return Document(
        document_id="doc_title_stability",
        original_filename="manual.txt",
        sha256=hashlib.sha256(content).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
        status=DocumentStatus.INDEXED,
        document_title=document_title,
        document_description=document_description,
    )


def test_assigns_title_and_description_when_document_has_none() -> None:
    """La primera respuesta válida de Agentes queda asociada al documento."""
    document = build_document()

    document.assign_document_title_description(
        document_title="Introducción a RAG",
        document_description="Explica los fundamentos de RAG.",
    )

    assert document.document_title == "Introducción a RAG"
    assert (
        document.document_description
        == "Explica los fundamentos de RAG."
    )


def test_regeneration_does_not_replace_existing_title_and_description() -> (
    None
):
    """Una regeneración de formatos no pisa el título ya establecido."""
    document = build_document(
        document_title="Título original",
        document_description="Descripción original.",
    )

    original_updated_at = document.updated_at

    document.assign_document_title_description(
        document_title="Título regenerado",
        document_description="Descripción regenerada.",
    )

    assert document.document_title == "Título original"
    assert document.document_description == "Descripción original."
    assert document.updated_at == original_updated_at


def test_assigns_only_the_field_still_missing() -> None:
    """Si solo falta la descripción, únicamente ella se completa."""
    document = build_document(
        document_title="Título ya persistido",
        document_description=None,
    )

    document.assign_document_title_description(
        document_title="Título que Agentes reenvía",
        document_description="Descripción nueva.",
    )

    assert document.document_title == "Título ya persistido"
    assert document.document_description == "Descripción nueva."


def test_none_values_do_not_overwrite_or_touch_updated_at() -> None:
    """Un fallo de extracción (None, None) no degrada datos útiles."""
    document = build_document(
        document_title="Título útil",
        document_description="Descripción útil.",
    )

    original_updated_at = document.updated_at

    document.assign_document_title_description(
        document_title=None,
        document_description=None,
    )

    assert document.document_title == "Título útil"
    assert document.document_description == "Descripción útil."
    assert document.updated_at == original_updated_at
