"""Pruebas unitarias de la integración con OCI Object Storage."""

from types import SimpleNamespace

import pytest

from app.infrastructure.storage.oci_object_storage import (
    OCIObjectStorage,
)
from app.ports.object_storage import ObjectStorageError


class FakeOCIClient:
    """Cliente OCI controlado para verificar operaciones de lectura."""

    def __init__(self, content: bytes) -> None:
        self._content = content
        self.last_request: dict[str, str] | None = None

    def get_object(
        self,
        *,
        namespace_name: str,
        bucket_name: str,
        object_name: str,
    ) -> SimpleNamespace:
        self.last_request = {
            "namespace_name": namespace_name,
            "bucket_name": bucket_name,
            "object_name": object_name,
        }

        return SimpleNamespace(
            data=SimpleNamespace(
                content=self._content
            )
        )


class FailingOCIClient:
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


def test_download_file_returns_object_content() -> None:
    """Devuelve exactamente los bytes recibidos desde OCI."""
    expected_content = b"contenido almacenado en OCI"

    client = FakeOCIClient(expected_content)

    storage = OCIObjectStorage(
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

    assert client.last_request == {
        "namespace_name": "namespace-test",
        "bucket_name": "bucket-test",
        "object_name": object_name,
    }


def test_download_file_wraps_oci_error() -> None:
    """Un error del SDK se expone mediante ObjectStorageError."""
    storage = OCIObjectStorage(
        namespace="namespace-test",
        bucket_name="bucket-test",
        client=FailingOCIClient(),
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