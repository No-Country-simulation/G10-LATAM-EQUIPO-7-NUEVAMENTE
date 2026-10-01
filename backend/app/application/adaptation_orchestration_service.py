"""Orquestación del flujo de adaptación educativa."""

from app.application.document_service import (
    DocumentService,
)
from app.application.format_generation_service import (
    FormatGenerationService,
)
from app.application.rag_integration_service import (
    RAGIntegrationService,
)
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatType,
)
from app.domain.generated_format import (
    GeneratedFormat,
)


class AdaptationDocumentStateError(Exception):
    """El documento no está en un estado válido para adaptación."""


class AdaptationOrchestrationService:
    """Coordina indexación y generación de formatos educativos.

    Este servicio representa el caso de uso completo de adaptación
    dentro de BackendAPI.

    Sus responsabilidades son:

    1. consultar el estado actual del documento;
    2. indexarlo cuando todavía está almacenado o requiere reintento;
    3. evitar una indexación innecesaria cuando ya está indexado;
    4. solicitar automáticamente Quiz y Flashcards;
    5. devolver los formatos generados y persistidos.

    No implementa acceso directo a OCI, RAG, Agentes ni persistencia.
    Estas responsabilidades permanecen delegadas a los servicios
    especializados.
    """

    _SPRINT_2_FORMATS = (
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    )

    _INDEXABLE_STATUSES = frozenset(
        {
            DocumentStatus.STORED,
            DocumentStatus.INDEXING_FAILED,
        }
    )

    def __init__(
        self,
        *,
        document_service: DocumentService,
        rag_integration_service: RAGIntegrationService,
        format_generation_service: FormatGenerationService,
    ) -> None:
        self._document_service = document_service
        self._rag_integration_service = (
            rag_integration_service
        )
        self._format_generation_service = (
            format_generation_service
        )

    async def adapt_document(
        self,
        *,
        document_id: str,
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[GeneratedFormat]:
        """Ejecuta el flujo de adaptación de un documento.

        Un documento almacenado se indexa antes de generar contenido.
        Una indexación previamente fallida puede reintentarse. Un
        documento ya indexado pasa directamente a generación.

        Sprint 2 genera automáticamente Quiz y Flashcards.

        Args:
            document_id: Identificador canónico del documento.
            profile: Perfil educativo del destinatario.
            niche: Área temática o contexto de aplicación.
            detail_level: Nivel de detalle requerido.
            learning_objective: Objetivo de aprendizaje opcional.

        Returns:
            Formatos generados y persistidos por
            FormatGenerationService.

        Raises:
            DocumentNotFoundError:
                Si el documento no existe.
            AdaptationDocumentStateError:
                Si el estado actual no permite iniciar la adaptación.
            RAGIntegrationError:
                Si falla la indexación.
            FormatGenerationIntegrationError:
                Si falla la integración con Agentes.
            FormatGenerationContractError:
                Si Agentes incumple el contrato de generación.
        """
        document = self._document_service.get_document(
            document_id
        )

        if (
            document.status
            in self._INDEXABLE_STATUSES
        ):
            await (
                self._rag_integration_service
                .index_document(
                    document_id
                )
            )

        elif (
            document.status
            != DocumentStatus.INDEXED
        ):
            raise AdaptationDocumentStateError(
                f"El documento {document_id} está en estado "
                f"{document.status.value} y no puede iniciar "
                "la adaptación."
            )

        return await (
            self._format_generation_service
            .generate_formats(
                document_id=document_id,
                formats=self._SPRINT_2_FORMATS,
                profile=profile,
                niche=niche,
                detail_level=detail_level,
                learning_objective=learning_objective,
            )
        )