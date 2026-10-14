"""Pruebas unitarias de FormatGenerationService."""

import asyncio
import hashlib

import pytest

from app.application.format_generation_service import (
    DocumentNotReadyForGenerationError,
    FormatGenerationAttemptStateError,
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
    GeneratedFormat,
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

    def update(
        self,
        generated_format,
    ):
        """Actualiza una generación existente en memoria."""
        for index, stored_format in enumerate(
            self.formats
        ):
            if (
                stored_format.format_id
                == generated_format.format_id
            ):
                self.formats[index] = (
                    generated_format
                )
                return generated_format

        raise RuntimeError(
            "No existe el formato "
            f"{generated_format.format_id}."
        )

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


class PartialFailureAgents(
    FakeAgents
):
    """Agentes falso que simula un 207: un formato ok y otro falló.

    Representa lo que el adapter HTTP ya corregido devuelve ante un
    éxito parcial real de Agentes: no lanza AgentsError, y cada
    resultado conserva su propio status y su propia causa.
    """

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
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
                        correct_answer="Servicio independiente",
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
                    text="Evidencia utilizada para el quiz.",
                ),
            ),
        )

        flashcards = AgentGeneratedFormatResult(
            format_type=GeneratedFormatType.FLASHCARDS,
            status=GeneratedFormatStatus.FAILED,
            content=None,
            chunks_used=(),
            error_message=(
                "Cuota de Gemini agotada. Intenta nuevamente más tarde."
            ),
        )

        return AgentGenerationResult(
            document_id=request.document_id,
            results=(quiz, flashcards),
        )


class GlobalFailureAgents(
    FakeAgents
):
    """Agentes falso que simula un fallo global (429/503/etc.) ya interpretado.

    Representa lo que el adapter HTTP ya corregido devuelve cuando TODO
    falló: no lanza AgentsError, y cada formato conserva su propia
    causa real en lugar de un mensaje genérico compartido.
    """

    async def generate_formats(
        self,
        request: AgentGenerationInput,
    ) -> AgentGenerationResult:
        quiz = AgentGeneratedFormatResult(
            format_type=GeneratedFormatType.QUIZ,
            status=GeneratedFormatStatus.FAILED,
            content=None,
            chunks_used=(),
            error_message="Cuota de Gemini agotada.",
        )

        flashcards = AgentGeneratedFormatResult(
            format_type=GeneratedFormatType.FLASHCARDS,
            status=GeneratedFormatStatus.FAILED,
            content=None,
            chunks_used=(),
            error_message="Timeout al esperar la respuesta de Gemini.",
        )

        return AgentGenerationResult(
            document_id=request.document_id,
            results=(quiz, flashcards),
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

def build_service(
    *,
    document: Document | None,
    agents=None,
) -> tuple[
    FormatGenerationService,
    FakeGeneratedFormatRepository,
]:
    """Construye el servicio con dependencias controladas."""
    repository = (
        FakeGeneratedFormatRepository()
    )

    service = FormatGenerationService(
        document_repository=(
            FakeDocumentRepository(
                document
            )
        ),
        generated_format_repository=repository,
        agents=(
            agents
            if agents is not None
            else FakeAgents()
        ),
    )

    return service, repository


def test_prepare_generation_persists_processing_attempts() -> None:
    """Registra Quiz y Flashcards antes de llamar a Agentes."""
    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        )
    )

    attempts = service.prepare_generation(
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

    assert len(attempts) == 2
    assert len(repository.formats) == 2

    assert {
        attempt.format_type
        for attempt in attempts
    } == {
        GeneratedFormatType.QUIZ,
        GeneratedFormatType.FLASHCARDS,
    }

    assert all(
        attempt.status
        == GeneratedFormatStatus.PROCESSING
        for attempt in attempts
    )

    assert all(
        attempt.content is None
        for attempt in attempts
    )

    assert all(
        attempt.chunks_used == ()
        for attempt in attempts
    )

    assert all(
        attempt.error_message is None
        for attempt in attempts
    )


def test_prepare_generation_rejects_unknown_document() -> None:
    """No registra intentos para un documento inexistente."""
    service, repository = build_service(
        document=None
    )

    with pytest.raises(
        FormatGenerationDocumentNotFoundError,
    ):
        service.prepare_generation(
            document_id="doc_inexistente",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
            profile="beginner",
            niche="general",
            detail_level="standard",
        )

    assert repository.formats == []


def test_prepare_generation_requires_indexed_document() -> None:
    """Solo permite preparar formatos para documentos indexados."""
    service, repository = build_service(
        document=build_document(
            DocumentStatus.STORED
        )
    )

    with pytest.raises(
        DocumentNotReadyForGenerationError,
    ):
        service.prepare_generation(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
            ),
            profile="beginner",
            niche="general",
            detail_level="standard",
        )

    assert repository.formats == []


