"""Excepciones HTTP públicas con código funcional estable."""

from fastapi import HTTPException

from app.core.error_codes import ErrorCode


class APIHTTPException(HTTPException):
    """Error HTTP controlado que conserva un código funcional público.

    Args:
        status_code: Código de estado HTTP.
        code: Identificador funcional estable consumible por Frontend.
        detail: Mensaje seguro y legible para el cliente.
        headers: Headers HTTP opcionales.

    El nombre de la excepción Python nunca forma parte del contrato público.
    """

    def __init__(
        self,
        *,
        status_code: int,
        code: ErrorCode,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )
        self.code = code
