from data_ai.metrics.retrieval_metrics import precision_at_k, recall_at_k


def test_recall_at_k():
    relevant = ["CH_001"]
    retrieved = ["CH_002", "CH_001", "CH_003"]
    assert recall_at_k(relevant, retrieved, 3) == 1.0


def test_precision_at_k():
    relevant = ["CH_001"]
    retrieved = ["CH_002", "CH_001", "CH_003"]
    assert precision_at_k(relevant, retrieved, 3) == 1 / 3
