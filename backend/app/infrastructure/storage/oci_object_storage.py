"""Implementación de ObjectStoragePort utilizando OCI Object Storage."""

from pathlib import Path
from typing import Any

import oci

from app.ports.object_storage import (
    ObjectStorageConfigurationError,
    ObjectStorageError,
)


class OCIObjectStorage:
    """Gestiona objetos persistentes en un bucket de OCI."""

    def __init__(
        self,
        *,
        namespace: str,
        bucket_name: str,
        region: str = "",
        config_file: str = "~/.oci/config",
        config_profile: str = "DEFAULT",
        client: Any | None = None,
    ) -> None:
        self._namespace = namespace
        self._bucket_name = bucket_name
        self._region = region
        self._config_file = config_file
        self._config_profile = config_profile
        self._client = client

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        """Carga un archivo local en el bucket configurado."""
        self._validate_target()

        try:
            with local_path.open("rb") as file_stream:
                self._get_client().put_object(
                    namespace_name=self._namespace,
                    bucket_name=self._bucket_name,
                    object_name=object_name,
                    put_object_body=file_stream,
                    content_type=content_type,
                )
        except ObjectStorageConfigurationError:
            raise
        except Exception as exc:
            raise ObjectStorageError(
                f"No fue posible cargar el objeto {object_name} en OCI."
            ) from exc

    def download_file(
        self,
        object_name: str,
    ) -> bytes:
        """Descarga un objeto almacenado en OCI."""
        self._validate_target()

        try:
            response = self._get_client().get_object(
                namespace_name=self._namespace,
                bucket_name=self._bucket_name,
                object_name=object_name,
            )

            return response.data.content
        except ObjectStorageConfigurationError:
            raise
        except Exception as exc:
            raise ObjectStorageError(
                f"No fue posible descargar el objeto {object_name}."
            ) from exc

    def delete_object(
        self,
        object_name: str,
    ) -> None:
        """Elimina un objeto del bucket configurado."""
        self._validate_target()

        try:
            self._get_client().delete_object(
                namespace_name=self._namespace,
                bucket_name=self._bucket_name,
                object_name=object_name,
            )
        except ObjectStorageConfigurationError:
            raise
        except Exception as exc:
            raise ObjectStorageError(
                f"No fue posible eliminar el objeto {object_name}."
            ) from exc

    def _validate_target(self) -> None:
        """Valida que namespace y bucket estén configurados."""
        if not self._namespace.strip():
            raise ObjectStorageConfigurationError(
                "OCI_NAMESPACE no está configurado."
            )

        if not self._bucket_name.strip():
            raise ObjectStorageConfigurationError(
                "OCI_BUCKET_NAME no está configurado."
            )

    def _get_client(self) -> Any:
        """Crea de forma diferida el cliente de OCI."""
        if self._client is not None:
            return self._client

        try:
            config = oci.config.from_file(
                file_location=str(
                    Path(self._config_file).expanduser()
                ),
                profile_name=self._config_profile,
            )

            if self._region.strip():
                config["region"] = self._region

            self._client = (
                oci.object_storage.ObjectStorageClient(
                    config
                )
            )
        except Exception as exc:
            raise ObjectStorageConfigurationError(
                "No fue posible inicializar OCI Object Storage."
            ) from exc

        return self._client