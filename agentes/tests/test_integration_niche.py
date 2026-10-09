import os
import re
import uuid
import warnings
import unicodedata

import pytest
from dotenv import load_dotenv

# Carga de entorno antes de importar la lógica de negocio
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

from fastapi.testclient import TestClient  # noqa: E402
from agentes.api import app, agent, vector_store  # noqa: E402

client = TestClient(app)

skip_if_no_key = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "api_key_aqui",
    reason="Se requiere GEMINI_API_KEY real en el .env."
)


@pytest.fixture
def doc_id_manager():
    """
    Genera un ID único y limpia la base vectorial al terminar.
    Emite una alerta visible si no puede limpiar.
    """
    doc_id = f"test_niche_{uuid.uuid4().hex[:6]}"
    yield doc_id

    try:
        if hasattr(vector_store, "collection"):
            vector_store.collection.delete(where={"document_id": doc_id})
        elif hasattr(vector_store, "delete"):
            vector_store.delete(document_id=doc_id)
        else:
            warnings.warn(f"No se encontró un método para limpiar {doc_id} del VectorStore.")
    except Exception as e:
        warnings.warn(f"Fallo al limpiar ChromaDB en el teardown: {type(e).__name__}: {e}")


def norm(items):
    s = " ".join(items).lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def hits(items, kws):
    """Cuenta coincidencias de keywords (prefijo de palabra) sobre texto normalizado."""
    t = norm(items)
    return sum(len(re.findall(r"\b" + re.escape(k), t)) for k in kws)


@skip_if_no_key
def test_e2e_autonomous_differential_niche(doc_id_manager):
    """
    Indexa por el endpoint real y verifica directo contra el agente que el nicho
    inclina la extracción de conceptos hacia su tema (dominancia temática).
    """
    doc_id = doc_id_manager

    texto_prueba = (
        "El sistema evalúa modelos de lenguaje avanzados en entornos corporativos. "
        "Por un lado, contiene módulos de cifrado AES-256 para proteger datos sensibles "
        "contra vulnerabilidades externas, garantizando una ciberseguridad robusta y "
        "criptografía de punta para la información clasificada.\n\n"
        "Por otro lado, incluye un motor de cálculo de métricas financieras diseñado "
        "para evaluar la rentabilidad continua, el retorno de inversión y los "
        "márgenes de ganancia trimestrales, optimizando las finanzas de las operaciones."
    )

    r_index = client.post(
        "/api/v1/index",
        data={"document_id": doc_id},
        files={"file": ("dummy.txt", texto_prueba.encode("utf-8"), "text/plain")}
    )
    assert r_index.status_code == 200, f"Falló indexación HTTP {r_index.status_code}: {r_index.text}"

    query_generica = "Extrae los conceptos principales"

    resultado_a = agent.extract_learning_metadata(
        query=query_generica, document_id=doc_id, niche="ciberseguridad y cifrado"
    )
    resultado_b = agent.extract_learning_metadata(
        query=query_generica, document_id=doc_id, niche="finanzas y rentabilidad"
    )

    assert resultado_a["status"] == "success", f"Fallo interno A: {resultado_a}"
    assert resultado_b["status"] == "success", f"Fallo interno B: {resultado_b}"

    conceptos_a = resultado_a["content"]["key_concepts"]
    conceptos_b = resultado_b["content"]["key_concepts"]

    assert len(conceptos_a) > 0, "Gemini devolvió una lista vacía para A."
    assert len(conceptos_b) > 0, "Gemini devolvió una lista vacía para B."

    KW_A = ("cifrado", "seguridad", "ciberseguridad", "criptograf", "proteg", "vulnerabilidad")
    KW_B = ("rentabilidad", "finanz", "metric", "inversion")

    a_cyber, a_fin = hits(conceptos_a, KW_A), hits(conceptos_a, KW_B)
    b_cyber, b_fin = hits(conceptos_b, KW_A), hits(conceptos_b, KW_B)

    assert a_cyber > a_fin, f"Nicho A no dominó en cyber. Hits(Cyber:{a_cyber}, Fin:{a_fin}). Conceptos: {conceptos_a}"
    assert b_fin > b_cyber, f"Nicho B no dominó en finanzas. Hits(Cyber:{b_cyber}, Fin:{b_fin}). Conceptos: {conceptos_b}"


@skip_if_no_key
def test_api_generate_wiring(doc_id_manager):
    """
    Wiring E2E de /generate: indexa un documento real, llama al endpoint sin formatos
    extra y valida que learning_metadata sea real y no el fallback de error.
    """
    doc_id = doc_id_manager

    texto = (
        "La API expone endpoints para indexar documentos y generar material de estudio. "
        "El pipeline recupera fragmentos relevantes desde una base de datos vectorial y "
        "los usa como contexto para producir resúmenes, cuestionarios y tarjetas de memorización."
    )

    r_index = client.post(
        "/api/v1/index",
        data={"document_id": doc_id},
        files={"file": ("wiring.txt", texto.encode("utf-8"), "text/plain")}
    )
    assert r_index.status_code == 200, f"Falló indexación: {r_index.text}"

    payload = {
        "document_id": doc_id,
        "formats": [],
        "profile": "profesional",
        "niche": "general",
        "detail_level": "avanzado",
        "query": "Conceptos principales del documento"
    }

    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 200, f"Error HTTP en /generate: {response.text}"

    data = response.json()
    assert "learning_metadata" in data, "Falta 'learning_metadata' en respuesta raíz"

    conceptos = data["learning_metadata"]["key_concepts"]
    assert len(conceptos) > 0, f"learning_metadata vacío: {data}"
    assert conceptos != ["Error al extraer conceptos"], f"/generate devolvió el fallback de error: {data}"