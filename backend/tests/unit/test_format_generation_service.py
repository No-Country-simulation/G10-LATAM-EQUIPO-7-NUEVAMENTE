"""Pruebas unitarias de FormatGenerationService."""

import asyncio
import hashlib

import pytest

from app.application.format_generation_service import (
    DocumentNotReadyForGenerationError,
    FormatGenerationContractError,
    FormatGenerationDocumentNotFoundError,
    FormatGenerationIntegrationError,
    FormatGenerationService,
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
)
from app.ports.agents_port import (
    AgentGeneratedFormatResult,
    AgentGenerationInput,
    AgentGenerationResult,
    AgentsError,
)


class FakeDocumentRepository:
    """Repositorio mínimo de documentos para pruebas."""

    def __init__(
        self,
        document: Document | None,
    ) -> None:
        self.document = document

    def create(
        self,
        document: Document,
    ) -> Document:
        self.document = document
        return document

    def find_by_id(
        self,
        document_id: str,
    ) -> Document | None:
        if (
            self.document is not None
            and self.document.document_id
            == document_id
        ):
            return self.document

        return None

    def find_by_sha256(
        self,
        sha256: str,
    ) -> Document | None:
        if (
            self.document is not None
            and self.document.sha256
            == sha256
        ):
            return self.document

        return None

    def update(
        self,
        document: Document,
    ) -> Document:
        self.document = document
        return document


class FakeGeneratedFormatRepository:
    """Repositorio en memoria para generaciones."""

    def __init__(self) -> None:
        self.formats = []

    def create(
        self,
        generated_format,
    ):
        self.formats.append(
            generated_format
        )
        return generated_format

    def find_by_id(
        self,
        format_id: str,
    ):
        return next(
            (
                generated_format
                for generated_format
                in self.formats
                if generated_format.format_id
                == format_id
            ),
            None,
        )

    def find_by_document_id(
        self,
        document_id: str,
    ):
        return [
            generated_format
            for generated_format
            in self.formats
            if generated_format.document_id
            == document_id
        ]


class FakeAgents:
    """Agentes falso que devuelve Quiz y Flashcards válidos."""

    def __init__(self) -> None:
        self.last_request: (
            AgentGenerationInput | None
        ) = None

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
        self.last_request = request

        quiz = AgentGeneratedFormatResult(
            format_type=GeneratedFormatType.QUIZ,
            status=GeneratedFormatStatus.SUCCESS,
            content=QuizContent(
                title="Quiz de prueba",
                instructions="Seleccione la respuesta correcta.",
                questions=(
                    QuizQuestion(
                        question_id="q1",
                        question="¿Qué es un microservicio?",
                        options=(
                            "Servicio independiente",
                            "Base de datos",
                        ),
                        correct_answer=(
                            "Servicio independiente"
                        ),
                        explanation=(
                            "Es una unidad desplegable independiente."
                        ),
                    ),
                ),
            ),
            chunks_used=(
                ChunkEvidence(
                    chunk_id="chunk_1",
                    document_id=request.document_id,
                    rank=1,
                    score=0.93,
                    text=(
                        "Los microservicios son servicios "
                        "desplegables independientemente."
                    ),
                ),
            ),
        )

        flashcards = AgentGeneratedFormatResult(
            format_type=(
                GeneratedFormatType.FLASHCARDS
            ),
            status=GeneratedFormatStatus.SUCCESS,
            content=FlashcardsContent(
                title="Flashcards de prueba",
                instructions="Revise cada tarjeta.",
                cards=(
                    FlashcardItem(
                        card_id="card_1",
                        front="Microservicio",
                        back=(
                            "Servicio pequeño e independiente."
                        ),
                    ),
                ),
            ),
            chunks_used=(
                ChunkEvidence(
                    chunk_id="chunk_1",
                    document_id=request.document_id,
                    rank=1,
                    score=0.93,
                    text=(
                        "Los microservicios son servicios "
                        "desplegables independientemente."
                    ),
                ),
            ),
        )

        results_by_format = {
            GeneratedFormatType.QUIZ: quiz,
            GeneratedFormatType.FLASHCARDS: (
                flashcards
            ),
        }

        return AgentGenerationResult(
            document_id=request.document_id,
            results=tuple(
                results_by_format[
                    format_type
                ]
                for format_type
                in request.formats
            ),
        )


class FailingAgents:
    """Agentes falso que simula un fallo externo."""

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
        raise AgentsError(
            "Fallo simulado de Agentes."
        )


class WrongDocumentAgents(
    FakeAgents
):
    """Agentes falso que responde por otro documento."""

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
        result = await super().generate_formats(
            request
        )

        return AgentGenerationResult(
            document_id="doc_otro",
            results=result.results,
        )


class MissingFormatAgents(
    FakeAgents
):
    """Agentes falso que omite uno de los formatos solicitados."""

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
        result = await super().generate_formats(
            request
        )

        return AgentGenerationResult(
            document_id=request.document_id,
            results=(
                result.results[0],
            ),
        )


def build_document(
    status: DocumentStatus,
) -> Document:
    """Construye un documento para pruebas."""
    content = b"contenido"

    return Document(
        document_id="doc_123",
        original_filename="manual.pdf",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="application/pdf",
        size_bytes=len(content),
        status=status,
    )


