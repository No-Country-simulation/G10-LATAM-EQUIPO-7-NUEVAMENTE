"""Pruebas unitarias de la entidad Document."""

import hashlib

import pytest

from app.domain.document import Document
from app.domain.enums import DocumentStatus


def build_document() -> Document:
    content = b"Documento NuevaMente"

    return Document(
        document_id="doc_123",
        original_filename="manual.pdf",
        sha256=hashlib.sha256(content).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
    )


def test_document_starts_as_received() -> None:
    document = build_document()

    assert document.status == DocumentStatus.RECEIVED
    assert document.oci_object_name is None


def test_document_updates_status() -> None:
    document = build_document()

    document.update_status(DocumentStatus.VALIDATED)

    assert document.status == DocumentStatus.VALIDATED


def test_document_assigns_oci_object() -> None:
    document = build_document()

    document.assign_oci_object(
        "documents/doc_123/original.pdf"
    )

    assert (
        document.oci_object_name
        == "documents/doc_123/original.pdf"
    )


def test_document_rejects_invalid_sha256() -> None:
    with pytest.raises(ValueError):
        Document(
            document_id="doc_123",
            original_filename="manual.pdf",
            sha256="invalid",
            content_type="application/pdf",
            size_bytes=10,
        )


def test_document_starts_as_active() -> None:
    """Un documento nuevo debe inicializarse activo por defecto."""
    document = build_document()

    assert document.is_active is True


def test_document_deactivate_and_activate() -> None:
    """deactivate y activate modifican únicamente is_active y updated_at."""
    document = build_document()
    document.update_status(DocumentStatus.STORED)
    document.assign_oci_object("documents/doc_123/original.pdf")

    initial_updated_at = document.updated_at

    document.deactivate()

    assert document.is_active is False
    assert document.status == DocumentStatus.STORED
    assert document.oci_object_name == "documents/doc_123/original.pdf"
    assert document.learning_metadata is None
    assert document.updated_at >= initial_updated_at

    deactivated_updated_at = document.updated_at

    document.activate()

    assert document.is_active is True
    assert document.status == DocumentStatus.STORED
    assert document.oci_object_name == "documents/doc_123/original.pdf"
    assert document.learning_metadata is None
    assert document.updated_at >= deactivated_updated_at