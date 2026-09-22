"""Pruebas de los contratos provisionales de adaptación."""

from app.schemas.adaptation import AdaptationRequest


def test_adaptation_request() -> None:
    request = AdaptationRequest(
        document_id="doc_123",
        profile="Principiante",
        output_format="Flashcards",
        niche="General",
        detail_level="Didáctico",
    )

    assert request.document_id == "doc_123"
    assert request.output_format == "Flashcards"