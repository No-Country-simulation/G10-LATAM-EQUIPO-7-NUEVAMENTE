"""Pruebas unitarias del adaptador OCI Object Storage."""

from types import SimpleNamespace

import pytest

from app.infrastructure.storage.oci_object_storage_adapter import (
    OCIObjectStorageAdapter,
)
from app.ports.object_storage_port import (
    ObjectStorageError,
)


class FakeOCIClient:
    """Cliente OCI controlado para verificar lectura y escritura."""

    def __init__(
        self,
        content: bytes = b"",
    ) -> None:
        self._content = content

        self.last_get_request: dict[
            str,
            str,
        ] | None = None

        self.last_put_request: dict[
            str,
            object,
        ] | None = None

    def get_object(
        self,
        *,
        namespace_name: str,
        bucket_name: str,
        object_name: str,
    ) -> SimpleNamespace:
        self.last_get_request = {
            "namespace_name": namespace_name,
            "bucket_name": bucket_name,
            "object_name": object_name,
        }

        return SimpleNamespace(
            data=SimpleNamespace(
                content=self._content
            )
        )

    def put_object(
        self,
        *,
        namespace_name: str,
        bucket_name: str,
        object_name: str,
        put_object_body,
        content_type: str | None = None,
    ) -> None:
        self.last_put_request = {
            "namespace_name": namespace_name,
            "bucket_name": bucket_name,
            "object_name": object_name,
            "put_object_body": put_object_body,
            "content_type": content_type,
        }


class FailingGetOCIClient:
    """Cliente OCI que simula un error durante get_object."""

    def get_object(
        self,
        *,
        namespace_name: str,
        bucket_name: str,
        object_name: str,
    ) -> None:
        raise RuntimeError(
            "Fallo simulado del SDK de OCI."
        )


class FailingPutOCIClient:
    """Cliente OCI que simula un error durante put_object."""

    def put_object(
        self,
        *,
        namespace_name: str,
        bucket_name: str,
        object_name: str,
        put_object_body,
        content_type: str | None = None,
    ) -> None:
        raise RuntimeError(
            "Fallo simulado del SDK de OCI."
        )


def test_upload_bytes_puts_content_in_configured_bucket() -> None:
    """Persiste bytes directamente sin crear un archivo temporal."""
    client = FakeOCIClient()

    storage = OCIObjectStorageAdapter(
        namespace="namespace-test",
        bucket_name="bucket-test",
        client=client,
    )

    object_name = (
        "documents/doc_test/generated/content.json"
    )

    content = (
        '{"mensaje":"áéíóú"}'
        .encode()
    )

    storage.upload_bytes(
        content=content,
        object_name=object_name,
        content_type="application/json",
    )

    assert client.last_put_request == {
        "namespace_name": "namespace-test",
        "bucket_name": "bucket-test",
        "object_name": object_name,
        "put_object_body": content,
        "content_type": "application/json",
    }


def test_upload_bytes_wraps_oci_error() -> None:
    """Un fallo del SDK al escribir se traduce al puerto de storage."""
    storage = OCIObjectStorageAdapter(
        namespace="namespace-test",
        bucket_name="bucket-test",
        client=FailingPutOCIClient(),
    )

    object_name = (
        "documents/doc_test/generated/content.json"
    )

    with pytest.raises(
        ObjectStorageError,
        match=(
            "No fue posible cargar el objeto "
            f"{object_name} en OCI."
        ),
    ):
        storage.upload_bytes(
            content=b"{}",
            object_name=object_name,
            content_type="application/json",
        )


def test_download_file_returns_object_content() -> None:
    """Devuelve exactamente los bytes recibidos desde OCI."""
    expected_content = (
        b"contenido almacenado en OCI"
    )

    client = FakeOCIClient(
        expected_content
    )

    storage = OCIObjectStorageAdapter(
        namespace="namespace-test",
        bucket_name="bucket-test",
        client=client,
    )

    object_name = (
        "documents/doc_test/original.pdf"
    )

    content = storage.download_file(
        object_name
    )

    assert content == expected_content

    assert client.last_get_request == {
        "namespace_name": "namespace-test",
        "bucket_name": "bucket-test",
        "object_name": object_name,
    }


def test_download_file_wraps_oci_error() -> None:
    """Un error del SDK se expone mediante ObjectStorageError."""
    storage = OCIObjectStorageAdapter(
        namespace="namespace-test",
        bucket_name="bucket-test",
        client=FailingGetOCIClient(),
    )

    object_name = (
        "documents/doc_test/original.pdf"
    )

    with pytest.raises(
        ObjectStorageError,
        match=(
            "No fue posible descargar el objeto "
            f"{object_name}."
        ),
    ):
        storage.download_file(
            object_name
        )
