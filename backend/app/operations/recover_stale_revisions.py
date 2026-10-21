"""CLI explícita de recuperación de revisiones interrumpidas.

Ejecución desde backend:
    python -m app.operations.recover_stale_revisions --database-url sqlite:///ruta.db

--apply exige confirmar la detención de los trabajadores. No llama al LLM.
"""

import argparse
import json
import sys
from collections.abc import Sequence

from app.application.stale_revision_recovery_service import StaleRevisionRecoveryService
from app.infrastructure.persistence.database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_stale_revision_recovery_adapter import (
    SQLiteStaleRevisionRecoveryAdapter,
)
from app.ports.generated_format_repository_port import GeneratedFormatRepositoryError


def build_parser() -> argparse.ArgumentParser:
    """Define un contrato operativo independiente de FastAPI."""
    parser = argparse.ArgumentParser(
        description="Inspecciona o cierra revisiones processing antiguas."
    )
    parser.add_argument("--database-url", required=True, help="URL SQLite explícita.")
    parser.add_argument("--older-than-minutes", type=int, default=60)
    parser.add_argument("--apply", action="store_true", help="Cambiar los estados a failed.")
    parser.add_argument(
        "--acknowledge-workers-stopped", action="store_true",
        help="Confirma que los trabajadores de generación/revisión están detenidos.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta la recuperación; 0 en éxito y 2 en error controlado."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.apply and not args.acknowledge_workers_stopped:
        parser.error("--apply exige --acknowledge-workers-stopped.")
    try:
        database = SQLiteDatabase(args.database_url)
        if not database.database_path.is_file():
            raise ValueError("La base SQLite indicada no existe; no se creará otra.")
        service = StaleRevisionRecoveryService(
            recovery_port=SQLiteStaleRevisionRecoveryAdapter(database),
        )
        result = service.execute(
            older_than_minutes=args.older_than_minutes,
            apply=args.apply,
        )
    except (ValueError, GeneratedFormatRepositoryError) as exc:
        print(f"Error de recuperación: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "applied": result.applied,
        "cutoff": result.cutoff.isoformat(),
        "candidates": [{
            "format_id": item.format_id,
            "original_format_id": item.original_format_id,
            "document_id": item.document_id,
            "updated_at": item.updated_at.isoformat(),
        } for item in result.candidates],
        "recovered_ids": list(result.recovered_ids),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
