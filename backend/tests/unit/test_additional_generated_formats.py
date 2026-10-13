"""Cobertura de contratos canónicos para TLDR y Video Script."""

from datetime import UTC, datetime

import pytest

from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    TLDRContent,
    VideoScriptContent,
    VideoScriptScene,
)
from app.domain.generated_educational_package import (
    GeneratedEducationalPackage,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.domain.learning_metadata import (
    LearningMetadata,
)
from app.infrastructure.persistence.models import (
    GeneratedFormatRecord,
)
from app.schemas.generated_format import (
    GeneratedFormatResponse,
)


def _context() -> GenerationContext:
    """Construye contexto pedagógico reutilizable."""
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
        learning_objective=(
            "Comprender la arquitectura."
        ),
    )


def _evidence() -> tuple[
    ChunkEvidence,
    ...,
]:
    """Construye evidencia válida para Data/IA."""
    return (
        ChunkEvidence(
            chunk_id="chunk_1",
            document_id="doc_123",
            rank=1,
            score=0.95,
            text=(
                "BackendAPI coordina integraciones "
                "y persistencia."
            ),
        ),
    )


def _tldr() -> TLDRContent:
    """Construye un TLDR canónico."""
    return TLDRContent(
        title="Resumen de arquitectura",
        summary=(
            "BackendAPI coordina los servicios externos."
        ),
        key_points=(
            "Orquestación",
            "Persistencia",
        ),
        conclusion=(
            "La separación de responsabilidades "
            "facilita el mantenimiento."
        ),
    )


def _video_script() -> VideoScriptContent:
    """Construye un Video Script canónico."""
    return VideoScriptContent(
        title="Arquitectura de NuevaMente",
        estimated_duration_minutes=2,
        scenes=(
            VideoScriptScene(
                scene_id="scene_1",
                title="Arquitectura",
                visual_description=(
                    "Diagrama con Backend, Agentes "
                    "y Data/IA."
                ),
                narration=(
                    "BackendAPI coordina las "
                    "integraciones externas."
                ),
                duration_seconds=45,
            ),
        ),
    )


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            _tldr(),
            {
                "title": "Resumen de arquitectura",
                "summary": (
                    "BackendAPI coordina los servicios externos."
                ),
                "key_points": [
                    "Orquestación",
                    "Persistencia",
                ],
                "conclusion": (
                    "La separación de responsabilidades "
                    "facilita el mantenimiento."
                ),
            },
        ),
        (
            _video_script(),
            {
                "title": "Arquitectura de NuevaMente",
                "estimated_duration_minutes": 2,
                "scenes": [
                    {
                        "scene_id": "scene_1",
                        "title": "Arquitectura",
                        "visual_description": (
                            "Diagrama con Backend, Agentes "
                            "y Data/IA."
                        ),
                        "narration": (
                            "BackendAPI coordina las "
                            "integraciones externas."
                        ),
                        "duration_seconds": 45,
                    }
                ],
            },
        ),
    ],
)
def test_additional_content_round_trip(
    content,
    expected: dict[str, object],
) -> None:
    """Los nuevos contratos conservan el JSON acordado con Data/IA."""
    payload = content.to_dict()

    assert payload == expected

    if isinstance(
        content,
        TLDRContent,
    ):
        rebuilt = TLDRContent.from_dict(
            payload
        )
    else:
        rebuilt = VideoScriptContent.from_dict(
            payload
        )

    assert rebuilt == content


@pytest.mark.parametrize(
    ("format_type", "content"),
    [
        (
            GeneratedFormatType.TLDR,
            _tldr(),
        ),
        (
            GeneratedFormatType.VIDEO_SCRIPT,
            _video_script(),
        ),
    ],
)
def test_generated_format_accepts_matching_additional_content(
    format_type: GeneratedFormatType,
    content,
) -> None:
    """GeneratedFormat valida TLDR y Video Script por tipo."""
    generated = GeneratedFormat(
        format_id=f"fmt_{format_type.value}",
        document_id="doc_123",
        format_type=format_type,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=_context(),
        content=content,
        chunks_used=_evidence(),
    )

    assert generated.is_evaluation_ready is True


