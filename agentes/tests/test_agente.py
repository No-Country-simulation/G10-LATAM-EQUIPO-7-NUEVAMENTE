import os
import csv
from agentes.agent_v1 import AgentV1
from agentes.rag.vector_store import VectorStore
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.chunks_loader import load_chunks_from_csv

# Rutas oficiales versionadas por Data/IA. Deben funcionar desde un
# clone limpio del repo, sin copias locales del CSV en otro lado.
CHUNKS_PATH = "Data_IA/data/evaluation/chunks_v1.csv"
GROUND_TRUTH_PATH = "Data_IA/data/evaluation/ground_truth_v1.csv"


def test_pipeline_con_ground_truth():
    print("\n--- INICIANDO PRUEBA FUNCIONAL E2E CON GROUND TRUTH ---")

    # 1. Levantar dependencias y agente
    embedding_service = MultilingualEmbedding()
    vector_store = VectorStore(
        path="./chroma_test_db",
        collection_name="test_collection",
        embedding_service=embedding_service
    )
    agent = AgentV1(vector_store=vector_store)

    # 2. Cargar la base de datos con chunks_v1.csv oficial
    assert os.path.exists(CHUNKS_PATH), f"Error: No se encontró {CHUNKS_PATH}"
    vector_store.add_chunks(load_chunks_from_csv(CHUNKS_PATH))

    # 3. Leer el examen oficial de Data/IA (lectura robusta)
    assert os.path.exists(GROUND_TRUTH_PATH), f"Error: No se encontró {GROUND_TRUTH_PATH}"

    # utf-8-sig elimina caracteres invisibles de Windows al inicio del archivo
    with open(GROUND_TRUTH_PATH, mode="r", encoding="utf-8-sig") as f:
        # Detectar automáticamente si usa coma o punto y coma
        primera_linea = f.readline()
        f.seek(0)
        delimitador = ";" if ";" in primera_linea else ","

        reader = csv.DictReader(f, delimiter=delimitador)
        caso_real = next(reader)

    case_id_oficial = caso_real.get("case_id")
    pregunta_oficial = caso_real.get("pregunta")

    print(f"\n[!] Columnas detectadas: {list(caso_real.keys())}")
    print(f"[!] Evaluando caso oficial: {case_id_oficial}")
    print(f"[!] Pregunta real: {pregunta_oficial}")

    # 4. Procesar por el pipeline estricto
    resultado_eval = agent.answer_for_evaluation(
        case_id=case_id_oficial,
        query=pregunta_oficial,
        top_k=5
    )

    # 5. Validar cumplimiento del contrato de Data/IA
    print(f"-> Estado retornado: {resultado_eval.get('status')}")
    assert resultado_eval.get("status") in ["success", "no_results"], "Fallo en el status del contrato"
    assert resultado_eval.get("case_id") == case_id_oficial, "El case_id retornado no coincide"
    assert "contract_version" in resultado_eval, "Falta la versión del contrato"
    assert "error" in resultado_eval, "Falta la llave 'error' en el contrato"
    assert resultado_eval.get("error") is None, "error debe ser null cuando status no es 'error'"

    print("--- ¡EL PIPELINE SUPERÓ EL CASO DEL GROUND TRUTH! ---")