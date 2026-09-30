from .rag.retriever import RetrieverService

# Diccionario base para los formatos requeridos en Sprint 2
PROMPTS_BASE = {
    "quiz": "Genera un cuestionario interactivo de opción múltiple (mínimo 3 preguntas) asegurando incluir la respuesta correcta y una breve justificación.",
    "flashcards": "Genera 5 tarjetas de memorización (flashcards). Cada una debe tener un concepto clave en la cara frontal y su definición concisa en la cara trasera."
}

class AgentV1:
    """
    Estructura principal del agente. Coordina el acceso al conocimiento
    a través de RetrieverService y ensambla los prompts para el LLM.
    """

    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def answer(self, query: str, document_id: str, formato: str, perfil: str, nicho: str, nivel: str, top_k: int = 5) -> dict:
        # 1. Recuperación filtrada por document_id
        resultados = self.retriever.retrieve(query=query, top_k=top_k, document_id=document_id)
        
        if not resultados:
            return {"status": "no_results", "content": None, "sources_used": []}

        contexto_unificado = "\n\n".join([res.text for res in resultados])
        
        # Extraemos los IDs de los chunks usados para enviarlos en el JSON final (Requerimiento Data/IA)
        chunks_usados = [res.chunk_id for res in resultados]

        # 2. Ensamblar Prompt Dinámico
        instruccion_base = PROMPTS_BASE.get(formato.lower(), "Genera un resumen estructurado.")
        
        prompt_final = f"""
        INSTRUCCIÓN PRINCIPAL:
        {instruccion_base}
        
        REGLAS DE ADAPTACIÓN:
        - Perfil objetivo: {perfil}
        - Nicho temático: {nicho}
        - Nivel de detalle: {nivel}
        Adapta el lenguaje y la complejidad estrictamente a este perfil.

        CONTEXTO RECUPERADO:
        {contexto_unificado}
        """

        # 3. LLM Gen (Por ahora mock, luego conectaremos la API real de Gemini)
        texto_generado = self._llamar_llm(prompt_final)

        # 4. Salida atómica
        return {
            "status": "success",
            "content": texto_generado,
            "sources_used": chunks_usados
        }

    def _llamar_llm(self, prompt: str) -> str:
        """
        Simulación temporal de la llamada al modelo de IA.
        """
        return "[Simulación IA] Contenido adaptado exitosamente generado en base al perfil y contexto solicitados."

    def answer_for_evaluation(
        self,
        case_id: str,
        query: str,
        top_k: int = 5
    ) -> dict:
        """
        Mantiene el contrato intacto para la evaluación de retrieval (Sprint 1).
        """
        return self.retriever.retrieve_for_evaluation(
            case_id=case_id,
            query=query,
            top_k=top_k
        )