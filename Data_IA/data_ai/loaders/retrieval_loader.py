from pathlib import Path
import json


def load_retrieval_batch(
    path: Path,
) -> list[dict]:
    """
    Carga resultados de retrieval desde un archivo JSON.

    Parameters
    ----------
    path : Path
        Ruta al archivo JSON.

    Returns
    -------
    list[dict]
        Lista de respuestas compatibles con
        Retrieval Contract v1.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo de retrieval: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "El archivo de retrieval debe contener "
            "una lista de payloads."
        )

    return data