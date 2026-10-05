import os
import csv
import json
from agentes.agent_v1 import AgentV1
from agentes.rag.vector_store import VectorStore
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.chunks_loader import load_chunks_from_csv

# Rutas oficiales versionadas por Data/IA (funcionan desde un clone
# limpio del repo, sin depender de copias locales sueltas).
CHUNKS_PATH = "Data_IA/data/evaluation/chunks_v1.csv"
GROUND_TRUTH_PATH = "Data_IA/data/evaluation/ground_truth_v1.csv"


def generar_lote_resultados():
    print("--- INICIANDO GENERACIÓN DEL LOTE DE EVALUACIÓN ---")

    # 1. Preparar Agente y Base Vectorial
    embedding_service = MultilingualEmbedding()
    vector_store = VectorStore(
        path="./chroma_test_db",
        collection_name="test_collection",
        embedding_service=embedding_service
    )

    if not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(f"No se encontró {CHUNKS_PATH}")

    vector_store.add_chunks(load_chunks_from_csv(CHUNKS_PATH))

    agent = AgentV1(vector_store=vector_store)

    # 2. Leer los 50 casos del ground truth
    if not os.path.exists(GROUND_TRUTH_PATH):
        raise FileNotFoundError(f"No se encontró {GROUND_TRUTH_PATH}")

    resultados = []

    with open(GROUND_TRUTH_PATH, mode="r", encoding="utf-8-sig") as f:
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

            # 3. Consultar al agente usando SOLO case_id y pregunta.
            # El contrato completo (incluido "error": null) lo arma
            # answer_for_evaluation() -> RetrieverService -> contract.py.
            # Este script no toca ni completa el payload manualmente.
            respuesta = agent.answer_for_evaluation(
                case_id=case_id,
                query=pregunta,
                top_k=5
            )
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