"""Endpoints HTTP relacionados con la carga de documentos."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.document import DocumentUploadResponse
from app.services.storage import FileTooLargeError, save_upload

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

_ALLOWED_EXTENSIONS = frozenset({
    ".pdf",
    ".md",
    ".txt",
})


def _is_supported_document(filename: str | None) -> bool:
    """Indica si el nombre corresponde a un formato admitido."""
    if not filename:
        return False

    extension = Path(filename).suffix.lower()

    return extension in _ALLOWED_EXTENSIONS


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar documento",
    description=(
        "Recibe un documento mediante multipart/form-data. "
        "Los formatos admitidos son PDF, Markdown (.md) y TXT."
    ),
)
async def upload_document(
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Documento PDF, Markdown (.md) o texto plano (.txt)."
            )
        ),
    ],
) -> DocumentUploadResponse:
    """Recibe y almacena temporalmente un documento soportado."""
    if not _is_supported_document(file.filename):
        await file.close()

        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Formato de documento no soportado. "
                "Se admiten archivos PDF, Markdown (.md) y TXT."
            ),
        )

    try:
        uploaded_file = await save_upload(file)
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "El archivo supera el máximo de "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        ) from exc

    return DocumentUploadResponse(
        filename=uploaded_file.filename,
        original_filename=uploaded_file.original_filename,
        content_type=uploaded_file.content_type,
        size_bytes=uploaded_file.size_bytes,
    )