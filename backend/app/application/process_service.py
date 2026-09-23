"""Casos de uso básicos relacionados con procesos."""

from uuid import uuid4

from app.domain.process import Process


class ProcessService:
    """Gestiona la creación inicial de procesos de BackendAPI.

    La persistencia de procesos se incorporará cuando se defina el contrato
    correspondiente.
    """

    def create_process(self, document_id: str) -> Process:
        """Crea un nuevo proceso asociado a un documento."""
        return Process(
            process_id=f"process_{uuid4().hex}",
            document_id=document_id,
        )