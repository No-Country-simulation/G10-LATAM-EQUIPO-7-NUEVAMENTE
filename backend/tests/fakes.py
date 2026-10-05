"""Dobles de prueba compartidos por BackendAPI."""

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from app.application.document_service import (
    DocumentService,
)
from app.domain.document import Document
from app.domain.enums import (
    DocumentStatus,
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    FlashcardItem,
    FlashcardsContent,
    QuizContent,
    QuizQuestion,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.ports.generated_format_repository_port import (
    GeneratedFormatRepositoryPort,
)
from app.ports.object_storage_port import (
    ObjectStorageError,
)
from app.ports.rag_port import (
    RAGDocumentInput,
    RAGError,
)


class FakeDocumentRepository:
    """Repositorio de documentos en memoria para pruebas."""

    def __init__(self) -> None:
        self.documents: dict[
            str,
            Document,
        ] = {}

    def create(
        self,
        document: Document,
    ) -> Document:
        self.documents[
            document.document_id
        ] = deepcopy(
            document
        )

        return document

    def find_by_id(
        self,
        document_id: str,
    ) -> Document | None:
        document = self.documents.get(
            document_id
        )

        if document is None:
            return None

        return deepcopy(
            document
        )

    def find_by_sha256(
        self,
        sha256: str,
    ) -> Document | None:
        document = next(
            (
                document
                for document
                in self.documents.values()
                if document.sha256 == sha256
            ),
            None,
        )

        if document is None:
            return None

        return deepcopy(
            document
        )

    def find_all(
        self,
    ) -> list[Document]:
        """Retorna documentos desde el más reciente."""
        documents = sorted(
            self.documents.values(),
            key=lambda document: document.created_at,
            reverse=True,
        )

        return [
            deepcopy(
                document
            )
            for document in documents
        ]

    def update(
        self,
        document: Document,
    ) -> Document:
        self.documents[
            document.document_id
        ] = deepcopy(
            document
        )

        return document


class FakeObjectStorage:
    """Almacenamiento en memoria para pruebas."""

    def __init__(self) -> None:
        self.uploaded_objects: dict[
            str,
            bytes,
        ] = {}

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        self.uploaded_objects[
            object_name
        ] = local_path.read_bytes()

    def download_file(
        self,
        object_name: str,
    ) -> bytes:
        return self.uploaded_objects[
            object_name
        ]

    def delete_object(
        self,
        object_name: str,
    ) -> None:
        self.uploaded_objects.pop(
            object_name,
            None,
        )


class FailingObjectStorage(
    FakeObjectStorage
):
    """Simula un fallo durante la escritura en Object Storage."""

    def upload_file(
        self,
        *,
        local_path: Path,
        object_name: str,
        content_type: str | None = None,
    ) -> None:
        raise ObjectStorageError(
            "Fallo simulado de Object Storage."
        )


class FailingDownloadObjectStorage(
    FakeObjectStorage
):
    """Simula un fallo durante la lectura desde Object Storage."""

    def download_file(
        self,
        object_name: str,
    ) -> bytes:
        raise ObjectStorageError(
            "Fallo simulado al recuperar "
            f"{object_name}."
        )


class FailingDeleteObjectStorage(
    FakeObjectStorage
):
    """Simula un fallo durante una compensación de Object Storage."""

    def delete_object(
        self,
        object_name: str,
    ) -> None:
        raise ObjectStorageError(
            "Fallo simulado al eliminar "
            f"{object_name}."
        )


class FakeRAGPort:
    """RAG falso que registra los documentos recibidos."""

    def __init__(self) -> None:
        self.received_documents: list[
            RAGDocumentInput
        ] = []

    async def index_document(
        self,
        document: RAGDocumentInput,
    ) -> None:
        self.received_documents.append(
            document
        )


class FailingRAGPort:
    """RAG falso que simula un fallo al recibir documentos."""

    async def index_document(
        self,
        document: RAGDocumentInput,
    ) -> None:
        raise RAGError(
            "Fallo simulado del módulo RAG."
        )


class FakeAdaptationOrchestrationService:
    """Simula la adaptación completa utilizada por las pruebas HTTP.

    El fake reproduce los efectos observables relevantes para BackendAPI:

    - registra el contexto pedagógico recibido;
    - lleva el documento de STORED a INDEXED;
    - genera Quiz y Flashcards válidos;
    - persiste ambos formatos.

    No ejecuta llamadas HTTP hacia RAG ni Agentes.
    """

    def __init__(
        self,
        *,
        document_service: DocumentService,
        generated_format_repository: GeneratedFormatRepositoryPort,
    ) -> None:
        self._document_service = document_service
        self._generated_format_repository = (
            generated_format_repository
        )

        self.requests: list[
            dict[str, object]
        ] = []

    async def adapt_document(
        self,
        *,
        document_id: str,
        profile: str,
        niche: str,
        detail_level: str,
        learning_objective: str | None = None,
    ) -> list[GeneratedFormat]:
        """Simula indexación y generación exitosa de ambos formatos."""
        self.requests.append(
            {
                "document_id": document_id,
                "profile": profile,
                "niche": niche,
                "detail_level": detail_level,
                "learning_objective": learning_objective,
            }
        )

        document = (
            self._document_service.get_document(
                document_id
            )
        )

        if document.status in {
            DocumentStatus.STORED,
            DocumentStatus.INDEXING_FAILED,
        }:
            self._document_service.start_indexing(
                document_id
            )
            self._document_service.complete_indexing(
                document_id
            )

        elif (
            document.status
            != DocumentStatus.INDEXED
        ):
            raise RuntimeError(
                "El fake de adaptación recibió un documento "
                f"en estado inesperado: {document.status.value}."
            )

        context = GenerationContext(
            profile=profile,
            niche=niche,
            detail_level=detail_level,
            learning_objective=learning_objective,
        )

        evidence = (
            ChunkEvidence(
                chunk_id=f"{document_id}_chunk_1",
                document_id=document_id,
                rank=1,
                score=0.95,
                text=(
                    "Contenido recuperado para "
                    "la adaptación educativa."
                ),
            ),
        )

        generated_formats = [
            GeneratedFormat(
                format_id=(
                    f"fmt_{uuid4().hex}"
                ),
                document_id=document_id,
                format_type=(
                    GeneratedFormatType.QUIZ
                ),
                status=(
                    GeneratedFormatStatus.SUCCESS
                ),
                generation_context=context,
                content=QuizContent(
                    title="Quiz de prueba",
                    instructions=(
                        "Seleccione la respuesta correcta."
                    ),
                    questions=(
                        QuizQuestion(
                            question_id=(
                                f"q_{uuid4().hex[:8]}"
                            ),
                            question=(
                                "¿Cuál es el concepto "
                                "principal?"
                            ),
                            options=(
                                "Respuesta correcta",
                                "Respuesta incorrecta",
                            ),
                            correct_answer=(
                                "Respuesta correcta"
                            ),
                            explanation=(
                                "Explicación basada en "
                                "el documento."
                            ),
                        ),
                    ),
                ),
                chunks_used=evidence,
            ),
            GeneratedFormat(
                format_id=(
                    f"fmt_{uuid4().hex}"
                ),
                document_id=document_id,
                format_type=(
                    GeneratedFormatType.FLASHCARDS
                ),
                status=(
                    GeneratedFormatStatus.SUCCESS
                ),
                generation_context=context,
                content=FlashcardsContent(
                    title="Flashcards de prueba",
                    instructions=(
                        "Revise cada tarjeta."
                    ),
                    cards=(
                        FlashcardItem(
                            card_id=(
                                f"card_{uuid4().hex[:8]}"
                            ),
                            front="Concepto principal",
                            back=(
                                "Definición basada "
                                "en el documento."
                            ),
                        ),
                    ),
                ),
                chunks_used=evidence,
            ),
        ]

        return [
            self._generated_format_repository.create(
                generated_format
            )
            for generated_format
            in generated_formats
        ]