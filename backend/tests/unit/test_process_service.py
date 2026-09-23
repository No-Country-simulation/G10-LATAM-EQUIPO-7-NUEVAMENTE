"""Pruebas unitarias de ProcessService."""

from app.application.process_service import ProcessService
from app.domain.enums import ProcessStatus


def test_create_process() -> None:
    service = ProcessService()

    process = service.create_process("doc_123")

    assert process.document_id == "doc_123"
    assert process.process_id.startswith("process_")
    assert process.status == ProcessStatus.PENDING