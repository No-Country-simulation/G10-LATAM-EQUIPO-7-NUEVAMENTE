"""Pruebas unitarias de la entidad Process."""

from app.domain.enums import ProcessStatus
from app.domain.process import Process


def test_process_starts_pending() -> None:
    process = Process(
        process_id="process_123",
        document_id="doc_123",
    )

    assert process.status == ProcessStatus.PENDING


def test_process_can_be_completed() -> None:
    process = Process(
        process_id="process_123",
        document_id="doc_123",
    )

    process.mark_processing()
    process.mark_completed()

    assert process.status == ProcessStatus.COMPLETED
    assert process.completed_at is not None


def test_process_can_fail() -> None:
    process = Process(
        process_id="process_123",
        document_id="doc_123",
    )

    process.mark_failed("Error de prueba")

    assert process.status == ProcessStatus.FAILED
    assert process.error_message == "Error de prueba"