def test_complete_generation_updates_same_attempts() -> None:
    """Los resultados reemplazan processing sin crear nuevas filas."""
    agents = FakeAgents()

    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        ),
        agents=agents,
    )

    attempts = service.prepare_generation(
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

    original_ids = {
        attempt.format_type: attempt.format_id
        for attempt in attempts
    }

    result = asyncio.run(
        service.complete_generation(
            attempts=tuple(
                attempts
            )
        )
    )

    assert len(result) == 2

    assert len(repository.formats) == 2

    assert all(
        generated_format.status
        == GeneratedFormatStatus.SUCCESS
        for generated_format in result
    )

    assert {
        generated_format.format_type:
        generated_format.format_id
        for generated_format in result
    } == original_ids

    assert agents.last_request is not None

    quiz = next(
        generated_format
        for generated_format in result
        if (
            generated_format.format_type
            == GeneratedFormatType.QUIZ
        )
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


def test_complete_generation_marks_same_attempts_failed_on_agents_error() -> None:
    """Un fallo externo convierte processing en failed."""
    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        ),
        agents=FailingAgents(),
    )

    attempts = service.prepare_generation(
        document_id="doc_123",
        formats=(
            GeneratedFormatType.QUIZ,
            GeneratedFormatType.FLASHCARDS,
        ),
        profile="beginner",
        niche="general",
        detail_level="standard",
    )

    original_ids = {
        attempt.format_id
        for attempt in attempts
    }

    with pytest.raises(
        FormatGenerationIntegrationError,
        match="Agentes no pudo generar",
    ):
        asyncio.run(
            service.complete_generation(
                attempts=tuple(
                    attempts
                )
            )
        )

    assert len(repository.formats) == 2

    assert {
        generated_format.format_id
        for generated_format
        in repository.formats
    } == original_ids

    assert all(
        generated_format.status
        == GeneratedFormatStatus.FAILED
        for generated_format
        in repository.formats
    )

    assert all(
        generated_format.content is None
        for generated_format
        in repository.formats
    )

    assert all(
        generated_format.error_message
        == (
            "Agentes no pudo generar los formatos "
            "del documento doc_123."
        )
        for generated_format
        in repository.formats
    )


def test_complete_generation_persists_partial_results_independently() -> None:
    """Un éxito parcial no colapsa el formato ok ni genericiza el fallido.

    Pin de contrato: esta lógica de persistir cada item de forma
    independiente ya existía en el servicio y no la modifica este
    cambio; lo que corrige el fix es que el adapter HTTP ahora
    efectivamente le entrega al servicio un resultado así (en vez de
    lanzar AgentsError) cuando Agentes responde 207.
    """
    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        ),
        agents=PartialFailureAgents(),
    )

    attempts = service.prepare_generation(
        document_id="doc_123",
        formats=(
            GeneratedFormatType.QUIZ,
            GeneratedFormatType.FLASHCARDS,
        ),
        profile="beginner",
        niche="technology",
        detail_level="detailed",
    )

    # No debe lanzar: un éxito parcial es un resultado válido, no una
    # excepción de integración.
    result = asyncio.run(
        service.complete_generation(
            attempts=tuple(attempts)
        )
    )

    assert len(result) == 2

    quiz = next(
        generated_format
        for generated_format in result
        if generated_format.format_type == GeneratedFormatType.QUIZ
    )
    flashcards = next(
        generated_format
        for generated_format in result
        if generated_format.format_type == GeneratedFormatType.FLASHCARDS
    )

    assert quiz.status == GeneratedFormatStatus.SUCCESS
    assert isinstance(quiz.content, QuizContent)

    assert flashcards.status == GeneratedFormatStatus.FAILED
    assert flashcards.content is None
    assert flashcards.error_message == (
        "Cuota de Gemini agotada. Intenta nuevamente más tarde."
    )


