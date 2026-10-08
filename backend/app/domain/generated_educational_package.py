"""Contrato canónico del paquete educativo persistido en OCI."""

from dataclasses import dataclass

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
)
from app.domain.learning_metadata import (
    LearningMetadata,
)


@dataclass(frozen=True, slots=True)
class GeneratedEducationalPackage:
    """Snapshot estable del contenido educativo vigente de un documento.

    El paquete contiene únicamente datos que BackendAPI considera canónicos
    para consumo y persistencia de contenido educativo. Las evidencias RAG,
    el contexto técnico de generación y la evaluación de Data/IA permanecen
    fuera de este contrato.

    Attributes:
        document_id: Identificador canónico del documento.
        learning_metadata: Metadatos pedagógicos vigentes.
        formats: Un formato terminal vigente por tipo soportado.
    """

    document_id: str
    learning_metadata: LearningMetadata
    formats: tuple[
        GeneratedFormat,
        ...,
    ]

    def __post_init__(self) -> None:
        """Valida las invariantes del paquete persistible."""
        if not self.document_id.strip():
            raise ValueError(
                "document_id no puede estar vacío."
            )

        if not self.formats:
            raise ValueError(
                "El paquete educativo requiere al menos un formato terminal."
            )

        format_types = [
            generated_format.format_type
            for generated_format in self.formats
        ]

        if len(format_types) != len(set(format_types)):
            raise ValueError(
                "El paquete educativo no puede repetir tipos de formato."
            )

        for generated_format in self.formats:
            if (
                generated_format.document_id
                != self.document_id
            ):
                raise ValueError(
                    "Todos los formatos del paquete deben pertenecer "
                    "al mismo document_id."
                )

            if (
                generated_format.status
                == GeneratedFormatStatus.PROCESSING
            ):
                raise ValueError(
                    "El paquete educativo no puede persistir formatos "
                    "en processing."
                )

    def to_dict(self) -> dict[str, object]:
        """Serializa el paquete al contrato JSON canónico de OCI."""
        return {
            "document_id": self.document_id,
            "learning_metadata": (
                self.learning_metadata.to_dict()
            ),
            "formats": {
                generated_format.format_type.value: (
                    self._serialize_format(
                        generated_format
                    )
                )
                for generated_format in self.formats
            },
        }

    @staticmethod
    def _serialize_format(
        generated_format: GeneratedFormat,
    ) -> dict[str, object]:
        """Serializa un formato terminal sin evidencias ni contexto interno."""
        content = generated_format.content

        return {
            "format_id": generated_format.format_id,
            "status": generated_format.status.value,
            "content": (
                content.to_dict()
                if content is not None
                else None
            ),
            "error_message": (
                generated_format.error_message
            ),
        }

    def get_format(
        self,
        format_type: GeneratedFormatType,
    ) -> GeneratedFormat | None:
        """Obtiene un formato del snapshot por su tipo."""
        return next(
            (
                generated_format
                for generated_format in self.formats
                if (
                    generated_format.format_type
                    == format_type
                )
            ),
            None,
        )
