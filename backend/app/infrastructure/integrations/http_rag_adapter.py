"""Adaptador HTTP para la integración de BackendAPI con RAG."""

from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.ports.rag_port import (
    RAGDocumentInput,
    RAGError,
)


class _RAGIndexHTTPResponse(BaseModel):
    """Respuesta HTTP esperada del endpoint de indexación de RAG."""

    model_config = ConfigDict(
        extra="ignore",
    )

    document_id: str
    status: Literal["indexed"]


class HTTPRAGAdapter:
    """Implementa RAGPort mediante el endpoint HTTP público de RAG.

    El adapter traduce el contrato interno de BackendAPI al contrato
    multipart/form-data expuesto por el servicio de Agentes/RAG.

    BackendAPI conserva la responsabilidad de recuperar el documento
    desde OCI. RAG recibe únicamente el identificador canónico y el
    archivo original necesario para ejecutar la indexación.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        index_path: str,
    ) -> None:
        if not index_path.startswith("/"):
            raise ValueError(
                "index_path debe comenzar con '/'."
            )

        self._client = client
        self._index_path = index_path

    async def index_document(
        self,
        document: RAGDocumentInput,
    ) -> None:
        """Envía un documento a RAG para su indexación.

        Args:
            document: Documento recuperado desde Object Storage.

        Raises:
            RAGError: Si existe un error de conexión, timeout,
                respuesta HTTP inválida o contrato incompatible.
        """
        data = {
            "document_id": document.document_id,
        }

        files = {
            "file": (
                document.filename,
                document.content,
                (
                    document.content_type
                    or "application/octet-stream"
                ),
            ),
        }

        try:
            response = await self._client.post(
                self._index_path,
                data=data,
                files=files,
            )

            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise RAGError(
                "La solicitud de indexación a RAG "
                f"superó el tiempo permitido para "
                f"{document.document_id}."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise RAGError(
                "RAG rechazó la indexación del documento "
                f"{document.document_id} con estado HTTP "
                f"{exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise RAGError(
                "No fue posible conectar con RAG para indexar "
                f"el documento {document.document_id}."
            ) from exc

        try:
            payload = _RAGIndexHTTPResponse.model_validate(
                response.json()
            )

        except (
            ValueError,
            ValidationError,
        ) as exc:
            raise RAGError(
                "RAG devolvió una respuesta de indexación inválida "
                f"para el documento {document.document_id}."
            ) from exc

        if payload.document_id != document.document_id:
            raise RAGError(
                "RAG devolvió un document_id diferente al enviado. "
                f"Esperado: {document.document_id}. "
                f"Recibido: {payload.document_id}."
            )