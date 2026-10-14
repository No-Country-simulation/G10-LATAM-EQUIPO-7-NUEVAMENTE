"""Configuración de la base de datos SQLite utilizada en desarrollo."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_DOCUMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    content_type TEXT,
    size_bytes INTEGER NOT NULL,
    status TEXT NOT NULL,
    oci_object_name TEXT,
    learning_metadata_json TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_GENERATED_FORMATS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS generated_formats (
    format_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,

    format_type TEXT NOT NULL
        CHECK (
            format_type IN (
                'quiz',
                'flashcards',
                'tldr',
                'video_script'
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
);
"""

_GENERATED_FORMATS_MIGRATION_TABLE_SQL = """
CREATE TABLE generated_formats_migrated (
    format_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,

    format_type TEXT NOT NULL
        CHECK (
            format_type IN (
                'quiz',
                'flashcards',
                'tldr',
                'video_script'
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
);
"""

_FORMAT_EVALUATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS format_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    format_id TEXT NOT NULL,

    -- V1 (Evaluator heurístico 1.1): NULL en una evaluación V2 pura.
    status TEXT
        CHECK (
            status IS NULL
            OR status IN (
                'aprobado',
                'requiere_revision',
                'rechazado'
            )
        ),

    relevance_score INTEGER
        CHECK (
            relevance_score IS NULL
            OR relevance_score BETWEEN 1 AND 5
        ),

    coherence_score INTEGER
        CHECK (
            coherence_score IS NULL
            OR coherence_score BETWEEN 1 AND 5
        ),

    didactic_adaptation_score INTEGER
        CHECK (
            didactic_adaptation_score IS NULL
            OR didactic_adaptation_score BETWEEN 1 AND 5
        ),

    content_support_score INTEGER
        CHECK (
            content_support_score IS NULL
            OR content_support_score BETWEEN 1 AND 5
        ),

    unsupported_information INTEGER NOT NULL
        CHECK (
            unsupported_information IN (0, 1)
        ),

    observations_json TEXT NOT NULL DEFAULT '[]',

    evaluator_version TEXT,
    rubric_version TEXT,

    -- V2 (Evaluation Contract V2, Sprint 4): NULL en una evaluación V1.
    verdict TEXT
        CHECK (
            verdict IS NULL
            OR verdict IN (
                'approved',
                'requires_revision',
                'rejected'
            )
        ),

    heuristic_scores_json TEXT,
    semantic_evaluation_json TEXT,

    created_at TEXT NOT NULL,

    FOREIGN KEY (format_id)
        REFERENCES generated_formats(format_id)
        ON DELETE CASCADE
);
"""

_FORMAT_EVALUATIONS_MIGRATION_TABLE_SQL = (
    _FORMAT_EVALUATIONS_TABLE_SQL
    .replace(
        "IF NOT EXISTS format_evaluations",
        "format_evaluations_migrated",
    )
)

_SCHEMA_INDEXES_SQL = (
    """
    CREATE INDEX IF NOT EXISTS
        idx_generated_formats_document
    ON generated_formats(document_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS
        idx_generated_formats_document_type
    ON generated_formats(
        document_id,
        format_type
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS
        idx_format_evaluations_format
    ON format_evaluations(format_id);
    """,
)

_REQUIRED_GENERATED_FORMAT_SCHEMA_TOKENS = (
    "'processing'",
    "'quiz'",
    "'flashcards'",
    "'tldr'",
    "'video_script'",
)


class SQLiteDatabase:
    """Gestiona conexiones y creación del esquema SQLite."""

    _URL_PREFIX = "sqlite:///"

    def __init__(
        self,
        database_url: str,
    ) -> None:
        if not database_url.startswith(
            self._URL_PREFIX
        ):
            raise ValueError(
                "SQLiteDatabase requiere una URL "
                "con formato sqlite:///ruta."
            )

        raw_path = database_url.removeprefix(
            self._URL_PREFIX
        )

        if not raw_path:
            raise ValueError(
                "La ruta de SQLite no puede estar vacía."
            )

        self._database_path = Path(
            raw_path
        )

    @property
    def database_path(self) -> Path:
        """Ruta física del archivo SQLite."""
        return self._database_path

    @contextmanager
    def connect(
        self,
    ) -> Iterator[sqlite3.Connection]:
        """Abre una conexión SQLite y garantiza su cierre.

        La transacción se confirma al salir normalmente del contexto.
        Si ocurre una excepción, SQLite realiza rollback antes de que
        la conexión sea cerrada.

        Yields:
            Conexión SQLite configurada para uso dentro del contexto.
        """
        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            self._database_path
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(
        self,
    ) -> None:
        """Crea y actualiza las estructuras requeridas por BackendAPI."""
        with self.connect() as connection:
            connection.execute(
                _DOCUMENTS_TABLE_SQL
            )

            self._ensure_generated_formats_schema(
                connection
            )

            self._ensure_documents_schema(
                connection
            )

            self._ensure_format_evaluations_schema(
                connection
            )

            for statement in (
                _SCHEMA_INDEXES_SQL
            ):
                connection.execute(
                    statement
                )

    @staticmethod
    def _ensure_documents_schema(
        connection: sqlite3.Connection,
    ) -> None:
        """Añade metadata pedagógica a bases creadas antes de Sprint 3."""
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(documents)"
            ).fetchall()
        }

        if (
            "learning_metadata_json"
            not in columns
        ):
            connection.execute(
                """
                ALTER TABLE documents
                ADD COLUMN learning_metadata_json TEXT
                """
            )

        if "is_active" not in columns:
            connection.execute(
                """
                ALTER TABLE documents
                ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1
                """
            )

    @staticmethod
    def _ensure_generated_formats_schema(
        connection: sqlite3.Connection,
    ) -> None:
        """Garantiza el CHECK vigente de estados y formatos.

        SQLite no permite modificar directamente una restricción ``CHECK``.
        Si la tabla existente no admite ``processing`` o cualquiera de los
        cuatro formatos canónicos, se reconstruye dentro de una transacción
        conservando todos los registros.

        Esto cubre tanto bases antiguas de Sprint 2 como bases de Sprint 3
        creadas cuando únicamente existían ``quiz`` y ``flashcards``.

        Las claves foráneas se desactivan únicamente durante la
        reconstrucción porque ``format_evaluations`` puede referenciar
        la tabla que se reemplaza. Antes de confirmar la migración se
        ejecuta ``foreign_key_check``.
        """
        schema_row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE
                type = 'table'
                AND name = 'generated_formats'
            """
        ).fetchone()

        if schema_row is None:
            connection.execute(
                _GENERATED_FORMATS_TABLE_SQL
            )
            return

        schema_sql = (
            schema_row["sql"] or ""
        ).lower()

        schema_is_current = all(
            token in schema_sql
            for token
            in _REQUIRED_GENERATED_FORMAT_SCHEMA_TOKENS
        )

        if schema_is_current:
            return

        connection.execute(
            "PRAGMA foreign_keys = OFF"
        )

        try:
            connection.execute(
                "BEGIN"
            )

            connection.execute(
                """
                DROP TABLE IF EXISTS
                    generated_formats_migrated
                """
            )

            connection.execute(
                _GENERATED_FORMATS_MIGRATION_TABLE_SQL
            )

            connection.execute(
                """
                INSERT INTO generated_formats_migrated (
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
                SELECT
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
                FROM generated_formats
                """
            )

            connection.execute(
                "DROP TABLE generated_formats"
            )

            connection.execute(
                """
                ALTER TABLE generated_formats_migrated
                RENAME TO generated_formats
                """
            )

            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if violations:
                raise sqlite3.IntegrityError(
                    "La migración de generated_formats "
                    "produjo referencias inválidas."
                )

            connection.commit()

        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise

        finally:
            connection.execute(
                "PRAGMA foreign_keys = ON"
            )

    @staticmethod
    def _ensure_format_evaluations_schema(
        connection: sqlite3.Connection,
    ) -> None:
        """Garantiza el esquema V1+V2 vigente de ``format_evaluations``.

        Sprint 4 relaja a nullable las columnas V1 (``status`` y los
        cuatro scores heurísticos enteros) y agrega las columnas V2
        (``verdict``, ``heuristic_scores_json``, ``semantic_evaluation_json``).
        SQLite no permite modificar directamente ``NOT NULL`` ni un
        ``CHECK`` existente, así que -igual que con ``generated_formats``-
        la tabla se reconstruye dentro de una transacción conservando
        todas las evaluaciones ya persistidas.
        """
        schema_row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE
                type = 'table'
                AND name = 'format_evaluations'
            """
        ).fetchone()

        if schema_row is None:
            connection.execute(
                _FORMAT_EVALUATIONS_TABLE_SQL
            )
            return

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(format_evaluations)"
            ).fetchall()
        }

        schema_is_current = (
            "verdict" in columns
            and "heuristic_scores_json" in columns
            and "semantic_evaluation_json" in columns
        )

        if schema_is_current:
            return

        connection.execute(
            "PRAGMA foreign_keys = OFF"
        )

        try:
            connection.execute(
                "BEGIN"
            )

            connection.execute(
                """
                DROP TABLE IF EXISTS
                    format_evaluations_migrated
                """
            )

            connection.execute(
                _FORMAT_EVALUATIONS_MIGRATION_TABLE_SQL
            )

            # Tolerante a tablas legacy que ni siquiera tengan todavía
            # las columnas V1 completas (p. ej. un stub mínimo con solo
            # evaluation_id/format_id): cada columna ausente se reemplaza
            # por un literal SQL que cumple el NOT NULL/CHECK del esquema
            # nuevo, en vez de asumir que siempre existió.
            column_sources = {
                "evaluation_id": "evaluation_id",
                "format_id": "format_id",
                "status": (
                    "status" if "status" in columns else "NULL"
                ),
                "relevance_score": (
                    "relevance_score"
                    if "relevance_score" in columns
                    else "NULL"
                ),
                "coherence_score": (
                    "coherence_score"
                    if "coherence_score" in columns
                    else "NULL"
                ),
                "didactic_adaptation_score": (
                    "didactic_adaptation_score"
                    if "didactic_adaptation_score" in columns
                    else "NULL"
                ),
                "content_support_score": (
                    "content_support_score"
                    if "content_support_score" in columns
                    else "NULL"
                ),
                "unsupported_information": (
                    "unsupported_information"
                    if "unsupported_information" in columns
                    else "0"
                ),
                "observations_json": (
                    "observations_json"
                    if "observations_json" in columns
                    else "'[]'"
                ),
                "evaluator_version": (
                    "evaluator_version"
                    if "evaluator_version" in columns
                    else "NULL"
                ),
                "rubric_version": (
                    "rubric_version"
                    if "rubric_version" in columns
                    else "NULL"
                ),
                "created_at": (
                    "created_at"
                    if "created_at" in columns
                    else "'1970-01-01T00:00:00+00:00'"
                ),
            }

            insert_columns = ", ".join(
                column_sources.keys()
            )
            select_expressions = ", ".join(
                column_sources.values()
            )

            connection.execute(
                f"""
                INSERT INTO format_evaluations_migrated (
                    {insert_columns}
                )
                SELECT {select_expressions}
                FROM format_evaluations
                """
            )

            connection.execute(
                "DROP TABLE format_evaluations"
            )

            connection.execute(
                """
                ALTER TABLE format_evaluations_migrated
                RENAME TO format_evaluations
                """
            )

            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if violations:
                raise sqlite3.IntegrityError(
                    "La migración de format_evaluations "
                    "produjo referencias inválidas."
                )

            connection.commit()

        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise

        finally:
            connection.execute(
                "PRAGMA foreign_keys = ON"
            )
