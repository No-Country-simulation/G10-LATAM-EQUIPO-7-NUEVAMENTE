import os
import csv
import json
from agentes.agent_v1 import AgentV1
from agentes.rag.vector_store import VectorStore
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.chunks_loader import load_chunks_from_csv

def generar_lote_resultados():
    print("--- INICIANDO GENERACIÓN DEL LOTE DE EVALUACIÓN ---")
    
    # 1. Preparar Agente y Base Vectorial
    embedding_service = MultilingualEmbedding()
    vector_store = VectorStore(
        path="./chroma_test_db", 
        collection_name="test_collection", 
        embedding_service=embedding_service
    )
    
    chunks_path = "agentes/chunks_v1.csv"
    if os.path.exists(chunks_path):
        vector_store.add_chunks(load_chunks_from_csv(chunks_path))
        
    agent = AgentV1(vector_store=vector_store)
    
    # 2. Leer los 50 casos del ground truth
    gt_path = "agentes/ground_truth_v1.csv"
    resultados = []
    
    with open(gt_path, mode="r", encoding="utf-8-sig") as f:
        primera_linea = f.readline()
        f.seek(0)
        delimitador = ";" if ";" in primera_linea else ","
        reader = csv.DictReader(f, delimiter=delimitador)
        
        for fila in reader:
            case_id = fila.get("case_id")
            pregunta = fila.get("pregunta")
            
            # Saltamos si hay filas vacías por error en el CSV
            if not case_id or not pregunta:
                continue 
                
            print(f"Procesando caso: {case_id}...")
            
            # 3. Consultar al agente usando SOLO case_id y pregunta
            respuesta = agent.answer_for_evaluation(
                case_id=case_id,
                query=pregunta,
                top_k=5
            )
            
            # --- AJUSTE ESTRICTO AL CONTRATO V1 ---
            if respuesta.get("status") == "success":
                respuesta["error"] = None
            # --------------------------------------
            
            resultados.append(respuesta)
            
    # 4. Guardar todo en formato JSON
    output_path = "agentes/retrieval_results_agentes_v1.json"
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(resultados, out_file, ensure_ascii=False, indent=4)
        
    print(f"\n--- ¡LOTE GENERADO CON ÉXITO! ---")
    print(f"Se procesaron {len(resultados)} casos.")
    print(f"Archivo guardado en: {output_path}")

if __name__ == "__main__":
    generar_lote_resultados()