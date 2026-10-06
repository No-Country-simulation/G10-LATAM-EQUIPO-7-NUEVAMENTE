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

    BackendAPI separa explícitamente dos etapas del flujo:

    1. indexación síncrona del documento;
    2. generación de formatos, ejecutable posteriormente en segundo plano.

    Esta separación permite que ``POST /documents`` confirme al cliente
    que el documento quedó correctamente indexado sin mantener abierta
    la petición HTTP mientras Agentes genera Quiz y Flashcards.

    El servicio no implementa acceso directo a OCI, RAG, Agentes ni
    persistencia. Estas responsabilidades permanecen delegadas a los
    servicios especializados.
    """

    _DEFAULT_FORMATS = (
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

    async def ensure_document_indexed(
        self,
        document_id: str,
    ) -> None:
        """Garantiza que un documento esté disponible en RAG.

        Un documento almacenado se indexa de forma síncrona. Una
        indexación previamente fallida puede reintentarse. Si el
        documento ya se encuentra indexado no se repite el trabajo.

        Args:
            document_id: Identificador canónico del documento.

        Raises:
            DocumentNotFoundError:
                Si el documento no existe.
            AdaptationDocumentStateError:
                Si el estado actual no permite iniciar la indexación.
            RAGIntegrationError:
                Si RAG no puede completar la indexación.
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
            return

        if (
            document.status
            == DocumentStatus.INDEXED
        ):
            return

        raise AdaptationDocumentStateError(
            f"El documento {document_id} está en estado "
            f"{document.status.value} y no puede iniciar "
            "la indexación para adaptación."
        )

    async def generate_default_formats(
        self,
        *,
        document_id: str,
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[GeneratedFormat]:
        """Genera Quiz y Flashcards para un documento indexado.

        Esta operación está diseñada para ejecutarse después de la
        indexación y puede ser programada como tarea en segundo plano.

        Args:
            document_id: Identificador canónico del documento.
            profile: Perfil educativo del destinatario.
            niche: Área temática o contexto de aplicación.
            detail_level: Nivel de detalle requerido.
            learning_objective: Objetivo de aprendizaje opcional.

        Returns:
            Formatos generados y persistidos.

        Raises:
            FormatGenerationDocumentNotFoundError:
                Si el documento no existe.
            DocumentNotReadyForGenerationError:
                Si el documento no está indexado.
            FormatGenerationIntegrationError:
                Si falla la integración con Agentes.
            FormatGenerationContractError:
                Si Agentes incumple el contrato de generación.
        """
        return await (
            self._format_generation_service
            .generate_formats(
                document_id=document_id,
                formats=self._DEFAULT_FORMATS,
                profile=profile,
                niche=niche,
                detail_level=detail_level,
                learning_objective=learning_objective,
            )
        )