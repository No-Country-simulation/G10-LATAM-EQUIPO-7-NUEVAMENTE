"""
Tests de los endpoints de evaluación de retrieval (contrato v2.0), health, delete e index.

NO llaman a Gemini ni escriben en tu ChromaDB: se reemplazan vector_store.search y
vector_store.collection por versiones controladas. El flujo SÍ pasa por tu
RetrieverService y por rag/contract.py reales, así que el payload es el de producción.
"""
import pytest
from fastapi.testclient import TestClient

import agentes.api as api
import agentes.errors as errors
from agentes.api import app, vector_store
from agentes.rag.models import Chunk, Document, SearchResult

client = TestClient(app)

URL = "/api/v1/evaluate/retrieval"
URL_LOTE = "/api/v1/evaluate/retrieval/batch"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def resultado(chunk_id, score=1.5, doc="doc_1", con_document_id=True):
    metadata = {"source": "archivo.pdf"}
    if con_document_id:
        metadata["document_id"] = doc
    return SearchResult(chunk_id=chunk_id, text=f"texto {chunk_id}", score=score, metadata=metadata)


def caso(case_id="c1", query="pregunta", **extra):
    return {"case_id": case_id, "query": query, "top_k": 3, **extra}


def parchear_search(monkeypatch, comportamiento):
    """comportamiento(query) -> lista de SearchResult | lanza una excepción."""
    def fake_search(query, top_k=5, filters=None):
        return comportamiento(query)
    monkeypatch.setattr(vector_store, "search", fake_search)


def boom(_query):
    raise RuntimeError("chroma caído")


CLAVES_V2 = {"contract_version", "case_id", "query", "top_k", "score_type", "status", "results", "error"}


# ----------------------------------------------------------------------
# Un caso: payload del contrato v2.0 sin modificar
# ----------------------------------------------------------------------
def test_success_devuelve_200_y_el_contrato_v2(monkeypatch):
    parchear_search(monkeypatch, lambda q: [resultado("a", 3.2), resultado("b", -1.0)])
    r = client.post(URL, json=caso(metadata_filters={"document_id": "doc_1"}))
    assert r.status_code == 200, r.text
    data = r.json()
    assert set(data) == CLAVES_V2
    assert data["contract_version"] == "2.0" and data["score_type"] == "cross_encoder"
    assert data["status"] == "success" and data["error"] is None
    assert [(x["rank"], x["chunk_id"]) for x in data["results"]] == [(1, "a"), (2, "b")]
    assert data["results"][0]["document_id"] == "doc_1"


def test_no_results_devuelve_200(monkeypatch):
    parchear_search(monkeypatch, lambda q: [])
    r = client.post(URL, json=caso())
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "no_results" and r.json()["results"] == []


def test_retrieval_failed_devuelve_500_con_el_body_del_contrato(monkeypatch):
    parchear_search(monkeypatch, boom)
    r = client.post(URL, json=caso("caso_x"))
    assert r.status_code == 500, r.text
    data = r.json()
    assert set(data) == CLAVES_V2
    assert data["case_id"] == "caso_x" and data["status"] == "error"
    assert data["error"]["code"] == "RETRIEVAL_FAILED" and "chroma caído" in data["error"]["message"]


def test_chunk_sin_document_id_no_escapa_como_excepcion(monkeypatch):
    # AHORA: build_success_response está DENTRO del try. 
    # Un chunk sin document_id lanza ValueError, se atrapa limpiamente y devuelve INVALID_INPUT (HTTP 422).
    parchear_search(monkeypatch, lambda q: [resultado("a"), resultado("b", con_document_id=False)])
    r = client.post(URL, json=caso())
    assert r.status_code == 422, r.text
    assert r.json()["status"] == "error"
    assert r.json()["error"]["code"] == "INVALID_INPUT"


def test_case_id_solo_espacios_es_invalid_input_422(monkeypatch):
    parchear_search(monkeypatch, lambda q: [resultado("a")])
    r = client.post(URL, json=caso("   "))
    assert r.status_code == 422, r.text
    data = r.json()
    assert set(data) == CLAVES_V2 and data["error"]["code"] == "INVALID_INPUT"


def test_validacion_de_entrada_de_fastapi(monkeypatch):
    assert client.post(URL, json={**caso(), "top_k": 0}).status_code == 422
    assert client.post(URL, json={**caso(), "campo_raro": 1}).status_code == 422
    assert client.post(URL, json={"case_id": "c", "query": ""}).status_code == 422


def test_modo_solo_body_devuelve_200_aunque_haya_error(monkeypatch):
    monkeypatch.setattr(errors, "EVAL_ERRORS_AS_HTTP", False)
    parchear_search(monkeypatch, boom)
    r = client.post(URL, json=caso())
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "error"


# ----------------------------------------------------------------------
# Lote: cada caso es atómico
# ----------------------------------------------------------------------
def comportamiento_por_query(query):
    if query == "falla":
        raise RuntimeError("fallo del retriever")
    if query == "vacio":
        return []
    return [resultado("a"), resultado("b")]


def test_lote_mixto_devuelve_207_y_no_pierde_casos(monkeypatch):
    parchear_search(monkeypatch, comportamiento_por_query)
    cuerpo = {"cases": [caso("c1", "ok"), caso("c2", "falla"), caso("c3", "vacio"), caso("c4", "ok")]}
    r = client.post(URL_LOTE, json=cuerpo)
    assert r.status_code == 207, r.text
    data = r.json()
    assert data["overall_status"] == "partial"
    assert (data["total"], data["succeeded"], data["failed"]) == (4, 3, 1)
    assert [p["case_id"] for p in data["results"]] == ["c1", "c2", "c3", "c4"]
    assert [p["status"] for p in data["results"]] == ["success", "error", "no_results", "success"]
    assert all(set(p) == CLAVES_V2 for p in data["results"])