def test_generated_format_rejects_mismatched_additional_content() -> None:
    """Un TLDR no puede persistirse como Video Script."""
    with pytest.raises(
        ValueError,
        match="VideoScriptContent",
    ):
        GeneratedFormat(
            format_id="fmt_mismatch",
            document_id="doc_123",
            format_type=(
                GeneratedFormatType.VIDEO_SCRIPT
            ),
            status=(
                GeneratedFormatStatus.SUCCESS
            ),
            generation_context=_context(),
            content=_tldr(),
            chunks_used=_evidence(),
        )


@pytest.mark.parametrize(
    ("format_type", "content"),
    [
        (
            GeneratedFormatType.TLDR,
            _tldr(),
        ),
        (
            GeneratedFormatType.VIDEO_SCRIPT,
            _video_script(),
        ),
    ],
)
def test_generated_format_record_round_trip_supports_new_formats(
    format_type: GeneratedFormatType,
    content,
) -> None:
    """La persistencia serializa y reconstruye los nuevos contratos."""
    generated = GeneratedFormat(
        format_id=f"fmt_{format_type.value}",
        document_id="doc_123",
        format_type=format_type,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=_context(),
        content=content,
        chunks_used=_evidence(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    rebuilt = (
        GeneratedFormatRecord
        .from_domain(
            generated
        )
        .to_domain()
    )

    assert rebuilt.format_type == format_type
    assert rebuilt.content == content
    assert rebuilt.chunks_used == generated.chunks_used


@pytest.mark.parametrize(
    ("format_type", "content"),
    [
        (
            GeneratedFormatType.TLDR,
            _tldr(),
        ),
        (
            GeneratedFormatType.VIDEO_SCRIPT,
            _video_script(),
        ),
    ],
)
def test_http_response_exposes_new_content_contracts(
    format_type: GeneratedFormatType,
    content,
) -> None:
    """GET /formats puede serializar TLDR y Video Script."""
    generated = GeneratedFormat(
        format_id=f"fmt_{format_type.value}",
        document_id="doc_123",
        format_type=format_type,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=_context(),
        content=content,
        chunks_used=_evidence(),
    )

    response = (
        GeneratedFormatResponse
        .from_domain(
            generated
        )
        .model_dump(
            mode="json"
        )
    )

    assert response["status"] == "success"
    assert response["content"] == content.to_dict()


def test_educational_package_serializes_additional_formats() -> None:
    """El snapshot OCI incluye TLDR y Video Script sin lógica especial."""
    formats = (
        GeneratedFormat(
            format_id="fmt_tldr",
            document_id="doc_123",
            format_type=GeneratedFormatType.TLDR,
            status=GeneratedFormatStatus.SUCCESS,
            generation_context=_context(),
            content=_tldr(),
            chunks_used=_evidence(),
        ),
        GeneratedFormat(
            format_id="fmt_video_script",
            document_id="doc_123",
            format_type=(
                GeneratedFormatType.VIDEO_SCRIPT
            ),
            status=GeneratedFormatStatus.SUCCESS,
            generation_context=_context(),
            content=_video_script(),
            chunks_used=_evidence(),
        ),
    )

    package = GeneratedEducationalPackage(
        document_id="doc_123",
        learning_metadata=LearningMetadata(
            key_concepts=(
                "Arquitectura",
            ),
            prerequisites=(),
            estimated_time_minutes=10,
        ),
        formats=formats,
    )

    payload = package.to_dict()

    assert set(
        payload["formats"]
    ) == {
        "tldr",
        "video_script",
    }

    assert (
        payload["formats"]["tldr"]["content"]
        == _tldr().to_dict()
    )

    assert (
        payload["formats"]["video_script"]["content"]
        == _video_script().to_dict()
    )


def test_tldr_rejects_non_list_key_points() -> None:
    """TLDR exige key_points como lista en el contrato JSON."""
    with pytest.raises(
        ValueError,
        match="key_points debe ser una lista",
    ):
        TLDRContent.from_dict(
            {
                "title": "Resumen",
                "summary": "Contenido",
                "key_points": "Punto",
                "conclusion": "Conclusión",
            }
        )


def test_video_script_rejects_invalid_scene_item() -> None:
    """Video Script no descarta escenas inválidas silenciosamente."""
    with pytest.raises(
        ValueError,
        match=r"scenes\[0\] debe ser un objeto",
    ):
        VideoScriptContent.from_dict(
            {
                "title": "Guion",
                "estimated_duration_minutes": 1,
                "scenes": [
                    "escena_invalida"
                ],
            }
        )
