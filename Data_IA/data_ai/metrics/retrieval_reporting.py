import pandas as pd


def get_case_result(
    results_df: pd.DataFrame,
    case_id: str,
) -> pd.Series:
    """
    Obtiene un único resultado por case_id.
    """

    matches = results_df.loc[
        results_df["case_id"] == case_id
    ]

    if matches.empty:
        raise ValueError(
            f"No existe resultado para case_id '{case_id}'."
        )

    if len(matches) > 1:
        raise ValueError(
            f"Existen múltiples resultados para '{case_id}'."
        )

    return matches.iloc[0]


def build_metric_summary(
    results_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula métricas promedio únicamente
    sobre casos elegibles.
    """

    metric_columns = [
        "recall_at_3",
        "recall_at_5",
        "precision_at_3",
        "precision_at_5",
    ]

    eligible_df = results_df.loc[
        results_df["metric_eligible"]
    ]

    if eligible_df.empty:
        return pd.DataFrame(
            columns=["metric", "mean"]
        )

    return (
        eligible_df[metric_columns]
        .mean()
        .rename("mean")
        .reset_index()
        .rename(columns={"index": "metric"})
    )


def build_status_summary(
    results_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Resume cantidad y porcentaje de casos
    por status.
    """

    if results_df.empty:
        return pd.DataFrame(
            columns=[
                "status",
                "count",
                "percentage",
            ]
        )

    summary = (
        results_df["status"]
        .value_counts(dropna=False)
        .rename_axis("status")
        .reset_index(name="count")
    )

    summary["percentage"] = (
        summary["count"]
        / len(results_df)
        * 100
    )

    return summary


def build_category_summary(
    results_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula métricas promedio por categoría,
    excluyendo errores técnicos.
    """

    eligible_df = results_df.loc[
        results_df["metric_eligible"]
    ].copy()

    metric_columns = [
        "recall_at_3",
        "recall_at_5",
        "precision_at_3",
        "precision_at_5",
    ]

    if eligible_df.empty:
        return pd.DataFrame(
            columns=[
                "categoria",
                *metric_columns,
            ]
        )

    return (
        eligible_df
        .groupby("categoria")[metric_columns]
        .mean()
        .reset_index()
    )


def print_batch_report(
    report: dict,
) -> None:
    """
    Muestra un resumen legible del lote evaluado.
    """

    print(
        f"Casos esperados: "
        f"{report['expected_cases']}"
    )

    print(
        f"Payloads recibidos: "
        f"{report['received_payloads']}"
    )

    print(
        f"Casos evaluados: "
        f"{report['evaluated_cases']}"
    )

    print(
        f"Casos faltantes: "
        f"{len(report['missing_case_ids'])}"
    )

    print(
        f"Casos extra: "
        f"{len(report['extra_case_ids'])}"
    )

    print(
        f"Case ID duplicados: "
        f"{len(report['duplicated_case_ids'])}"
    )

    print(
        f"Errores de procesamiento: "
        f"{len(report['batch_errors'])}"
    )