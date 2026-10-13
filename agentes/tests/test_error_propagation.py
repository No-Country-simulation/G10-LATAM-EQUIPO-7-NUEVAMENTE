"""
Tests de propagación de errores estructurada por formato y política HTTP.

NO llaman a Gemini: se reemplazan agent.extract_learning_metadata y agent.answer
por versiones controladas, así que corren en segundos y sin consumir cuota.
"""
import pytest
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

from agentes.api import app, agent
from agentes.errors import build_error, classify_exception

client = TestClient(app)

FALLBACK_META = {
    "key_concepts": ["Error al extraer conceptos"],
    "prerequisites": ["No se pudieron determinar"],
    "estimated_time_minutes": 0,
}


def meta_ok():
    return {
        "status": "success",
        "content": {"key_concepts": ["a", "b", "c"], "prerequisites": ["x"], "estimated_time_minutes": 5},
        "error_message": None,
        "error": None,
        "document_title": "documento.pdf",
        "document_description": "Describe el pipeline RAG del proyecto.",
    }


def meta_fail(causa="RESOURCE_EXHAUSTED"):
    return {
        "status": "failed",
        "content": FALLBACK_META,
        "error_message": f"fallo {causa}",
        "error": build_error(causa, f"fallo {causa}"),
        "document_title": "documento.pdf",
        "document_description": None,
    }


def answer_ok(formato):
    return {
        "status": "success",
        "content": {"title": f"contenido {formato}"},
        "sources_used": [{"rank": 1, "chunk_id": "c1", "document_id": "d", "score": 0.9, "text": "t"}],
        "error_message": None,
        "error": None,
    }


def answer_fail(causa):
    return {
        "status": "failed",
        "content": None,
        "sources_used": [],
        "error_message": f"fallo {causa}",
        "error": build_error(causa, f"fallo {causa}"),
    }


def payload(formats):
    return {
        "document_id": "doc_x",
        "formats": formats,
        "profile": "profesional",
        "niche": "general",
        "detail_level": "avanzado",
        "query": "conceptos principales",
    }


def parchear(monkeypatch, meta, por_formato):
    """por_formato: dict formato -> resultado (dict) o Exception a lanzar."""
    monkeypatch.setattr(agent, "extract_learning_metadata", lambda **kw: meta)

    def fake_answer(**kw):
        r = por_formato[kw["formato"]]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(agent, "answer", fake_answer)


def por_id(data):
    return {r["format"]: r for r in data["results"]}


