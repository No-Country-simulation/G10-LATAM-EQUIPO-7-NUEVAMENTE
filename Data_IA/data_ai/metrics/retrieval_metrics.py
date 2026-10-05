"""Métricas reproducibles para evaluar retrieval contra Ground Truth."""

from collections.abc import Iterable


def recall_at_k(
    relevant_ids: Iterable[str],
    retrieved_ids: Iterable[str],
    k: int,
) -> float:
    """Calcula Recall@K."""
    if k <= 0:
        raise ValueError("k debe ser mayor que 0.")

    relevant = set(relevant_ids)
    if not relevant:
        return 0.0

    retrieved = list(retrieved_ids)[:k]
    return len(relevant.intersection(retrieved)) / len(relevant)


def precision_at_k(
    relevant_ids: Iterable[str],
    retrieved_ids: Iterable[str],
    k: int,
) -> float:
    """Calcula Precision@K."""
    if k <= 0:
        raise ValueError("k debe ser mayor que 0.")

    relevant = set(relevant_ids)
    retrieved = list(retrieved_ids)[:k]

    if not retrieved:
        return 0.0

    return len(relevant.intersection(retrieved)) / k
