from typing import Any

from pydantic import ValidationError

from data_ai.schemas.retrieval import RetrievalContract


def validate_retrieval_contract(
    payload: dict[str, Any],
) -> list[str]:
    """
    Valida un payload contra Retrieval Contract v1
    utilizando el schema Pydantic oficial.

    Parameters
    ----------
    payload : dict[str, Any]
        Payload recibido desde el módulo de retrieval.

    Returns
    -------
    list[str]
        Lista de errores.
        Una lista vacía indica que el payload es válido.
    """

    try:
        RetrievalContract.model_validate(payload)
        return []

    except ValidationError as exc:
        errors: list[str] = []

        for error in exc.errors():
            location = ".".join(
                str(part)
                for part in error["loc"]
            )

            message = error["msg"]

            if location:
                errors.append(
                    f"{location}: {message}"
                )
            else:
                errors.append(message)

        return errors