# ----------------------------------------------------------------------
# Política HTTP
# ----------------------------------------------------------------------
def test_todo_ok_devuelve_200(monkeypatch):
    parchear(monkeypatch, meta_ok(), {"quiz": answer_ok("quiz"), "tldr": answer_ok("tldr")})
    r = client.post("/api/v1/generate", json=payload(["quiz", "tldr"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["overall_status"] == "success"
    assert all(x["status"] == "success" and x["error"] is None for x in data["results"])


def test_campos_nuevos_en_la_raiz(monkeypatch):
    parchear(monkeypatch, meta_ok(), {"quiz": answer_ok("quiz")})
    data = client.post("/api/v1/generate", json=payload(["quiz"])).json()
    assert data["document_title"] == "documento.pdf"
    assert data["document_description"] == "Describe el pipeline RAG del proyecto."
    assert isinstance(data["execution_time_seconds"], float) and data["execution_time_seconds"] >= 0
    assert all("execution_time_seconds" in x for x in data["results"])


def test_fallo_parcial_no_destruye_los_otros_formatos(monkeypatch):
    parchear(monkeypatch, meta_ok(), {
        "quiz": answer_ok("quiz"),
        "flashcards": answer_ok("flashcards"),
        "tldr": answer_fail("RESOURCE_EXHAUSTED"),
        "video_script": answer_ok("video_script"),
    })
    r = client.post("/api/v1/generate", json=payload(["quiz", "flashcards", "tldr", "video_script"]))
    assert r.status_code == 207, r.text
    data = r.json()
    assert data["overall_status"] == "partial"
    res = por_id(data)
    for f in ("quiz", "flashcards", "video_script"):
        assert res[f]["status"] == "success" and res[f]["content"] is not None, f
    assert res["tldr"]["status"] == "failed"
    assert res["tldr"]["error"]["code"] == "RESOURCE_EXHAUSTED"
    assert res["tldr"]["error"]["retryable"] is True
    assert res["tldr"]["error"]["http_status"] == 429


def test_todos_fallan_por_cuota_devuelve_429_con_detalle(monkeypatch):
    parchear(monkeypatch, meta_fail("RESOURCE_EXHAUSTED"), {
        "quiz": answer_fail("RESOURCE_EXHAUSTED"),
        "tldr": answer_fail("RESOURCE_EXHAUSTED"),
    })
    r = client.post("/api/v1/generate", json=payload(["quiz", "tldr"]))
    assert r.status_code == 429, r.text
    data = r.json()
    assert data["overall_status"] == "failed"
    assert len(data["results"]) == 2
    assert all(x["error"]["code"] == "RESOURCE_EXHAUSTED" for x in data["results"])


def test_todos_fallan_por_proveedor_saturado_devuelve_503(monkeypatch):
    parchear(monkeypatch, meta_fail("PROVIDER_UNAVAILABLE"), {"quiz": answer_fail("PROVIDER_UNAVAILABLE")})
    r = client.post("/api/v1/generate", json=payload(["quiz"]))
    assert r.status_code == 503, r.text


def test_prioridad_de_causas_cuota_gana_a_saturacion(monkeypatch):
    parchear(monkeypatch, meta_fail("PROVIDER_UNAVAILABLE"), {
        "quiz": answer_fail("PROVIDER_UNAVAILABLE"),
        "tldr": answer_fail("RESOURCE_EXHAUSTED"),
    })
    r = client.post("/api/v1/generate", json=payload(["quiz", "tldr"]))
    assert r.status_code == 429, r.text


def test_documento_sin_contenido_devuelve_404(monkeypatch):
    meta = {
        "status": "no_results", "content": None, "error_message": "Sin resultados",
        "error": build_error("NO_CONTEXT", "sin contenido"), "document_title": None, "document_description": None,
    }
    no_res = {"status": "no_results", "content": None, "sources_used": [],
              "error_message": "sin contexto", "error": build_error("NO_CONTEXT", "sin contexto")}
    parchear(monkeypatch, meta, {"quiz": no_res})
    r = client.post("/api/v1/generate", json=payload(["quiz"]))
    assert r.status_code == 404, r.text
    assert r.json()["learning_metadata"] == FALLBACK_META


def test_formato_no_soportado_es_fallo_controlado(monkeypatch):
    parchear(monkeypatch, meta_ok(), {"quiz": answer_ok("quiz")})
    r = client.post("/api/v1/generate", json=payload(["quiz", "pdf"]))
    assert r.status_code == 207, r.text
    res = por_id(r.json())
    assert res["quiz"]["status"] == "success"
    assert res["pdf"]["status"] == "failed"
    assert res["pdf"]["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_excepcion_inesperada_en_un_formato_no_tumba_los_demas(monkeypatch):
    parchear(monkeypatch, meta_ok(), {
        "quiz": answer_ok("quiz"),
        "flashcards": RuntimeError("boom inesperado"),
        "tldr": answer_ok("tldr"),
    })
    r = client.post("/api/v1/generate", json=payload(["quiz", "flashcards", "tldr"]))
    assert r.status_code == 207, r.text
    res = por_id(r.json())
    assert res["quiz"]["status"] == "success"
    assert res["tldr"]["status"] == "success"
    assert res["flashcards"]["status"] == "failed"
    assert res["flashcards"]["error"]["code"] == "INTERNAL_ERROR"


def test_metadatos_fallan_pero_formatos_ok_es_parcial(monkeypatch):
    parchear(monkeypatch, meta_fail("PROVIDER_UNAVAILABLE"), {"quiz": answer_ok("quiz")})
    r = client.post("/api/v1/generate", json=payload(["quiz"]))
    assert r.status_code == 207, r.text
    data = r.json()
    assert data["learning_metadata_status"] == "failed"
    assert data["learning_metadata_error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert data["learning_metadata"] == FALLBACK_META
    assert data["document_title"] == "documento.pdf"
    assert data["document_description"] is None


def test_sin_formatos_y_metadatos_fallan_es_error_global(monkeypatch):
    parchear(monkeypatch, meta_fail("PROVIDER_UNAVAILABLE"), {})
    r = client.post("/api/v1/generate", json=payload([]))
    assert r.status_code == 503, r.text


def test_sin_formatos_y_metadatos_ok_es_200(monkeypatch):
    parchear(monkeypatch, meta_ok(), {})
    r = client.post("/api/v1/generate", json=payload([]))
    assert r.status_code == 200, r.text
    assert r.json()["results"] == []


# ----------------------------------------------------------------------
# Clasificación de excepciones del SDK de Gemini
# ----------------------------------------------------------------------
def _api_error(clase, codigo, estado, mensaje):
    return clase(codigo, {"error": {"code": codigo, "message": mensaje, "status": estado}})


@pytest.mark.parametrize("clase,codigo,estado,mensaje,esperado,retryable", [
    (genai_errors.ClientError, 429, "RESOURCE_EXHAUSTED", "Quota exceeded", "RESOURCE_EXHAUSTED", True),
    (genai_errors.ServerError, 503, "UNAVAILABLE", "high demand", "PROVIDER_UNAVAILABLE", True),
    (genai_errors.ServerError, 504, "DEADLINE_EXCEEDED", "timeout", "PROVIDER_TIMEOUT", True),
    (genai_errors.ServerError, 500, "INTERNAL", "internal", "PROVIDER_ERROR", True),
    (genai_errors.ClientError, 404, "NOT_FOUND", "model no longer available", "MODEL_NOT_FOUND", False),
    (genai_errors.ClientError, 400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key.", "PROVIDER_AUTH_ERROR", False),
    (genai_errors.ClientError, 403, "PERMISSION_DENIED", "denied", "PROVIDER_AUTH_ERROR", False),
    (genai_errors.ClientError, 400, "INVALID_ARGUMENT", "bad schema", "PROVIDER_REJECTED_REQUEST", False),
])
def test_clasifica_errores_de_gemini(clase, codigo, estado, mensaje, esperado, retryable):
    info = classify_exception(_api_error(clase, codigo, estado, mensaje))
    assert info["code"] == esperado
    assert info["retryable"] is retryable
    assert info["upstream_status"] == codigo
    assert info["provider"] == "gemini"


def test_excepcion_desconocida_es_error_interno():
    info = classify_exception(ValueError("algo raro"))
    assert info["code"] == "INTERNAL_ERROR"
    assert info["provider"] == "internal"
    assert info["http_status"] == 500
