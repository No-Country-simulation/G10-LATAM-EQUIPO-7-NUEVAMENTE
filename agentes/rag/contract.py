from .models import SearchResult
from .vector_store import VectorStore  # única implementación (punto 2)
from .contract import (
    build_success_response,
    build_no_results_response,
    build_error_response,
)


class RetrieverService:
    """
    Interfaz principal de recuperación. Coordina VectorStore y arma
    las respuestas bajo el contrato v1.0 acordado con Data/IA.
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
        self._validate_query(query)
        self._validate_top_k(top_k)

        return self.vector_store.search(query=query, top_k=top_k)

    def retrieve_for_evaluation(
        self,
        case_id: str,
        query: str,
        top_k: int = 5
    ) -> dict:
        """
        Punto 3 de Tara: case_id ya NO tiene default, es obligatorio
        (evita IDs duplicados si el caller no lo manda).
        """

        if not case_id or not case_id.strip():
            raise ValueError(
                "case_id es obligatorio para evaluación y no puede "
                "estar vacío."
            )

        try:
            self._validate_query(query)
            self._validate_top_k(top_k)
            results = self.vector_store.search(query=query, top_k=top_k)
        except ValueError as exc:
            return build_error_response(
                case_id, query, top_k, "INVALID_INPUT", str(exc)
            )
        except Exception as exc:
            return build_error_response(
                case_id, query, top_k, "RETRIEVAL_FAILED", str(exc)
            )

        if not results:
            return build_no_results_response(case_id, query, top_k)

        return build_success_response(case_id, query, top_k, results)

    @staticmethod
    def _validate_query(query: str):
        if not query or not query.strip():
            raise ValueError("La consulta (query) no puede estar vacía.")

    @staticmethod
    def _validate_top_k(top_k: int):
        if top_k <= 0:
            raise ValueError("top_k debe ser mayor que 0.")