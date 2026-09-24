import os
from agentes.agent_v1 import AgentV1
from agentes.rag.vector_store import VectorStore
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.chunks_loader import load_chunks_from_csv

def test_pipeline_completo():
    print("--- INICIANDO PRUEBA FUNCIONAL DEL AGENTE ---")

    # 0. Instanciar las dependencias requeridas por tu arquitectura
    print("[0] Preparando dependencias (Embeddings y Vector Store)...")
    embedding_service = MultilingualEmbedding()
    vector_store = VectorStore(
        path="./chroma_test_db", 
        collection_name="test_collection", 
        embedding_service=embedding_service
    )

    # 1. Importación e instanciación de AgentV1 (ahora sí le pasamos el vector_store)
    print("[1] Instanciando AgentV1...")
    agent = AgentV1(vector_store=vector_store)
    assert agent is not None, "El agente no se pudo instanciar."

    # 2. Carga real de chunks_v1.csv al Vector Store
    csv_path = "chunks_v1.csv" # Asegúrate de que el CSV esté en la raíz del proyecto
    if os.path.exists(csv_path):
        print(f"[2] Cargando chunks desde {csv_path}...")
        chunks = load_chunks_from_csv(csv_path)
        # Cargamos los chunks directamente en el vector store
        vector_store.add_chunks(chunks)
        print(f"-> Se cargaron {len(chunks)} chunks exitosamente.")
    else:
        print(f"[!] Advertencia: No se encontró el archivo {csv_path} en la raíz.")

    # 3. Ejecución de answer()
    print("[3] Probando método general answer()...")
    respuesta_general = agent.answer(query="¿Qué es Kubernetes?")
    print(f"Respuesta general obtenida: {str(respuesta_general)[:100]}...")

    # 4. Ejecución de answer_for_evaluation() con un caso del Ground Truth
    print("[4] Probando answer_for_evaluation() para métricas de Data/IA...")
    eval_resultado = agent.answer_for_evaluation(
        case_id="CLD-ES-001-Q01",
        query="¿Qué es Kubernetes?",
        top_k=5
    )
    print(f"Estado del contrato recibido: {eval_resultado.get('status')}")
    
    # 5. Validación de respuestas success y no_results
    assert eval_resultado.get("status") in ["success", "no_results"], "El estado del contrato es inválido."
    print("-> Validación de estados 'success' / 'no_results' pasada con éxito.")

    print("--- ¡TODAS LAS PRUEBAS FUNCIONALES PASARON CORRECTAMENTE! ---")

if __name__ == "__main__":
    test_pipeline_completo()