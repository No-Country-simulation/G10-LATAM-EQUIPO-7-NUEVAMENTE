import pandas as pd

from data_ai.metrics.retrieval_metrics import (
    recall_at_k,
    precision_at_k,
)

from data_ai.validators.retrieval_validator import (
    validate_retrieval_contract,
)


def parse_relevant_chunk_ids(
    value: str,
) -> list[str]:
    """Convierte relevant_chunk_ids a una lista."""

    if pd.isna(value):
        return []

    return [
        chunk_id.strip()
        for chunk_id in str(value).split(";")
        if chunk_id.strip()
    ]


def extract_retrieved_chunk_ids(
    payload: dict,
) -> list[str]:
    """Extrae chunk_id respetando el ranking."""

    errors = validate_retrieval_contract(
        payload
    )

    if errors:
        raise ValueError(
            "El payload no cumple el contrato:\n- "
            + "\n- ".join(errors)
        )

    if payload["status"] != "success":
        return []

    results = sorted(
        payload["results"],
        key=lambda result: result["rank"],
    )

    return [
        result["chunk_id"]
        for result in results
    ]


def evaluate_retrieval_case(
    payload: dict,
    ground_truth: pd.DataFrame,
) -> dict:
    """
    Evalúa un caso individual de retrieval contra el Ground Truth.

    Los casos con status='error' se registran,
    pero no participan en las métricas de calidad.
    """

    contract_errors = validate_retrieval_contract(payload)

    if contract_errors:
        raise ValueError(
            "Contrato de retrieval inválido:\n- "
            + "\n- ".join(contract_errors)
        )

    case_id = payload["case_id"]

    matched_rows = ground_truth.loc[
        ground_truth["case_id"] == case_id
    ]

    if matched_rows.empty:
        raise ValueError(
            f"case_id '{case_id}' no existe en Ground Truth."
        )

    if len(matched_rows) > 1:
        raise ValueError(
            f"case_id '{case_id}' aparece más de una vez "
            "en Ground Truth."
        )

    gt_row = matched_rows.iloc[0]

    relevant_ids = gt_row["relevant_chunk_ids_list"]
    retrieved_ids = extract_retrieved_chunk_ids(payload)

    status = payload["status"]

    if status == "error":
        error_data = payload["error"]

        return {
            "case_id": case_id,
            "categoria": gt_row["categoria"],
            "pregunta": gt_row["pregunta"],
            "status": status,
            "metric_eligible": False,
            "relevant_chunk_ids": relevant_ids,
            "retrieved_chunk_ids": [],
            "recall_at_3": None,
            "recall_at_5": None,
            "precision_at_3": None,
            "precision_at_5": None,
            "error_code": error_data["code"],
            "error_message": error_data["message"],
        }

    return {
        "case_id": case_id,
        "categoria": gt_row["categoria"],
        "pregunta": gt_row["pregunta"],
        "status": status,
        "metric_eligible": True,
        "relevant_chunk_ids": relevant_ids,
        "retrieved_chunk_ids": retrieved_ids,
        "recall_at_3": recall_at_k(
            relevant_ids,
            retrieved_ids,
            k=3,
        ),
        "recall_at_5": recall_at_k(
            relevant_ids,
            retrieved_ids,
            k=5,
        ),
        "precision_at_3": precision_at_k(
            relevant_ids,
            retrieved_ids,
            k=3,
        ),
        "precision_at_5": precision_at_k(
            relevant_ids,
            retrieved_ids,
            k=5,
        ),
        "error_code": None,
        "error_message": None,
    }


def evaluate_retrieval_batch(
    payloads: list[dict],
    ground_truth: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """
    Evalúa un lote de respuestas de retrieval.

    Detecta casos faltantes, extras, duplicados
    y errores de procesamiento.
    """

    expected_case_ids = set(
        ground_truth["case_id"].tolist()
    )

    received_case_ids = []
    evaluations = []
    batch_errors = []

    for index, payload in enumerate(payloads):

        case_id = payload.get("case_id")

        if case_id is not None:
            received_case_ids.append(case_id)

        try:
            evaluation = evaluate_retrieval_case(
                payload,
                ground_truth,
            )

            evaluations.append(evaluation)

        except Exception as exc:
            batch_errors.append({
                "index": index,
                "case_id": case_id,
                "error": str(exc),
            })

    duplicated_case_ids = sorted({
        case_id
        for case_id in received_case_ids
        if received_case_ids.count(case_id) > 1
    })

    received_case_id_set = set(
        received_case_ids
    )

    missing_case_ids = sorted(
        expected_case_ids
        - received_case_id_set
    )

    extra_case_ids = sorted(
        received_case_id_set
        - expected_case_ids
    )

    results_df = pd.DataFrame(
        evaluations
    )

    report = {
        "expected_cases": len(expected_case_ids),
        "received_payloads": len(payloads),
        "evaluated_cases": len(results_df),
        "missing_case_ids": missing_case_ids,
        "extra_case_ids": extra_case_ids,
        "duplicated_case_ids": duplicated_case_ids,
        "batch_errors": batch_errors,
    }

    return results_df, report