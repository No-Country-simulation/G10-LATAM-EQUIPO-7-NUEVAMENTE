"""Persistencia del paquete educativo generado en Object Storage."""

import json

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_educational_package import (
    GeneratedEducationalPackage,
)
from app.domain.generated_format import (
    GeneratedFormat,
)
from app.ports.document_repository_port import (
    DocumentRepositoryError,
    DocumentRepositoryPort,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryError,
    GeneratedFormatRepositoryPort,
)
from app.ports.object_storage_port import (
    ObjectStorageError,
    ObjectStoragePort,
)


class GeneratedPackageError(Exception):
    """Error general durante la construcción o persistencia del paquete."""


class GeneratedPackageDataError(
    GeneratedPackageError
):
    """Los datos persistidos no permiten construir un paquete canónico."""


class GeneratedPackageStorageError(
    GeneratedPackageError
):
    """No fue posible almacenar el paquete educativo en Object Storage."""


class GeneratedPackageStorageService:
    """Construye y persiste el snapshot educativo vigente de un documento.

    El servicio conserva un único objeto JSON canónico por documento:

    ``documents/{document_id}/generated/content.json``

    Cada nueva generación o regeneración terminal reemplaza ese objeto con
    un snapshot reconstruido desde la persistencia de BackendAPI.

    Política de selección por formato:
    - ignora intentos ``processing``;
    - si existe al menos un ``success``, conserva el éxito más reciente;
    - si nunca hubo éxito, conserva el intento terminal más reciente.

    De esta forma una regeneración fallida nunca elimina de OCI un contenido
    exitoso anterior, y regenerar un único formato no elimina el otro formato
    vigente del documento.
    """

    _JSON_CONTENT_TYPE = "application/json"

    def __init__(
        self,
        *,
        document_repository: DocumentRepositoryPort,
        generated_format_repository: (
            GeneratedFormatRepositoryPort
        ),
        object_storage: ObjectStoragePort,
    ) -> None:
        self._document_repository = (
            document_repository
        )
        self._generated_format_repository = (
            generated_format_repository
        )
        self._object_storage = object_storage

    def persist_current_package(
        self,
        document_id: str,
    ) -> str:
        """Reconstruye y persiste el paquete educativo vigente.

        Args:
            document_id: Documento cuyo snapshot debe persistirse.

        Returns:
            Nombre lógico del objeto escrito en Object Storage.

        Raises:
            GeneratedPackageDataError:
                Si el documento no existe, no tiene metadata pedagógica,
                no existen resultados terminales o falla la lectura de
                persistencia.
            GeneratedPackageStorageError:
                Si Object Storage rechaza la escritura.
        """
        try:
            document = (
                self._document_repository.find_by_id(
                    document_id
                )
            )

            history = (
                self._generated_format_repository
                .find_by_document_id(
                    document_id
                )
            )

        except (
            DocumentRepositoryError,
            GeneratedFormatRepositoryError,
        ) as exc:
            raise GeneratedPackageDataError(
                "No fue posible consultar los datos requeridos "
                f"para construir el paquete de {document_id}."
            ) from exc

        if document is None:
            raise GeneratedPackageDataError(
                f"No existe el documento {document_id}."
            )

        if document.learning_metadata is None:
            raise GeneratedPackageDataError(
                "El documento no tiene metadatos pedagógicos "
                "disponibles para construir el paquete educativo."
            )

        selected_formats = (
            self._select_stable_formats(
                history
            )
        )

        if not selected_formats:
            raise GeneratedPackageDataError(
                "No existen formatos terminales disponibles "
                f"para construir el paquete de {document_id}."
            )

        package = GeneratedEducationalPackage(
            document_id=document_id,
            learning_metadata=(
                document.learning_metadata
            ),
            formats=selected_formats,
        )

        payload = json.dumps(
            package.to_dict(),
            ensure_ascii=False,
            indent=2,
        ).encode(
            "utf-8"
        )

        object_name = (
            self.build_object_name(
                document_id
            )
        )

        try:
            self._object_storage.upload_bytes(
                content=payload,
                object_name=object_name,
                content_type=(
                    self._JSON_CONTENT_TYPE
                ),
            )

        except ObjectStorageError as exc:
            raise GeneratedPackageStorageError(
                "No fue posible persistir el paquete educativo "
                f"del documento {document_id} en Object Storage."
            ) from exc

        return object_name

    @classmethod
    def _select_stable_formats(
        cls,
        history: list[
            GeneratedFormat
        ],
    ) -> tuple[
        GeneratedFormat,
        ...,
    ]:
        """Selecciona un snapshot terminal estable por tipo de formato."""
        selected: list[
            GeneratedFormat
        ] = []

        for format_type in GeneratedFormatType:
            terminal_candidates = [
                generated_format
                for generated_format in history
                if (
                    generated_format.format_type
                    == format_type
                    and generated_format.status
                    != GeneratedFormatStatus.PROCESSING
                )
            ]

            if not terminal_candidates:
                continue

            successful_candidates = [
                generated_format
                for generated_format
                in terminal_candidates
                if (
                    generated_format.status
                    == GeneratedFormatStatus.SUCCESS
                )
            ]

            candidates = (
                successful_candidates
                if successful_candidates
                else terminal_candidates
            )

            selected.append(
                max(
                    candidates,
                    key=cls._history_order_key,
                )
            )

        return tuple(
            selected
        )

    @staticmethod
    def _history_order_key(
        generated_format: GeneratedFormat,
    ) -> tuple[object, ...]:
        """Orden estable para resolver el resultado más reciente."""
        return (
            generated_format.created_at,
            generated_format.updated_at,
            generated_format.format_id,
        )

    @staticmethod
    def build_object_name(
        document_id: str,
    ) -> str:
        """Construye la ruta canónica del JSON dentro del mismo bucket."""
        if not document_id.strip():
            raise ValueError(
                "document_id no puede estar vacío."
            )

        return (
            f"documents/{document_id}/"
            "generated/content.json"
        )