def test_complete_generation_persists_distinct_causes_on_global_failure() -> None:
    """Un fallo global conserva la causa real de cada formato, no un mensaje genérico compartido.

    Pin de contrato a nivel de servicio (no ejercita el adapter HTTP real):
    documenta que, cuando Agentes responde con un body válido aunque todo
    haya fallado, el servicio NO debe tratarlo como AgentsError/fallo de
    integración ni sobrescribir cada causa con un mensaje genérico
    compartido. El test de regresión real del fix HTTP está en
    test_http_agents_adapter_preserves_global_failure_causes.
    """
    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        ),
        agents=GlobalFailureAgents(),
    )

    attempts = service.prepare_generation(
        document_id="doc_123",
        formats=(
            GeneratedFormatType.QUIZ,
            GeneratedFormatType.FLASHCARDS,
        ),
        profile="beginner",
        niche="general",
        detail_level="standard",
    )

    # No debe lanzar FormatGenerationIntegrationError: Agentes respondió
    # con un body válido (aunque todo haya fallado), no hubo un fallo de
    # transporte/integración.
    result = asyncio.run(
        service.complete_generation(
            attempts=tuple(attempts)
        )
    )

    assert len(result) == 2
    assert all(
        generated_format.status == GeneratedFormatStatus.FAILED
        for generated_format in result
    )

    quiz = next(
        generated_format
        for generated_format in result
        if generated_format.format_type == GeneratedFormatType.QUIZ
    )
    flashcards = next(
        generated_format
        for generated_format in result
        if generated_format.format_type == GeneratedFormatType.FLASHCARDS
    )

    assert quiz.error_message == "Cuota de Gemini agotada."
    assert flashcards.error_message == "Timeout al esperar la respuesta de Gemini."
    assert quiz.error_message != flashcards.error_message


def test_complete_generation_marks_attempt_failed_on_wrong_document_id() -> None:
    """Un contrato inválido actualiza el intento existente a failed."""
    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        ),
        agents=WrongDocumentAgents(),
    )

    attempts = service.prepare_generation(
        document_id="doc_123",
        formats=(
            GeneratedFormatType.QUIZ,
        ),
        profile="beginner",
        niche="general",
        detail_level="standard",
    )

    format_id = attempts[0].format_id

    with pytest.raises(
        FormatGenerationContractError,
        match="document_id diferente",
    ):
        asyncio.run(
            service.complete_generation(
                attempts=tuple(
                    attempts
                )
            )
        )

    assert len(repository.formats) == 1

    failed_attempt = (
        repository.formats[0]
    )

    assert (
        failed_attempt.format_id
        == format_id
    )

    assert (
        failed_attempt.status
        == GeneratedFormatStatus.FAILED
    )


def test_complete_generation_marks_attempts_failed_when_result_is_incomplete() -> None:
    """Una respuesta incompleta falla el mismo lote processing."""
    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        ),
        agents=MissingFormatAgents(),
    )

    attempts = service.prepare_generation(
        document_id="doc_123",
        formats=(
            GeneratedFormatType.QUIZ,
            GeneratedFormatType.FLASHCARDS,
        ),
        profile="beginner",
        niche="general",
        detail_level="standard",
    )

    with pytest.raises(
        FormatGenerationContractError,
        match="no coinciden con los solicitados",
    ):
        asyncio.run(
            service.complete_generation(
                attempts=tuple(
                    attempts
                )
            )
        )

    assert len(repository.formats) == 2

    assert all(
        generated_format.status
        == GeneratedFormatStatus.FAILED
        for generated_format
        in repository.formats
    )


def test_prepare_generation_rejects_duplicate_formats() -> None:
    """No permite preparar dos veces el mismo formato."""
    service, repository = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        )
    )

    with pytest.raises(
        ValueError,
        match="formatos duplicados",
    ):
        service.prepare_generation(
            document_id="doc_123",
            formats=(
                GeneratedFormatType.QUIZ,
                GeneratedFormatType.QUIZ,
            ),
            profile="beginner",
            niche="general",
            detail_level="standard",
        )

    assert repository.formats == []


def test_complete_generation_requires_processing_attempts() -> None:
    """No permite ejecutar nuevamente un intento ya terminado."""
    service, _ = build_service(
        document=build_document(
            DocumentStatus.INDEXED
        )
    )

    attempts = service.prepare_generation(
        document_id="doc_123",
        formats=(
            GeneratedFormatType.QUIZ,
        ),
        profile="beginner",
        niche="general",
        detail_level="standard",
    )

    processing = attempts[0]

    invalid_attempt = GeneratedFormat(
        format_id=processing.format_id,
        document_id=processing.document_id,
        format_type=processing.format_type,
        status=GeneratedFormatStatus.FAILED,
        generation_context=(
            processing.generation_context
        ),
        content=None,
        chunks_used=(),
        error_message="Fallo previo.",
        created_at=processing.created_at,
        updated_at=processing.updated_at,
    )

    with pytest.raises(
        FormatGenerationAttemptStateError,
        match="processing",
    ):
        asyncio.run(
            service.complete_generation(
                attempts=(
                    invalid_attempt,
                )
            )
        )