def test_lote_sin_errores_es_200(monkeypatch):
    parchear_search(monkeypatch, comportamiento_por_query)
    r = client.post(URL_LOTE, json={"cases": [caso("c1", "ok"), caso("c2", "vacio")]})
    assert r.status_code == 200, r.text
    assert r.json()["overall_status"] == "success"


def test_lote_todo_falla_por_retrieval_devuelve_500(monkeypatch):
    parchear_search(monkeypatch, boom)
    r = client.post(URL_LOTE, json={"cases": [caso("c1"), caso("c2")]})
    assert r.status_code == 500, r.text
    assert r.json()["overall_status"] == "failed" and r.json()["failed"] == 2


def test_lote_todo_invalid_input_devuelve_422(monkeypatch):
    parchear_search(monkeypatch, comportamiento_por_query)
    r = client.post(URL_LOTE, json={"cases": [caso("  "), caso("   ")]})
    assert r.status_code == 422, r.text
    assert all(p["error"]["code"] == "INVALID_INPUT" for p in r.json()["results"])


def test_lote_invalid_input_mas_retrieval_failed_prioriza_500(monkeypatch):
    parchear_search(monkeypatch, boom)
    r = client.post(URL_LOTE, json={"cases": [caso("  "), caso("c2")]})
    assert r.status_code == 500, r.text


def test_lote_modo_solo_body_devuelve_200(monkeypatch):
    monkeypatch.setattr(errors, "EVAL_ERRORS_AS_HTTP", False)
    parchear_search(monkeypatch, boom)
    r = client.post(URL_LOTE, json={"cases": [caso("c1")]})
    assert r.status_code == 200, r.text
    assert r.json()["overall_status"] == "failed"


def test_lote_vacio_o_demasiado_grande_se_rechaza():
    assert client.post(URL_LOTE, json={"cases": []}).status_code == 422
    assert client.post(URL_LOTE, json={"cases": [caso(f"c{i}") for i in range(101)]}).status_code == 422


# ----------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------
class FakeCollection:
    def __init__(self, ids=None, error=None):
        self.ids = list(ids or [])
        self.error = error
        self.borrados = None

    def count(self):
        if self.error:
            raise self.error
        return len(self.ids)

    def get(self, where=None, include=None):
        if self.error:
            raise self.error
        return {"ids": list(self.ids)}

    def delete(self, ids=None, where=None):
        self.borrados = ids


def test_health_ok(monkeypatch):
    monkeypatch.setattr(vector_store, "collection", FakeCollection(["a"]))
    monkeypatch.setattr(api, "API_KEY", "AQ.clave-de-prueba")
    data = client.get("/api/v1/health").json()
    assert data["status"] == "ok" and data["vector_store_ok"] and data["gemini_key_configured"]
    assert "AQ." not in str(data)  # nunca expone la key


def test_health_degradado_si_falla_el_vector_store(monkeypatch):
    monkeypatch.setattr(vector_store, "collection", FakeCollection(error=RuntimeError("sin acceso")))
    monkeypatch.setattr(api, "API_KEY", "AQ.clave-de-prueba")
    data = client.get("/api/v1/health").json()
    assert data["status"] == "degraded" and data["vector_store_ok"] is False


def test_health_degradado_con_key_falsa(monkeypatch):
    monkeypatch.setattr(vector_store, "collection", FakeCollection(["a"]))
    monkeypatch.setattr(api, "API_KEY", "fake-test-key-for-pytest")
    data = client.get("/api/v1/health").json()
    assert data["status"] == "degraded" and data["gemini_key_configured"] is False


# ----------------------------------------------------------------------
# Delete
# ----------------------------------------------------------------------
def test_delete_borra_los_chunks_del_documento(monkeypatch):
    col = FakeCollection(["d_1_0", "d_1_1", "d_1_2"])
    monkeypatch.setattr(vector_store, "collection", col)
    r = client.delete("/api/v1/documents/d")
    assert r.status_code == 200, r.text
    assert r.json() == {"document_id": "d", "status": "deleted", "chunks_deleted": 3}
    assert col.borrados == ["d_1_0", "d_1_1", "d_1_2"]


def test_delete_documento_inexistente_devuelve_404(monkeypatch):
    col = FakeCollection([])
    monkeypatch.setattr(vector_store, "collection", col)
    r = client.delete("/api/v1/documents/no_existe")
    assert r.status_code == 404, r.text
    assert r.json()["status"] == "not_found" and col.borrados is None


def test_delete_error_interno_devuelve_500(monkeypatch):
    monkeypatch.setattr(vector_store, "collection", FakeCollection(error=RuntimeError("boom")))
    assert client.delete("/api/v1/documents/d").status_code == 500


# ----------------------------------------------------------------------
# Index: título y cantidad de chunks
# ----------------------------------------------------------------------
def test_index_devuelve_titulo_y_chunks_indexados(monkeypatch):
    monkeypatch.setattr(api, "extract_document", lambda ruta: [Document(text="hola mundo")])
    monkeypatch.setattr(api, "create_chunks", lambda docs: [Chunk(id=f"d_1_{i}", text="t") for i in range(3)])
    monkeypatch.setattr(vector_store, "add_chunks", lambda chunks: None)
    r = client.post(
        "/api/v1/index",
        data={"document_id": "d"},
        files={"file": ("informe.pdf", b"contenido", "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"document_id": "d", "status": "indexed", "document_title": "informe.pdf", "chunks_indexed": 3}