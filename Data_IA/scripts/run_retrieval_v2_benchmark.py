from pathlib import Path
import sys
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.vector_store import VectorStore
from agentes.rag.pipeline import ingest_ground_truth_v1
from agentes.agent_v1 import AgentV1


GROUND_TRUTH_PATH = (
    ROOT / "Data_IA" / "data" / "evaluation" / "ground_truth_v2.csv"
)

CHUNKS_PATH = (
    ROOT / "Data_IA" / "data" / "evaluation" / "chunks_v1.csv"
)

OUTPUT_PATH = (
    ROOT
    / "Data_IA"
    / "data"
    / "evaluation"
    / "input"
    / "retrieval_results_agentes_v2.json"
)

CHROMA_PATH = ROOT / ".benchmark_chroma_v2"


def main():
    print("Cargando Ground Truth...")

    gt = pd.read_csv(
        GROUND_TRUTH_PATH,
        encoding="utf-8-sig",
    )

    assert len(gt) == 50
    assert gt["case_id"].nunique() == 50

    print("Inicializando embeddings...")

    embedding_service = MultilingualEmbedding()

    print("Inicializando Vector Store V2...")

    vector_store = VectorStore(
        path=str(CHROMA_PATH),
        collection_name="benchmark_retrieval_v2",
        embedding_service=embedding_service,
    )

    print("Cargando corpus congelado...")

    ingest_result = ingest_ground_truth_v1(
        str(CHUNKS_PATH),
        vector_store,
    )

    print("Chunks cargados:", ingest_result)

    agent = AgentV1(vector_store)

    batch = []

    for index, row in gt.iterrows():
        case_id = str(row["case_id"]).strip()
        query = str(row["pregunta"]).strip()
        document_id = str(row["document_id"]).strip()

        print(
            f"[{index + 1:02d}/50] "
            f"{case_id} | document_id={document_id}"
        )

        metadata_filters = {
            "document_id": document_id
        }

        response = agent.answer_for_evaluation(
            case_id=case_id,
            query=query,
            top_k=5,
            metadata_filters=metadata_filters,
        )

        # Trazabilidad adicional para el notebook V2
        response["filter_mode"] = "document_id"
        response["filter_trace"] = {
            "document_id": document_id
        }

        batch.append(response)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            batch,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("Benchmark terminado.")
    print("Casos generados:", len(batch))
    print("Salida:", OUTPUT_PATH)


if __name__ == "__main__":
    main()