"""Schemas provisionales para solicitudes de adaptación educativa."""

from pydantic import Field

from app.domain.enums import ProcessStatus
from app.schemas.common import BaseSchema


class AdaptationRequest(BaseSchema):
    """Solicitud mínima para adaptar un documento.

    Los valores específicos permitidos para perfil, formato, nicho y
    nivel de detalle se definirán cuando se cierre el contrato con
    Frontend y RAG/Agentes.
    """

    document_id: str = Field(
        min_length=1,
        description="Documento que será utilizado como fuente.",
    )
    profile: str = Field(
        min_length=1,
        description="Perfil del destinatario.",
    )
    output_format: str = Field(
        min_length=1,
        description="Formato pedagógico solicitado.",
    )
    niche: str = Field(
        min_length=1,
        description="Sector o contexto de aplicación.",
    )
    detail_level: str = Field(
        min_length=1,
        description="Nivel de detalle esperado.",
    )


class AdaptationAcceptedResponse(BaseSchema):
    """Respuesta inicial después de aceptar una adaptación."""

    process_id: str
    document_id: str
    status: ProcessStatus