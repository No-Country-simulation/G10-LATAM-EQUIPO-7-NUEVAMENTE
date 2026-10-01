import uuid
from .rag.retriever import RetrieverService

PROMPTS_BASE = {
    "quiz": "Genera un cuestionario interactivo de opción múltiple (mínimo 3 preguntas) asegurando incluir la respuesta correcta y una breve justificación.",
    "flashcards": "Genera 5 tarjetas de memorización (flashcards). Cada una debe tener un concepto clave en la cara frontal y su definición concisa en la cara trasera."
}

class AgentV1:
    def __init__(self, vector_store):
        self.retriever = RetrieverService(vector_store)

    def answer(self, query: str, document_id: str, formato: str, perfil: str, nicho: str, nivel: str, learning_objective: str = None, top_k: int = 5) -> dict:
        # 1. Recuperación
        resultados = self.retriever.retrieve(query=query, top_k=top_k, document_id=document_id)
        
        if not resultados:
            return {
                "status": "no_results", 
                "content": None, 
                "sources_used": [],
                "error_message": "No se encontró contexto suficiente en el documento."
            }

        contexto_unificado = "\n\n".join([res.text for res in resultados])
        
        # 2. Construcción de evidencia completa
        chunks_usados = []
        for index, res in enumerate(resultados):
            chunks_usados.append({
                "rank": index + 1,
                "chunk_id": res.chunk_id,
                "document_id": getattr(res, "document_id", document_id),
                "score": getattr(res, "score", 0.0),
                "text": res.text
            })

        # 3. Ensamblar Prompt Dinámico
        instruccion_base = PROMPTS_BASE.get(formato.lower(), "Genera un resumen estructurado.")
        
        prompt_final = f"""
        INSTRUCCIÓN PRINCIPAL:
        {instruccion_base}
        
        REGLAS DE ADAPTACIÓN:
        - Perfil objetivo: {perfil}
        - Nicho temático: {nicho}
        - Nivel de detalle: {nivel}
        """
        if learning_objective:
            prompt_final += f"- Objetivo de aprendizaje: {learning_objective}\n"
            
        prompt_final += f"""
        Adapta el lenguaje y la complejidad estrictamente a este perfil.

        CONTEXTO RECUPERADO:
        {contexto_unificado}
        """

        # 4. LLM Gen
        texto_generado = self._llamar_llm(prompt_final, formato)

        # 5. Salida atómica
        return {
            "status": "success",
            "content": texto_generado,
            "sources_used": chunks_usados,
            "error_message": None
        }

    def _llamar_llm(self, prompt: str, formato: str) -> dict:
        """Simulación temporal con IDs, Títulos e Instrucciones."""
        if formato.lower() == "quiz":
            return {
                "title": "[Simulación] Cuestionario de Validación",
                "instructions": "Lee cuidadosamente cada pregunta y selecciona la opción correcta basándote en el documento.",
                "questions": [
                    {
                        "question_id": f"q_{uuid.uuid4().hex[:8]}",
                        "question": "[Simulación] ¿Cuál es un concepto central del documento?",
                        "options": ["A) Respuesta correcta", "B) Distractor 1", "C) Distractor 2", "D) Distractor 3"],
                        "correct_answer": "A) Respuesta correcta",
                        "explanation": "Justificación simulada basada en el contexto recuperado."
                    }
                ]
            }
        elif formato.lower() == "flashcards":
            return {
                "title": "[Simulación] Tarjetas de Memoria",
                "instructions": "Utiliza estas tarjetas para repasar los conceptos clave.",
                "cards": [
                    {
                        "card_id": f"c_{uuid.uuid4().hex[:8]}",
                        "front": "[Simulación] Concepto Clave Extraído",
                        "back": "Definición concisa generada por la IA basada en el contexto."
                    }
                ]
            }
        
        return {"error": "Formato no soportado."}

    def answer_for_evaluation(self, case_id: str, query: str, top_k: int = 5) -> dict:
        return self.retriever.retrieve_for_evaluation(case_id=case_id, query=query, top_k=top_k)