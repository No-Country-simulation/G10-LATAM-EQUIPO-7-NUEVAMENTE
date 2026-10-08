"""Pruebas de persistencia SQLite para los cuatro formatos canónicos."""

import hashlib
import sqlite3
from pathlib import Path

from app.domain.document import Document
from app.domain.enums import (
    GeneratedFormatStatus,
    GeneratedFormatType,
)
from app.domain.generated_content import (
    TLDRContent,
    VideoScriptContent,
    VideoScriptScene,
)
from app.domain.generated_format import (
    ChunkEvidence,
    GeneratedFormat,
    GenerationContext,
)
from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.sqlite_document_repository_adapter import (
    SQLiteDocumentRepositoryAdapter,
)
from app.infrastructure.persistence.sqlite_generated_format_repository_adapter import (
    SQLiteGeneratedFormatRepositoryAdapter,
)


def _build_document() -> Document:
    """Construye un documento válido para satisfacer la FK."""
    content = b"documento de prueba"

    return Document(
        document_id="doc_four_formats",
        original_filename="manual.txt",
        sha256=hashlib.sha256(
            content
        ).hexdigest(),
        content_type="text/plain",
        size_bytes=len(content),
    )


def _build_context() -> GenerationContext:
    """Construye contexto pedagógico válido."""
    return GenerationContext(
        profile="intermediate",
        niche="backend",
        detail_level="detailed",
    )


def _build_evidence() -> tuple[
    ChunkEvidence,
    ...,
]:
    """Construye evidencia utilizada por los formatos."""
    return (
        ChunkEvidence(
            chunk_id="chunk_1",
            document_id="doc_four_formats",
            rank=1,
            score=0.95,
            text=(
                "BackendAPI coordina integraciones "
                "y persistencia."
            ),
        ),
    )


def _build_tldr() -> GeneratedFormat:
    """Construye una generación TLDR exitosa."""
    return GeneratedFormat(
        format_id="fmt_tldr_db",
        document_id="doc_four_formats",
        format_type=GeneratedFormatType.TLDR,
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=_build_context(),
        content=TLDRContent(
            title="Resumen",
            summary=(
                "BackendAPI coordina las integraciones."
            ),
            key_points=(
                "Orquestación",
                "Persistencia",
            ),
            conclusion=(
                "El desacoplamiento facilita el mantenimiento."
            ),
        ),
        chunks_used=_build_evidence(),
    )


def _build_video_script() -> GeneratedFormat:
    """Construye una generación Video Script exitosa."""
    return GeneratedFormat(
        format_id="fmt_video_script_db",
        document_id="doc_four_formats",
        format_type=(
            GeneratedFormatType.VIDEO_SCRIPT
        ),
        status=GeneratedFormatStatus.SUCCESS,
        generation_context=_build_context(),
        content=VideoScriptContent(
            title="Arquitectura de NuevaMente",
            estimated_duration_minutes=1,
            scenes=(
                VideoScriptScene(
                    scene_id="scene_1",
                    title="Introducción",
                    visual_description=(
                        "Diagrama de componentes."
                    ),
                    narration=(
                        "BackendAPI coordina servicios externos."
                    ),
                    duration_seconds=30,
                ),
            ),
        ),
        chunks_used=_build_evidence(),
    )


def test_repository_persists_tldr_and_video_script(
    tmp_path: Path,
) -> None:
    """SQLite acepta y reconstruye los dos formatos adicionales."""
    database = SQLiteDatabase(
        "sqlite:///"
        f"{(tmp_path / 'four_formats.db').as_posix()}"
    )
    database.initialize()

    document_repository = (
        SQLiteDocumentRepositoryAdapter(
            database
        )
    )
    format_repository = (
        SQLiteGeneratedFormatRepositoryAdapter(
            database
        )
    )

    document_repository.create(
        _build_document()
    )

    tldr = _build_tldr()
    video_script = _build_video_script()

    format_repository.create(
        tldr
    )
    format_repository.create(
        video_script
    )

    persisted_tldr = (
        format_repository.find_by_id(
            tldr.format_id
        )
    )
    persisted_video = (
        format_repository.find_by_id(
            video_script.format_id
        )
    )

    assert persisted_tldr is not None
    assert (
        persisted_tldr.format_type
        == GeneratedFormatType.TLDR
    )
    assert (
        persisted_tldr.content
        == tldr.content
    )

    assert persisted_video is not None
    assert (
        persisted_video.format_type
        == GeneratedFormatType.VIDEO_SCRIPT
    )
    assert (
        persisted_video.content
        == video_script.content
    )


def test_database_migrates_current_two_format_schema_to_four_formats(
    tmp_path: Path,
) -> None:
    """Amplía una BD Sprint 3 existente sin perder historial."""
    database_path = (
        tmp_path / "migration_four_formats.db"
    )

    connection = sqlite3.connect(
        database_path
    )
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        """
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            sha256 TEXT NOT NULL UNIQUE,
            content_type TEXT,
            size_bytes INTEGER NOT NULL,
            status TEXT NOT NULL,
            oci_object_name TEXT,
            learning_metadata_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE generated_formats (
            format_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            format_type TEXT NOT NULL
                CHECK (
                    format_type IN (
                        'quiz',
                        'flashcards'
                    )
                ),
            status TEXT NOT NULL
                CHECK (
                    status IN (
                        'processing',
                        'success',
                        'failed',
                        'no_results'
                    )
                ),
            content_json TEXT,
            chunks_used_json TEXT NOT NULL DEFAULT '[]',
            profile TEXT NOT NULL,
            niche TEXT NOT NULL,
            detail_level TEXT NOT NULL,
            learning_objective TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (document_id)
                REFERENCES documents(document_id)
                ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE format_evaluations (
            evaluation_id TEXT PRIMARY KEY,
            format_id TEXT NOT NULL,
            FOREIGN KEY (format_id)
                REFERENCES generated_formats(format_id)
                ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        INSERT INTO documents (
            document_id,
            original_filename,
            sha256,
            content_type,
            size_bytes,
            status,
            oci_object_name,
            learning_metadata_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "doc_legacy_four",
            "legacy.txt",
            "b" * 64,
            "text/plain",
            10,
            "indexed",
            "documents/doc_legacy_four/original.txt",
            None,
            "2026-10-07T12:00:00+00:00",
            "2026-10-07T12:00:00+00:00",
        ),
    )

    connection.execute(
        """
        INSERT INTO generated_formats (
            format_id,
            document_id,
            format_type,
            status,
            content_json,
            chunks_used_json,
            profile,
            niche,
            detail_level,
            learning_objective,
            error_message,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "fmt_legacy_quiz",
            "doc_legacy_four",
            "quiz",
            "failed",
            None,
            "[]",
            "beginner",
            "general",
            "standard",
            None,
            "Fallo histórico",
            "2026-10-07T12:01:00+00:00",
            "2026-10-07T12:01:00+00:00",
        ),
    )

    connection.execute(
        """
        INSERT INTO format_evaluations (
            evaluation_id,
            format_id
        )
        VALUES (?, ?)
        """,
        (
            "eval_legacy_four",
            "fmt_legacy_quiz",
        ),
    )

    connection.commit()
    connection.close()

    database = SQLiteDatabase(
        f"sqlite:///{database_path.as_posix()}"
    )
    database.initialize()

    with database.connect() as connection:
        schema_row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE
                type = 'table'
                AND name = 'generated_formats'
            """
        ).fetchone()

        assert schema_row is not None

        schema_sql = (
            schema_row["sql"] or ""
        ).lower()

        assert "'processing'" in schema_sql
        assert "'tldr'" in schema_sql
        assert "'video_script'" in schema_sql

        legacy_format = connection.execute(
            """
            SELECT *
            FROM generated_formats
            WHERE format_id = ?
            """,
            ("fmt_legacy_quiz",),
        ).fetchone()

        assert legacy_format is not None
        assert (
            legacy_format["status"]
            == "failed"
        )

        legacy_evaluation = connection.execute(
            """
            SELECT *
            FROM format_evaluations
            WHERE evaluation_id = ?
            """,
            ("eval_legacy_four",),
        ).fetchone()

        assert legacy_evaluation is not None
        assert (
            legacy_evaluation["format_id"]
            == "fmt_legacy_quiz"
        )

        for format_type in (
            "tldr",
            "video_script",
        ):
            connection.execute(
                """
                INSERT INTO generated_formats (
                    format_id,
                    document_id,
                    format_type,
                    status,
                    content_json,
                    chunks_used_json,
                    profile,
                    niche,
                    detail_level,
                    learning_objective,
                    error_message,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"fmt_{format_type}_processing",
                    "doc_legacy_four",
                    format_type,
                    "processing",
                    None,
                    "[]",
                    "beginner",
                    "general",
                    "standard",
                    None,
                    None,
                    "2026-10-07T12:02:00+00:00",
                    "2026-10-07T12:02:00+00:00",
                ),
            )

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        assert violations == []

    database.initialize()
