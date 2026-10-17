import pytest
from fastapi.testclient import TestClient
from agentes.api import app
from agentes.errors import build_error

client = TestClient(app)

# Variable global para rastrear los formatos solicitados independientemente del state
_CURRENT_FORMATS = []

def payload(formats):
    global _CURRENT_FORMATS
    _CURRENT_FORMATS = formats
    return {
        "document_id": "doc_x",
        "formats": formats,
        "profile": "p",
        "niche": "n",
        "detail_level": "d"
    }

def meta_ok():
    return {
        "status": "success",
        "content": {
            "document_title": "doc.pdf",
            "key_concepts": ["a"],
            "prerequisites": ["b"],
            "estimated_time_minutes": 10
        }
    }

def meta_fail(code):
    return {
        "status": "failed",
        "content": None,
        "error_message": "Error simulado",
        "error": build_error(code, "Error simulado")
    }

def answer_ok(fmt):
    return {
        "format": fmt,
        "status": "success",
        "content": {"title": f"{fmt} content"},
        "sources_used": [],
        "execution_time_seconds": 1.0
    }

def answer_fail(code, fmt=""):
    return {
        "format": fmt,
        "status": "failed",
        "content": None,
        "sources_used": [],
        "error_message": "Fallo format",
        "error": build_error(code, "Fallo format"),
        "execution_time_seconds": 1.0
    }

def parchear(monkeypatch, meta_res, formats_res_dict):
    """Ayudante que simula la ejecución completa de LangGraph interceptando su entrada."""
    def mock_ejecutar(grafo, state):
        format_results = []
        # Usamos _CURRENT_FORMATS en lugar de inferir del state
        for fmt in _CURRENT_FORMATS:
            if fmt in formats_res_dict:
                res = formats_res_dict[fmt]
                if isinstance(res, Exception):
                    format_results.append({
                        "format": fmt,
                        "status": "failed",
                        "content": None,
                        "sources_used": [],
                        "error_message": str(res),
                        "error": build_error("INTERNAL_ERROR", str(res)),
                        "execution_time_seconds": 1.0
                    })
                else:
                    res["format"] = fmt
                    format_results.append(res)
            else:
                # Simula que el grafo rechaza formatos no soportados
                format_results.append({
                    "format": fmt,
                    "status": "failed",
                    "content": None,
                    "error_message": "Formato no soportado",
                    "error": build_error("UNSUPPORTED_FORMAT", "Formato no soportado")
                })
        return {
            "metadata_result": meta_res,
            "format_results": format_results
        }
    monkeypatch.setattr("agentes.api.ejecutar_grafo", mock_ejecutar)

def test_todo_ok_devuelve_200(monkeypatch):
    parchear(monkeypatch, meta_ok(), {"quiz": answer_ok("quiz"), "tldr": answer_ok("tldr")})
    r = client.post("/api/v1/generate", json=payload(["quiz", "tldr"]))
    assert r.status_code == 200, r.text

def test_campos_nuevos_en_la_raiz(monkeypatch):
    def mock_meta_ok_campos_nuevos():
        return {
            "status": "success",
            "content": {
                "document_title": "documento.pdf",
                "key_concepts": ["a"],
                "prerequisites": ["x"],
                "estimated_time_minutes": 5
            },
            "document_title": "documento.pdf",
            "document_description": "desc"
        }
    parchear(monkeypatch, mock_meta_ok_campos_nuevos(), {"quiz": answer_ok("quiz")})
    data = client.post("/api/v1/generate", json=payload(["quiz"])).json()
    assert data["document_title"] == "documento.pdf"

def test_fallo_parcial_no_destruye_los_otros_formatos(monkeypatch):
    parchear(monkeypatch, meta_ok(), {
        "quiz": answer_ok("quiz"),
        "flashcards": answer_ok("flashcards"),
        "tldr": answer_fail("RESOURCE_EXHAUSTED"),
        "video_script": answer_ok("video_script"),
    })
    r = client.post("/api/v1/generate", json=payload(["quiz", "flashcards", "tldr", "video_script"]))
    assert r.status_code == 207, r.text

def test_todos_fallan_por_cuota_devuelve_429_con_detalle(monkeypatch):
    parchear(monkeypatch, meta_fail("RESOURCE_EXHAUSTED"), {
        "quiz": answer_fail("RESOURCE_EXHAUSTED"),
        "tldr": answer_fail("RESOURCE_EXHAUSTED"),
    })
    r = client.post("/api/v1/generate", json=payload(["quiz", "tldr"]))
    assert r.status_code == 429, r.text

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
        "error": build_error("NO_CONTEXT", "sin contenido")
    }
    no_res = {"status": "no_results", "content": None, "sources_used": [],
              "error_message": "sin contexto", "error": build_error("NO_CONTEXT", "sin contexto")}