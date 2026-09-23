from .rag.retriever import Retriever


class AgentV1:
    """
    Estructura inicial del agente.
    Coordina el acceso al conocimiento a través del Retriever,
    sin conocer los detalles internos del RAG (embeddings, vector store).
    """

    def __init__(self, vector_store):
        self.retriever = Retriever(vector_store)

    def answer(
        self,
        query: str,
        top_k: int = 5
    ):
        return self.retriever.retrieve(
            query=query,
            top_k=top_k
        )

    def answer_for_evaluation(
        self,
        case_id: str,
        query: str,
        top_k: int = 5
    ) -> dict:
        return self.retriever.retrieve_for_evaluation(
            case_id=case_id,
            query=query,
            top_k=top_k
        )