"""Endpoints HTTP relacionados con documentos."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.api.adaptation_execution import (
    execute_background_generation,
    execute_indexing,
)
from app.api.dependencies import (
    get_adaptation_orchestration_service,
    get_document_service,
    get_generated_format_query_service,
    get_object_storage,
    get_temporary_storage,
)
from app.application.adaptation_orchestration_service import (
    AdaptationOrchestrationService,
)
from app.application.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
)
from app.application.generated_format_query_service import (
    GeneratedFormatQueryDocumentNotFoundError,
    GeneratedFormatQueryService,
)
from app.core.config import settings
from app.domain.document import Document
from app.ports.object_storage_port import ObjectStoragePort
from app.ports.temporary_storage_port import (
    FileTooLargeError,
    TemporaryStoragePort,
)
from app.schemas.adaptation import (
    AdaptationNiche,
    AdaptationProfile,
    NonEmptyString,
)
from app.schemas.document import (
    DocumentCreatedResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.schemas.generated_format import (
    DocumentFormatsResponse,
    GeneratedFormatResponse,
)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

_CHUNK_SIZE = 1024 * 1024  # 1 MiB

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


async def _read_upload_chunks(
    file: UploadFile,
) -> AsyncIterator[bytes]:
    """Convierte un UploadFile HTTP en un flujo asíncrono de bytes."""
    while chunk := await file.read(
        _CHUNK_SIZE
    ):
        yield chunk


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


def _to_document_response(
    document: Document,
) -> DocumentResponse:
    """Convierte la entidad de dominio al contrato HTTP público."""
    return DocumentResponse(
        document_id=document.document_id,
        filename=document.original_filename,
        status=document.status,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post(
    "",
    response_model=DocumentCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar e indexar documento",
    description=(
        "Recibe un documento PDF, Markdown o TXT junto con "
        "el contexto pedagógico. Backend valida y almacena "
        "el archivo, completa la indexación RAG de forma "
        "síncrona y, una vez indexado, programa la generación "
        "de Quiz y Flashcards en segundo plano."
    ),
    responses={
        200: {
            "model": DocumentCreatedResponse,
            "description": (
                "Documento previamente registrado e indexado."
            ),
        },
        400: {
            "description": "Documento vacío o inválido.",
        },
        409: {
            "description": (
                "El documento no se encuentra en un estado "
                "válido para ejecutar la indexación."
            ),
        },
        413: {
            "description": "Documento demasiado grande.",
        },
        415: {
            "description": "Formato o MIME type no soportado.",
        },
        502: {
            "description": (
                "Error durante almacenamiento o indexación "
                "del documento."
            ),
        },
    },
)
async def upload_document(
    response: Response,
    background_tasks: BackgroundTasks,
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Documento PDF, Markdown (.md) "
                "o texto plano (.txt)."
            )
        ),
    ],
    profile: Annotated[
        AdaptationProfile,
        Form(
            description=(
                "Perfil educativo del destinatario."
            )
        ),
    ],
    niche: Annotated[
        AdaptationNiche,
        Form(
            description=(
                "Área temática o contexto de aplicación."
            )
        ),
    ],
    detail_level: Annotated[
        NonEmptyString,
        Form(
            description=(
                "Nivel de detalle esperado durante la generación."
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
    temporary_storage: Annotated[
        TemporaryStoragePort,
        Depends(get_temporary_storage),
    ],
    orchestration_service: Annotated[
        AdaptationOrchestrationService,
        Depends(
            get_adaptation_orchestration_service
        ),
    ],
    learning_objective: Annotated[
        NonEmptyString | None,
        Form(
            description=(
                "Objetivo de aprendizaje específico, "
                "cuando sea informado."
            )
        ),
    ] = None,
) -> DocumentCreatedResponse:
    """Carga, almacena e indexa un documento.

    La generación pedagógica se programa como tarea en segundo plano
    únicamente después de que la indexación RAG finaliza correctamente.
    """
    _validate_document_type(
        file.filename,
        file.content_type,
    )

    original_filename = (
        file.filename or "archivo"
    )
    content_type = file.content_type

    try:
        try:
            temporary_file = (
                await temporary_storage.save(
                    original_filename=original_filename,
                    chunks=_read_upload_chunks(file),
                )
            )
        except FileTooLargeError as exc:
            raise HTTPException(
                status_code=(
                    status.HTTP_413_CONTENT_TOO_LARGE
                ),
                detail=(
                    "El archivo supera el máximo de "
                    f"{settings.MAX_UPLOAD_SIZE_MB} MB."
                ),
            ) from exc
    finally:
        await file.close()

    temporary_path = temporary_file.path

    if temporary_file.size_bytes == 0:
        temporary_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El documento no puede estar vacío.",
        )

    try:
        registration = (
            document_service.register_document(
                local_path=temporary_path,
                original_filename=original_filename,
                content_type=content_type,
                size_bytes=temporary_file.size_bytes,
            )
        )

        document = registration.document

        if document.oci_object_name is None:
            document = (
                document_service.store_document(
                    document_id=document.document_id,
                    local_path=temporary_path,
                    object_storage=object_storage,
                )
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
        temporary_path.unlink(
            missing_ok=True
        )

    await execute_indexing(
        orchestration_service=orchestration_service,
        document_id=document.document_id,
    )

    current_document = (
        document_service.get_document(
            document.document_id
        )
    )

    background_tasks.add_task(
        execute_background_generation,
        orchestration_service=orchestration_service,
        document_id=current_document.document_id,
        profile=profile,
        niche=niche,
        detail_level=detail_level,
        learning_objective=learning_objective,
    )

    if not registration.created:
        response.status_code = (
            status.HTTP_200_OK
        )

    return DocumentCreatedResponse(
        document_id=current_document.document_id,
        filename=current_document.original_filename,
        status=current_document.status,
        duplicate=not registration.created,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar documentos activos",
    description=(
        "Retorna los documentos persistidos y disponibles "
        "para consulta desde la biblioteca."
    ),
)
async def list_documents(
    document_service: Annotated[
        DocumentService,
        Depends(get_document_service),
    ],
) -> DocumentListResponse:
    """Obtiene los documentos activos de la biblioteca."""
    documents = (
        document_service.list_active_documents()
    )

    return DocumentListResponse(
        documents=[
            _to_document_response(
                document
            )
            for document in documents
        ]
    )


@router.get(
    "/{document_id}/formats",
    response_model=DocumentFormatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar formatos generados",
    description=(
        "Retorna Quiz y Flashcards persistidos para "
        "un documento junto con su estado agregado."
    ),
    responses={
        404: {
            "description": (
                "Documento no encontrado."
            ),
        },
    },
)
async def get_document_formats(
    document_id: str,
    generated_format_query_service: Annotated[
        GeneratedFormatQueryService,
        Depends(
            get_generated_format_query_service
        ),
    ],
) -> DocumentFormatsResponse:
    """Consulta los formatos pedagógicos de un documento."""
    try:
        result = (
            generated_format_query_service
            .get_document_formats(
                document_id
            )
        )

    except (
        GeneratedFormatQueryDocumentNotFoundError
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc

    formats = (
        {
            generated_format.format_type: (
                GeneratedFormatResponse
                .from_domain(
                    generated_format
                )
            )
            for generated_format
            in result.formats
        }
        if result.formats
        else None
    )

    return DocumentFormatsResponse(
        document_id=result.document_id,
        status=result.status,
        formats=formats,
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

    return _to_document_response(
        document
    )