"""Pruebas de migración SQLite de ``format_evaluations`` (V1 -> V1+V2)."""

import sqlite3
from pathlib import Path

from app.infrastructure.persistence.database import (
    SQLiteDatabase,
)
from app.infrastructure.persistence.models import (
    FormatEvaluationRecord,
)


def test_initialize_migrates_fully_populated_v1_table_without_data_loss(
    tmp_path: Path,
) -> None:
    """Una tabla V1 pre-Sprint-4, con una fila real y completa, sobrevive
    intacta a la migración que agrega las columnas V2 y relaja los
    ``NOT NULL``/``CHECK`` de las columnas V1."""
    database_path = tmp_path / "legacy_populated.db"

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
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
                    CHECK (format_type IN ('quiz', 'flashcards')),
                status TEXT NOT NULL
                    CHECK (status IN ('success', 'failed', 'no_results')),
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

        # Esquema V1 real, pre-Sprint-4: status y los cuatro scores son
        # NOT NULL (todavía no existen verdict/heuristic_scores_json/
        # semantic_evaluation_json), tal como estaba en origin/QA antes
        # de esta tarea.
        connection.execute(
            """
            CREATE TABLE format_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                format_id TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (
                        status IN (
                            'aprobado',
                            'requiere_revision',
                            'rechazado'
                        )
                    ),
                relevance_score INTEGER NOT NULL
                    CHECK (relevance_score BETWEEN 1 AND 5),
                coherence_score INTEGER NOT NULL
                    CHECK (coherence_score BETWEEN 1 AND 5),
                didactic_adaptation_score INTEGER NOT NULL
                    CHECK (didactic_adaptation_score BETWEEN 1 AND 5),
                content_support_score INTEGER NOT NULL
                    CHECK (content_support_score BETWEEN 1 AND 5),
                unsupported_information INTEGER NOT NULL
                    CHECK (unsupported_information IN (0, 1)),
                observations_json TEXT NOT NULL DEFAULT '[]',
                evaluator_version TEXT,
                rubric_version TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (format_id)
                    REFERENCES generated_formats(format_id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            INSERT INTO documents (
                document_id, original_filename, sha256, content_type,
                size_bytes, status, oci_object_name, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "doc_legacy",
                "manual.txt",
                "a" * 64,
                "text/plain",
                10,
                "indexed",
                "documents/doc_legacy/original.txt",
                "2026-09-01T12:00:00+00:00",
                "2026-09-01T12:00:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO generated_formats (
                format_id, document_id, format_type, status, content_json,
                chunks_used_json, profile, niche, detail_level,
                learning_objective, error_message, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "fmt_legacy",
                "doc_legacy",
                "quiz",
                "success",
                '{"questions": []}',
                "[]",
                "beginner",
                "general",
                "standard",
                "Aprender fracciones",
                None,
                "2026-09-01T12:01:00+00:00",
                "2026-09-01T12:01:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO format_evaluations (
                evaluation_id, format_id, status, relevance_score,
                coherence_score, didactic_adaptation_score,
                content_support_score, unsupported_information,
                observations_json, evaluator_version, rubric_version,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "eval_legacy_populated",
                "fmt_legacy",
                "requiere_revision",
                4,
                3,
                2,
                5,
                1,
                '["Falta justificar la respuesta 2."]',
                "evaluator-1.1",
                "rubric-1.0",
                "2026-09-01T12:02:00+00:00",
            ),
        )

        connection.commit()
    finally:
        connection.close()

    database = SQLiteDatabase(f"sqlite:///{database_path.as_posix()}")
    database.initialize()

    with database.connect() as connection:
        schema = connection.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'table' AND name = 'format_evaluations'
            """
        ).fetchone()

        assert schema is not None
        assert "verdict" in (schema["sql"] or "")
        assert "heuristic_scores_json" in (schema["sql"] or "")

        row = connection.execute(
            """
            SELECT * FROM format_evaluations
            WHERE evaluation_id = ?
            """,
            ("eval_legacy_populated",),
        ).fetchone()

        assert row is not None
        assert row["format_id"] == "fmt_legacy"
        assert row["status"] == "requiere_revision"
        assert row["relevance_score"] == 4
        assert row["coherence_score"] == 3
        assert row["didactic_adaptation_score"] == 2
        assert row["content_support_score"] == 5
        assert row["unsupported_information"] == 1
        assert row["observations_json"] == (
            '["Falta justificar la respuesta 2."]'
        )
        assert row["evaluator_version"] == "evaluator-1.1"
        assert row["rubric_version"] == "rubric-1.0"
        assert row["created_at"] == "2026-09-01T12:02:00+00:00"
        assert row["verdict"] is None
        assert row["heuristic_scores_json"] is None
        assert row["semantic_evaluation_json"] is None

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        assert violations == []

        evaluation = FormatEvaluationRecord.from_row(row).to_domain()

        assert evaluation.is_v2 is False
        assert evaluation.status is not None
        assert evaluation.status.value == "requiere_revision"
        assert evaluation.scores is not None
        assert evaluation.scores.relevance == 4
        assert evaluation.scores.content_support == 5
        assert evaluation.unsupported_information is True
        assert evaluation.observations == (
            "Falta justificar la respuesta 2.",
        )
        assert evaluation.verdict is None
        assert evaluation.heuristic_scores is None
        assert evaluation.semantic_evaluation is None

        # La tabla temporal de la migración no debe quedar residual.
        leftover = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'format_evaluations_migrated'
            """
        ).fetchone()
        assert leftover is None
