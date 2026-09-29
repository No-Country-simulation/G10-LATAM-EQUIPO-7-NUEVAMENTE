"""Pruebas unitarias del adaptador HTTP BackendAPI-RAG."""

import asyncio

import httpx
import pytest

from app.infrastructure.integrations.http_rag_adapter import (
    HTTPRAGAdapter,
)
from app.ports.rag_port import (
    RAGDocumentInput,
    RAGError,
)


def _build_document() -> RAGDocumentInput:
    """Construye un documento representativo para las pruebas."""
    return RAGDocumentInput(
        document_id="doc_123",
        filename="manual.pdf",
        content_type="application/pdf",
        content=b"%PDF-contenido-binario",
    )


def test_http_rag_adapter_sends_multipart_document() -> None:
    """Envía document_id y archivo original mediante multipart."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.url.path
            == "/api/v1/index"
        )

        content_type = request.headers[
            "content-type"
        ]

        assert content_type.startswith(
            "multipart/form-data;"
        )

        body = request.content

        assert b'name="document_id"' in body
        assert b"doc_123" in body
        assert b'name="file"' in body
        assert b'filename="manual.pdf"' in body
        assert b"application/pdf" in body
        assert b"%PDF-contenido-binario" in body

        return httpx.Response(
            status_code=200,
            json={
                "document_id": "doc_123",
                "status": "indexed",
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://rag.test",
        ) as client:
            adapter = HTTPRAGAdapter(
                client=client,
                index_path="/api/v1/index",
            )

            await adapter.index_document(
                _build_document()
            )

    asyncio.run(
        run_test()
    )


def test_http_rag_adapter_rejects_wrong_document_id() -> None:
    """Rechaza una respuesta asociada a otro documento."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "document_id": "doc_otro",
                "status": "indexed",
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://rag.test",
        ) as client:
            adapter = HTTPRAGAdapter(
                client=client,
                index_path="/api/v1/index",
            )

            with pytest.raises(
                RAGError,
                match=(
                    "document_id diferente"
                ),
            ):
                await adapter.index_document(
                    _build_document()
                )

    asyncio.run(
        run_test()
    )


def test_http_rag_adapter_rejects_non_indexed_response() -> None:
    """Rechaza respuestas que no confirman indexación."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "document_id": "doc_123",
                "status": "processing",
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://rag.test",
        ) as client:
            adapter = HTTPRAGAdapter(
                client=client,
                index_path="/api/v1/index",
            )

            with pytest.raises(
                RAGError,
                match="respuesta de indexación inválida",
            ):
                await adapter.index_document(
                    _build_document()
                )

    asyncio.run(
        run_test()
    )


def test_http_rag_adapter_translates_http_error() -> None:
    """Traduce respuestas HTTP de error al contrato RAGError."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=503,
            json={
                "detail": "Servicio no disponible",
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://rag.test",
        ) as client:
            adapter = HTTPRAGAdapter(
                client=client,
                index_path="/api/v1/index",
            )

            with pytest.raises(
                RAGError,
                match="estado HTTP 503",
            ):
                await adapter.index_document(
                    _build_document()
                )

    asyncio.run(
        run_test()
    )


def test_http_rag_adapter_translates_timeout() -> None:
    """Traduce timeouts HTTP al contrato RAGError."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    transport = httpx.MockTransport(
        handler
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://rag.test",
        ) as client:
            adapter = HTTPRAGAdapter(
                client=client,
                index_path="/api/v1/index",
            )

            with pytest.raises(
                RAGError,
                match="superó el tiempo permitido",
            ):
                await adapter.index_document(
                    _build_document()
                )

    asyncio.run(
        run_test()
    )