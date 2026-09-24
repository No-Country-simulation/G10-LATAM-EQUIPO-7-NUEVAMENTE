"""
Contrato de retrieval v1.0 acordado con Data/IA para el cálculo de
Recall@3, Recall@5, Precision@3, Precision@5.
 
Toda respuesta (success, no_results, error) trae siempre la misma
forma de llaves, incluyendo "error" (null cuando no aplica), para
que el consumidor del JSON no tenga que manejar formas distintas
según el status.
"""

from .models import SearchResult

CONTRACT_VERSION = "1.0"
SCORE_TYPE = "cosine_similarity"


def build_success_response(
    case_id: str,
    query: str,
    top_k: int,
    results: list[SearchResult]
) -> dict:

    return {
        "contract_version": CONTRACT_VERSION,
        "case_id": case_id,
        "query": query,
        "top_k": top_k,
        "score_type": SCORE_TYPE,
        "status": "success",
        "results": [
            {
                "rank": rank,
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "score": round(result.score, 4),
                "text": result.text,
                "metadata": result.metadata
            }
            for rank, result in enumerate(results, start=1)
        ],
        "error": None
    }


def build_no_results_response(case_id: str, query: str, top_k: int) -> dict:

    return {
        "contract_version": CONTRACT_VERSION,
        "case_id": case_id,
        "query": query,
        "top_k": top_k,
        "score_type": SCORE_TYPE,
        "status": "no_results",
        "results": [],
        "error": None
    }


def build_error_response(
    case_id: str,
    query: str,
    top_k: int,
    code: str,
    message: str
) -> dict:

    return {
        "contract_version": CONTRACT_VERSION,
        "case_id": case_id,
        "query": query,
        "top_k": top_k,
        "score_type": SCORE_TYPE,
        "status": "error",
        "results": [],
        "error": {
            "code": code,
            "message": message
        }
    }