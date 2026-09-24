"""Endpoint legacy de carga de archivos.

Se mantiene temporalmente por compatibilidad mientras la carga de documentos
migra a ``POST /documents``.
"""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.file import UploadedFile
from app.services.storage import FileTooLargeError, save_upload

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    response_model=UploadedFile,
    status_code=status.HTTP_201_CREATED,
    summary="Subir un archivo",
)
async def upload_file(
    file: Annotated[
        UploadFile,
        File(description="Archivo a almacenar."),
    ],
) -> UploadedFile:
    try:
        return await save_upload(file)
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                "El archivo supera el máximo de "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        ) from exc