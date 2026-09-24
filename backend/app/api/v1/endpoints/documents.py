"""Endpoints HTTP relacionados con documentos."""

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.api.dependencies import (
    get_document_service,
    get_object_storage,
)
from app.application.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
)
from app.core.config import settings
from app.ports.object_storage import ObjectStoragePort
from app.schemas.document import (
    DocumentCreatedResponse,
    DocumentResponse,
)
from app.services.storage import FileTooLargeError, save_upload

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

_ALLOWED_MIME_TYPES = {
    ".pdf": frozenset({
        "application/pdf",
    }),
    ".md": frozenset({
        "text/markdown",
        "text/plain",
        "application/octet-stream",
    }),
    ".txt": frozenset({
        "text/plain",
        "application/octet-stream",
    }),
}


def _validate_document_type(
    filename: str | None,
    content_type: str | None,
) -> None:
    """Valida la extensión y el MIME type declarado del documento."""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El documento debe tener un nombre.",
        )

    extension = Path(filename).suffix.lower()

    allowed_mime_types = _ALLOWED_MIME_TYPES.get(
        extension
    )

    if allowed_mime_types is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Formato de documento no soportado. "
                "Se admiten archivos PDF, Markdown (.md) y TXT."
            ),
        )

    normalized_content_type = (
        (content_type or "")
        .split(";", maxsplit=1)[0]
        .strip()
        .lower()
    )

    if normalized_content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "El MIME type informado no corresponde "
                "con un formato admitido."
            ),
        )


@router.post(
    "",
    response_model=DocumentCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar e identificar documento",
    description=(
        "Recibe un documento PDF, Markdown o TXT, "
        "valida sus características e identifica "
        "su contenido mediante SHA-256."
    ),
    responses={
        200: {
            "model": DocumentCreatedResponse,
            "description": "Documento previamente registrado.",
        },
        400: {
            "description": "Documento vacío o inválido.",
        },
        413: {
            "description": "Documento demasiado grande.",
        },
        415: {
            "description": "Formato o MIME type no soportado.",
        },
        502: {
            "description": "Error al almacenar el documento en OCI.",
        },
    },
)
async def upload_document(
    response: Response,
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Documento PDF, Markdown (.md) "
                "o texto plano (.txt)."
            )
        ),
    ],
    document_service: Annotated[
        DocumentService,
        Depends(get_document_service),
    ],
    object_storage: Annotated[
        ObjectStoragePort,
        Depends(get_object_storage),
    ],
) -> DocumentCreatedResponse:
    """Valida, identifica y registra un documento."""
    _validate_document_type(
        file.filename,
        file.content_type,
    )

    try:
        uploaded_file = await save_upload(file)
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                "El archivo supera el máximo de "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        ) from exc

    temporary_path = Path(uploaded_file.path)

    if uploaded_file.size_bytes == 0:
        temporary_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El documento no puede estar vacío.",
        )

    try:
        registration = document_service.register_document(
            local_path=temporary_path,
            original_filename=uploaded_file.original_filename,
            content_type=uploaded_file.content_type,
            size_bytes=uploaded_file.size_bytes,
        )

        document = registration.document

        if document.oci_object_name is None:
            document = document_service.store_document(
                document_id=document.document_id,
                local_path=temporary_path,
                object_storage=object_storage,
            )

    except DocumentStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "El documento fue registrado, pero no pudo "
                "almacenarse en OCI Object Storage."
            ),
        ) from exc
    finally:
        temporary_path.unlink(missing_ok=True)

    if not registration.created:
        response.status_code = status.HTTP_200_OK

    return DocumentCreatedResponse(
        document_id=document.document_id,
        filename=document.original_filename,
        status=document.status,
        duplicate=not registration.created,
    )

@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar documento",
    description=(
        "Consulta la metadata y el estado actual de "
        "un documento mediante su document_id."
    ),
    responses={
        404: {
            "description": "Documento no encontrado.",
        },
    },
)
async def get_document(
    document_id: str,
    document_service: Annotated[
        DocumentService,
        Depends(get_document_service),
    ],
) -> DocumentResponse:
    """Consulta un documento previamente registrado."""
    try:
        document = document_service.get_document(
            document_id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return DocumentResponse(
        document_id=document.document_id,
        filename=document.original_filename,
        status=document.status,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )