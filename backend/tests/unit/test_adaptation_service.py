"""Pruebas unitarias de AdaptationService."""

import asyncio
import hashlib

import pytest

from app.application.adaptation_service import (
    AdaptationService,
    DocumentNotReadyError,
)
from app.domain.document import Document
from app.domain.enums import DocumentStatus
from app.ports.agents import (
    AgentAdaptationInput,
    AgentAdaptationResult,
)


class FakeDocumentRepository:
    def __init__(self, document: Document) -> None:
        self.document = document

    def create(self, document: Document) -> Document:
        self.document = document
        return document

    def find_by_id(self, document_id: str) -> Document | None:
        if self.document.document_id == document_id:
            return self.document
        return None

    def find_by_sha256(self, sha256: str) -> Document | None:
        if self.document.sha256 == sha256:
            return self.document
        return None

    def update(self, document: Document) -> Document:
        self.document = document
        return document


class FakeAgents:
    async def generate_adaptation(
        self,
        request: AgentAdaptationInput,
    ) -> AgentAdaptationResult:
        return AgentAdaptationResult(
            metadata={"profile": request.profile},
            content={"title": "Contenido adaptado"},
            quality={"status": "approved"},
        )


def build_document(
    status: DocumentStatus,
) -> Document:
    content = b"contenido"

    return Document(
        document_id="doc_123",
        original_filename="manual.pdf",
        sha256=hashlib.sha256(content).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
        status=status,
    )


def test_generate_adaptation_for_indexed_document() -> None:
    repository = FakeDocumentRepository(
        build_document(DocumentStatus.INDEXED)
    )

    service = AdaptationService(
        repository=repository,
        agents=FakeAgents(),
    )

    result = asyncio.run(
        service.generate(
            document_id="doc_123",
            profile="Principiante",
            output_format="Flashcards",
            niche="General",
            detail_level="Didáctico",
        )
    )

    assert result.content["title"] == "Contenido adaptado"


def test_rejects_document_not_indexed() -> None:
    repository = FakeDocumentRepository(
        build_document(DocumentStatus.STORED)
    )

    service = AdaptationService(
        repository=repository,
        agents=FakeAgents(),
    )

    with pytest.raises(DocumentNotReadyError):
        asyncio.run(
            service.generate(
                document_id="doc_123",
                profile="Principiante",
                output_format="Flashcards",
                niche="General",
                detail_level="Didáctico",
            )
        )