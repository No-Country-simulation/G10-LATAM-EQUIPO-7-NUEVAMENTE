from typing import Any


VALID_STATUSES = {
    "success",
    "no_results",
    "error",
}


def validate_retrieval_contract(
    payload: dict[str, Any],
) -> list[str]:
    """
    Valida una respuesta contra Retrieval Contract v1.

    Returns
    -------
    list[str]
        Lista de errores. Una lista vacía indica
        que el payload cumple el contrato.
    """

    errors = []

    required_fields = [
        "contract_version",
        "case_id",
        "query",
        "top_k",
        "score_type",
        "status",
        "results",
        "error",
    ]

    for field in required_fields:
        if field not in payload:
            errors.append(
                f"Falta el campo obligatorio: {field}"
            )

    if errors:
        return errors

    if payload["contract_version"] != "1.0":
        errors.append(
            "contract_version debe ser '1.0'."
        )

    if (
        not isinstance(payload["case_id"], str)
        or not payload["case_id"].strip()
    ):
        errors.append(
            "case_id debe ser un string no vacío."
        )

    if (
        not isinstance(payload["query"], str)
        or not payload["query"].strip()
    ):
        errors.append(
            "query debe ser un string no vacío."
        )

    if payload["top_k"] != 5:
        errors.append(
            "Para Retrieval v1, top_k debe ser 5."
        )

    if (
        not isinstance(payload["score_type"], str)
        or not payload["score_type"].strip()
    ):
        errors.append(
            "score_type debe ser un string no vacío."
        )

    if payload["status"] not in VALID_STATUSES:
        errors.append(
            f"status inválido: {payload['status']}"
        )

    if not isinstance(payload["results"], list):
        errors.append(
            "results debe ser una lista."
        )
        return errors

    status = payload["status"]

    if status == "success":

        if not payload["results"]:
            errors.append(
                "status='success' requiere al menos un resultado."
            )

        if payload["error"] is not None:
            errors.append(
                "status='success' requiere error=null."
            )

    elif status == "no_results":

        if payload["results"]:
            errors.append(
                "status='no_results' requiere results=[]."
            )

        if payload["error"] is not None:
            errors.append(
                "status='no_results' requiere error=null."
            )

    elif status == "error":

        if payload["results"]:
            errors.append(
                "status='error' requiere results=[]."
            )

        error_data = payload["error"]

        if not isinstance(error_data, dict):
            errors.append(
                "status='error' requiere un objeto error."
            )
        else:

            if not error_data.get("code"):
                errors.append(
                    "error.code es obligatorio."
                )

            if not error_data.get("message"):
                errors.append(
                    "error.message es obligatorio."
                )

    for index, result in enumerate(
        payload["results"],
        start=1,
    ):

        if not isinstance(result, dict):
            errors.append(
                f"results[{index}] debe ser un objeto."
            )
            continue

        required_result_fields = [
            "rank",
            "chunk_id",
            "document_id",
            "score",
            "text",
        ]

        for field in required_result_fields:

            if field not in result:
                errors.append(
                    f"results[{index}] no contiene '{field}'."
                )

        if (
            "rank" in result
            and result["rank"] != index
        ):
            errors.append(
                f"results[{index}] tiene "
                f"rank={result['rank']}, "
                f"pero se esperaba rank={index}."
            )

        if (
            "score" in result
            and not isinstance(
                result["score"],
                (int, float),
            )
        ):
            errors.append(
                f"results[{index}].score debe ser numérico."
            )

    return errors