def test_generate_formats_persists_quiz_and_flashcards() -> None:
    """Genera y persiste ambos formatos con contexto y evidencias."""
    document_repository = FakeDocumentRepository(
        build_document(
            DocumentStatus.INDEXED
        )
    )

    generated_repository = (
        FakeGeneratedFormatRepository()
    )

    agents = FakeAgents()

    service = FormatGenerationService(
        document_repository=(
            document_repository
        ),
        generated_format_repository=(
            generated_repository
        ),
        agents=agents,
    )

    result = asyncio.run(
        service.generate_formats(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
                GeneratedFormatType.FLASHCARDS,
            ),
            profile="beginner",
            niche="technology",
            detail_level="detailed",
            learning_objective=(
                "Comprender microservicios."
            ),
        )
    )

    assert len(result) == 2
    assert len(
        generated_repository.formats
    ) == 2

    assert agents.last_request is not None

    assert (
        agents.last_request
        .generation_context
        .detail_level
        == "detailed"
    )

    quiz = result[0]

    assert (
        quiz.format_type
        == GeneratedFormatType.QUIZ
    )

    assert isinstance(
        quiz.content,
        QuizContent,
    )

    assert (
        quiz.chunks_used[0].text
        == (
            "Los microservicios son servicios "
            "desplegables independientemente."
        )
    )


def test_generate_formats_rejects_unknown_document() -> None:
    """No invoca Agentes si el documento no existe."""
    service = FormatGenerationService(
        document_repository=(
            FakeDocumentRepository(
                None
            )
        ),
        generated_format_repository=(
            FakeGeneratedFormatRepository()
        ),
        agents=FakeAgents(),
    )

    with pytest.raises(
        FormatGenerationDocumentNotFoundError,
    ):
        asyncio.run(
            service.generate_formats(
                document_id="doc_inexistente",
                formats=(
                    GeneratedFormatType.QUIZ,
                ),
                profile="beginner",
                niche="general",
                detail_level="standard",
            )
        )


def test_generate_formats_requires_indexed_document() -> None:
    """Solo permite generar formatos para documentos indexados."""
    service = FormatGenerationService(
        document_repository=(
            FakeDocumentRepository(
                build_document(
                    DocumentStatus.STORED
                )
            )
        ),
        generated_format_repository=(
            FakeGeneratedFormatRepository()
        ),
        agents=FakeAgents(),
    )

    with pytest.raises(
        DocumentNotReadyForGenerationError,
    ):
        asyncio.run(
            service.generate_formats(
                document_id="doc_123",
                formats=(
                    GeneratedFormatType.QUIZ,
                ),
                profile="beginner",
                niche="general",
                detail_level="standard",
            )
        )


def test_generate_formats_translates_agents_error() -> None:
    """Traduce fallos externos de Agentes."""
    service = FormatGenerationService(
        document_repository=(
            FakeDocumentRepository(
                build_document(
                    DocumentStatus.INDEXED
                )
            )
        ),
        generated_format_repository=(
            FakeGeneratedFormatRepository()
        ),
        agents=FailingAgents(),
    )

    with pytest.raises(
        FormatGenerationIntegrationError,
        match="Agentes no pudo generar",
    ):
        asyncio.run(
            service.generate_formats(
                document_id="doc_123",
                formats=(
                    GeneratedFormatType.QUIZ,
                ),
                profile="beginner",
                niche="general",
                detail_level="standard",
            )
        )


def test_generate_formats_rejects_wrong_document_id() -> None:
    """No persiste resultados asociados a otro documento."""
    repository = (
        FakeGeneratedFormatRepository()
    )

    service = FormatGenerationService(
        document_repository=(
            FakeDocumentRepository(
                build_document(
                    DocumentStatus.INDEXED
                )
            )
        ),
        generated_format_repository=repository,
        agents=WrongDocumentAgents(),
    )

    with pytest.raises(
        FormatGenerationContractError,
        match="document_id diferente",
    ):
        asyncio.run(
            service.generate_formats(
                document_id="doc_123",
                formats=(
                    GeneratedFormatType.QUIZ,
                ),
                profile="beginner",
                niche="general",
                detail_level="standard",
            )
        )

    assert repository.formats == []


def test_generate_formats_requires_all_requested_results() -> None:
    """Rechaza una respuesta incompleta antes de persistir."""
    repository = (
        FakeGeneratedFormatRepository()
    )

    service = FormatGenerationService(
        document_repository=(
            FakeDocumentRepository(
                build_document(
                    DocumentStatus.INDEXED
                )
            )
        ),
        generated_format_repository=repository,
        agents=MissingFormatAgents(),
    )

    with pytest.raises(
        FormatGenerationContractError,
        match=(
            "no coinciden con los solicitados"
        ),
    ):
        asyncio.run(
            service.generate_formats(
                document_id="doc_123",
                formats=(
                    GeneratedFormatType.QUIZ,
                    GeneratedFormatType.FLASHCARDS,
                ),
                profile="beginner",
                niche="general",
                detail_level="standard",
            )
        )

    assert repository.formats == []


def test_generate_formats_rejects_duplicate_request() -> None:
    """No permite solicitar dos veces el mismo formato."""
    service = FormatGenerationService(
        document_repository=(
            FakeDocumentRepository(
                build_document(
                    DocumentStatus.INDEXED
                )
            )
        ),
        generated_format_repository=(
            FakeGeneratedFormatRepository()
        ),
        agents=FakeAgents(),
    )

    with pytest.raises(
        ValueError,
        match="formatos duplicados",
    ):
        asyncio.run(
            service.generate_formats(
                document_id="doc_123",
                formats=(
                    GeneratedFormatType.QUIZ,
                    GeneratedFormatType.QUIZ,
                ),
                profile="beginner",
                niche="general",
                detail_level="standard",
            )
        )