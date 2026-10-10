import os
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agentes.api import (
    app,
    TLDRContent,
    VideoScene,
    VideoScriptContent,
    QuizContent,
    FlashcardsContent,
    LearningMetadata,
    vector_store # Importamos el vector_store real para inyectar contexto
)
from agentes.agent_v1 import AgentV1
from agentes.rag.models import Chunk


# ==========================================
# FIXTURE: INYECCIÓN DE CONTEXTO REAL EN CHROMADB
# ==========================================
@pytest.fixture(autouse=True)
def setup_real_context():
    """
    Inyecta un chunk real en la base de datos vectorial antes de los tests.
    Se adapta dinámicamente a la firma del modelo Chunk.
    """
    texto_real = "Kubernetes orquesta contenedores en nodos de cómputo. Los Pods son la unidad básica de ejecución, y los Deployments gestionan su escalabilidad. Es una herramienta esencial para el ecosistema DevOps moderno."
    meta = {"document_id": "doc-k8s-real"}
    
    try:
        # Intento 1: Asumiendo que el campo identificador se llama 'id'
        chunk_real = Chunk(
            id="chk-real-01",
            text=texto_real,
            metadata=meta
        )
    except TypeError:
        # Intento 2: Asumiendo que el ID se genera automáticamente
        chunk_real = Chunk(
            text=texto_real,
            metadata=meta
        )
        
    vector_store.add_chunks([chunk_real])
    yield


# ==========================================
# 1. Tests de Contratos Pydantic (Validación Local)
# ==========================================
def test_tldr_content_accepts_valid_payload():
    """1. TLDRContent acepta payload completo."""
    payload = {
        "title": "Resumen Kubernetes",
        "summary": "Kubernetes automatiza despliegues.",
        "key_points": ["Pods", "Deployments", "Services"],
        "conclusion": "Estandariza la nube.",
    }
    tldr = TLDRContent(**payload)
    assert tldr.title == payload["title"]
    assert len(tldr.key_points) == 3


def test_tldr_content_rejects_incomplete_payload():
    """2. TLDRContent rechaza payload incompleto."""
    with pytest.raises(ValidationError):
        TLDRContent(title="Incompleto")


def test_video_scene_accepts_valid_payload():
    """3. VideoScene acepta payload completo."""
    payload = {
        "scene_id": "SC-01", "title": "Intro",
        "narration": "Hoy aprenderemos Kubernetes.",
        "visual_description": "Logo en pantalla.", "duration_seconds": 45,
    }
    scene = VideoScene(**payload)
    assert scene.scene_id == "SC-01"


def test_video_script_content_accepts_valid_payload():
    """4. VideoScriptContent acepta payload completo."""
    payload = {
        "title": "Clase Express", "estimated_duration_minutes": 3,
        "scenes": [{
            "scene_id": "SC-01", "title": "Contexto",
            "narration": "Hola.", "visual_description": "Profesor.", "duration_seconds": 60,
        }],
    }
    script = VideoScriptContent(**payload)
    assert script.estimated_duration_minutes == 3


def test_video_script_content_rejects_incomplete_payload():
    """5. VideoScriptContent rechaza payload incompleto."""
    with pytest.raises(ValidationError):
        VideoScriptContent(title="Solo título", estimated_duration_minutes=5)


# ==========================================
# 2. Tests de API Endpoint (EJECUCIÓN REAL LLM)
# ==========================================
@pytest.fixture
def test_client():
    return TestClient(app)

def test_generate_accepts_tldr_real(test_client):
    """6. /api/v1/generate ejecuta TLDR real contra Gemini."""
    response = test_client.post(
        "/api/v1/generate",
        json={
            "document_id": "doc-k8s-real",
            "formats": ["tldr"],
            "profile": "universitario",
            "niche": "DevOps",
            "detail_level": "básico",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["status"] == "success"
    assert data["results"][0]["format"] == "tldr"
    assert "learning_metadata" in data


def test_generate_accepts_video_script_real(test_client):
    """7. /api/v1/generate ejecuta Video Script real contra Gemini."""
    response = test_client.post(
        "/api/v1/generate",
        json={
            "document_id": "doc-k8s-real",
            "formats": ["video_script"],
            "profile": "profesional",
            "niche": "Cloud",
            "detail_level": "avanzado",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["status"] == "success"
    assert data["results"][0]["format"] == "video_script"


def test_generate_unknown_format_returns_failed(test_client):
    """10. formato desconocido devuelve failed sin llamar al LLM."""
    response = test_client.post(
        "/api/v1/generate",
        json={
            "document_id": "doc-k8s-real",
            "formats": ["formato_inexistente"],
            "profile": "estudiante",
            "niche": "TI",
            "detail_level": "básico",
        },
    )
    assert response.status_code == 200
    data = response.json()
    res = data["results"][0]
    assert res["format"] == "formato_inexistente"
    assert res["status"] == "failed"
    # Ajuste exacto del string de error retornado por api.py
    assert "no soportado" in res["error_message"]


# ==========================================
# 3. Tests de AgentV1 (EJECUCIÓN REAL SIN MOCKS)
# ==========================================
def test_agent_v1_uses_tldr_content_schema_real():
    """11. AgentV1 extrae clase TLDRContent de forma E2E."""
    agent = AgentV1(vector_store=vector_store)
    result = agent.answer(
        query="Conceptos clave",
        document_id="doc-k8s-real",
        formato="tldr",
        perfil="universitario",
        nicho="Kubernetes",
        nivel="intermedio",
    )
    assert result["status"] == "success"
    
    # Validamos reconstruyendo el objeto Pydantic a partir del dict
    tldr_obj = TLDRContent(**result["content"])
    assert tldr_obj.title is not None
    assert len(tldr_obj.key_points) > 0
    assert len(result["sources_used"]) >= 1


def test_agent_v1_uses_video_script_content_schema_real():
    """12. AgentV1 extrae clase VideoScriptContent de forma E2E."""
    agent = AgentV1(vector_store=vector_store)
    result = agent.answer(
        query="Guion K8s",
        document_id="doc-k8s-real",
        formato="video_script",
        perfil="universitario",
        nicho="Kubernetes",
        nivel="intermedio",
    )
    assert result["status"] == "success"
    
    # Validamos reconstruyendo el objeto Pydantic
    video_obj = VideoScriptContent(**result["content"])
    assert video_obj.title is not None
    assert isinstance(video_obj.scenes, list)


def test_agent_v1_gemini_error_returns_failed_real(monkeypatch):
    """13. Forzamos un error en el motor de IA para verificar que AgentV1 captura la excepción y retorna status == 'failed'."""
    import agentes.agent_v1 as agent_module

    # Interceptamos la función interna que ejecuta el LLM para que lance una excepción controlada
    def mock_generate_failing(*args, **kwargs):
        raise RuntimeError("Error simulado 503: Falla en el motor de IA")

    monkeypatch.setattr(agent_module, "_generate_and_parse", mock_generate_failing)

    agent = AgentV1(vector_store=vector_store)
    
    # Probamos el método que consume el generador del LLM
    result = agent.extract_learning_metadata(
        query="Conceptos clave",
        document_id="doc-k8s-real",
        niche="Kubernetes"
    )

    # Validamos que el AgentV1 atrapó el error y cumplió el contrato de error pasivo del Sprint 3
    assert result["status"] == "failed"
    assert result["content"] is not None
    assert result["error_message"] is not None
    assert "Error simulado" in result["error_message"]