import os
# Asegurar variables de entorno de prueba antes de cualquier importación de agente/api
os.environ.setdefault("GEMINI_API_KEY", "fake-test-key-for-pytest")
os.environ.setdefault("GEMINI_MODEL", "gemini-test-model")

import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from fastapi.testclient import TestClient

from agentes.api import (
    app,
    TLDRContent,
    VideoScene,
    VideoScriptContent,
    QuizContent,
    FlashcardsContent,
    LearningMetadata,
)
from agentes.agent_v1 import AgentV1
from agentes.rag.models import SearchResult


# Mock común para learning_metadata en la raíz
MOCK_LEARNING_METADATA = {
    "status": "success",
    "content": {
        "key_concepts": ["Concepto 1", "Concepto 2", "Concepto 3"],
        "prerequisites": ["Conocimiento previo"],
        "estimated_time_minutes": 10
    }
}


# ==========================================
# 1. Tests de Contratos Pydantic
# ==========================================

def test_tldr_content_accepts_valid_payload():
    """1. TLDRContent acepta payload completo."""
    payload = {
        "title": "Resumen Ejecutivo: Arquitectura de Kubernetes",
        "summary": "Kubernetes automatiza el despliegue, escalado y gestión de contenedores.",
        "key_points": [
            "Los Pods son las unidades básicas de ejecución.",
            "Deployments gestionan la disponibilidad y réplicas.",
            "Services proporcionan abstracción de red y balanceo.",
        ],
        "conclusion": "Kubernetes estandariza la infraestructura moderna en la nube.",
    }
    tldr = TLDRContent(**payload)
    assert tldr.title == payload["title"]
    assert tldr.summary == payload["summary"]
    assert len(tldr.key_points) == 3
    assert tldr.conclusion == payload["conclusion"]


def test_tldr_content_rejects_incomplete_payload():
    """2. TLDRContent rechaza payload incompleto."""
    incomplete = {
        "title": "Título sin otros campos obligatorios"
    }
    with pytest.raises(ValidationError):
        TLDRContent(**incomplete)


def test_video_scene_accepts_valid_payload():
    """3. VideoScene acepta payload completo."""
    payload = {
        "scene_id": "SCENE-01",
        "title": "Introducción a Pods",
        "narration": "Hoy aprenderemos la unidad fundamental de cómputo en Kubernetes.",
        "visual_description": "Animación mostrando un contenedor dentro de una cápsula (Pod).",
        "duration_seconds": 45,
    }
    scene = VideoScene(**payload)
    assert scene.scene_id == "SCENE-01"
    assert scene.title == payload["title"]
    assert scene.narration == payload["narration"]
    assert scene.visual_description == payload["visual_description"]
    assert scene.duration_seconds == 45


def test_video_script_content_accepts_valid_payload():
    """4. VideoScriptContent acepta payload completo."""
    payload = {
        "title": "Clase Express: Introducción a Kubernetes",
        "estimated_duration_minutes": 3,
        "scenes": [
            {
                "scene_id": "SCENE-01",
                "title": "Bienvenida y Contexto",
                "narration": "Bienvenidos a este micro-curso sobre orquestación.",
                "visual_description": "Profesor en pantalla con fondo de centro de datos.",
                "duration_seconds": 60,
            },
            {
                "scene_id": "SCENE-02",
                "title": "El Rol de los Pods",
                "narration": "Un Pod encapsula uno o más contenedores estrechamente ligados.",
                "visual_description": "Diagrama de arquitectura con cajas de contenedores.",
                "duration_seconds": 120,
            },
        ],
    }
    script = VideoScriptContent(**payload)
    assert script.title == payload["title"]
    assert script.estimated_duration_minutes == 3
    assert len(script.scenes) == 2
    assert script.scenes[0].scene_id == "SCENE-01"
    assert script.scenes[1].duration_seconds == 120


def test_video_script_content_rejects_incomplete_payload():
    """5. VideoScriptContent rechaza payload incompleto."""
    incomplete = {
        "title": "Solo título",
        "estimated_duration_minutes": 5,
        # Falta 'scenes'
    }
    with pytest.raises(ValidationError):
        VideoScriptContent(**incomplete)


# ==========================================
# 2. Tests de API Endpoint /api/v1/generate
# ==========================================

@pytest.fixture
def test_client():
    return TestClient(app)


def test_generate_accepts_tldr(test_client):
    """6. /api/v1/generate acepta 'tldr' y preserva contrato raíz con learning_metadata."""
    mock_result = {
        "status": "success",
        "content": {
            "title": "Resumen TLDR",
            "summary": "Resumen conciso.",
            "key_points": ["Punto 1", "Punto 2", "Punto 3"],
            "conclusion": "Conclusión final."
        },
        "sources_used": [{"rank": 1, "chunk_id": "c1", "text": "texto"}],
        "error_message": None,
    }
    with patch("agentes.api.agent.extract_learning_metadata", return_value=MOCK_LEARNING_METADATA), \
         patch("agentes.api.agent.answer", return_value=mock_result) as mock_answer:
        response = test_client.post(
            "/api/v1/generate",
            json={
                "document_id": "doc-test-1",
                "formats": ["tldr"],
                "profile": "universitario",
                "niche": "DevOps",
                "detail_level": "intermedio",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Validación del contrato raíz de QA
        assert "document_id" in data
        assert data["document_id"] == "doc-test-1"
        assert "learning_metadata" in data
        assert data["learning_metadata"]["estimated_time_minutes"] == 10
        assert "results" in data

        assert len(data["results"]) == 1
        res = data["results"][0]
        assert res["format"] == "tldr"
        assert res["status"] == "success"
        assert res["content"] is not None
        assert res["error_message"] is None
        mock_answer.assert_called_once()
        assert mock_answer.call_args.kwargs["formato"] == "tldr"


def test_generate_accepts_video_script(test_client):
    """7. /api/v1/generate acepta 'video_script' y preserva contrato raíz."""
    mock_result = {
        "status": "success",
        "content": {
            "title": "Guion Educativo",
            "estimated_duration_minutes": 2,
            "scenes": [
                {
                    "scene_id": "SC-1",
                    "title": "Escena 1",
                    "narration": "Texto",
                    "visual_description": "Visual",
                    "duration_seconds": 120,
                }
            ],
        },
        "sources_used": [{"rank": 1, "chunk_id": "c1", "text": "texto"}],
        "error_message": None,
    }
    with patch("agentes.api.agent.extract_learning_metadata", return_value=MOCK_LEARNING_METADATA), \
         patch("agentes.api.agent.answer", return_value=mock_result) as mock_answer:
        response = test_client.post(
            "/api/v1/generate",
            json={
                "document_id": "doc-test-2",
                "formats": ["video_script"],
                "profile": "profesional",
                "niche": "Cloud",
                "detail_level": "avanzado",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Validación del contrato raíz de QA
        assert "document_id" in data
        assert "learning_metadata" in data
        assert "results" in data

        assert len(data["results"]) == 1
        res = data["results"][0]
        assert res["format"] == "video_script"
        assert res["status"] == "success"
        assert res["content"] is not None
        mock_answer.assert_called_once()
        assert mock_answer.call_args.kwargs["formato"] == "video_script"


def test_generate_still_accepts_quiz(test_client):
    """8. /api/v1/generate sigue aceptando 'quiz'."""
    mock_result = {
        "status": "success",
        "content": {
            "title": "Quiz",
            "instructions": "Responde las preguntas",
            "questions": [],
        },
        "sources_used": [],
        "error_message": None,
    }
    with patch("agentes.api.agent.extract_learning_metadata", return_value=MOCK_LEARNING_METADATA), \
         patch("agentes.api.agent.answer", return_value=mock_result) as mock_answer:
        response = test_client.post(
            "/api/v1/generate",
            json={
                "document_id": "doc-test-3",
                "formats": ["quiz"],
                "profile": "estudiante",
                "niche": "TI",
                "detail_level": "básico",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "learning_metadata" in data
        res = data["results"][0]
        assert res["format"] == "quiz"
        assert res["status"] == "success"
        mock_answer.assert_called_once()


def test_generate_still_accepts_flashcards(test_client):
    """9. /api/v1/generate sigue aceptando 'flashcards'."""
    mock_result = {
        "status": "success",
        "content": {
            "title": "Flashcards",
            "instructions": "Repasa las tarjetas",
            "cards": [],
        },
        "sources_used": [],
        "error_message": None,
    }
    with patch("agentes.api.agent.extract_learning_metadata", return_value=MOCK_LEARNING_METADATA), \
         patch("agentes.api.agent.answer", return_value=mock_result) as mock_answer:
        response = test_client.post(
            "/api/v1/generate",
            json={
                "document_id": "doc-test-4",
                "formats": ["flashcards"],
                "profile": "estudiante",
                "niche": "TI",
                "detail_level": "básico",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "learning_metadata" in data
        res = data["results"][0]
        assert res["format"] == "flashcards"
        assert res["status"] == "success"
        mock_answer.assert_called_once()


def test_generate_unknown_format_returns_failed(test_client):
    """10. formato desconocido devuelve status == 'failed'."""
    with patch("agentes.api.agent.extract_learning_metadata", return_value=MOCK_LEARNING_METADATA), \
         patch("agentes.api.agent.answer") as mock_answer:
        response = test_client.post(
            "/api/v1/generate",
            json={
                "document_id": "doc-test-5",
                "formats": ["formato_inexistente"],
                "profile": "estudiante",
                "niche": "TI",
                "detail_level": "básico",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "learning_metadata" in data
        assert len(data["results"]) == 1
        res = data["results"][0]
        assert res["format"] == "formato_inexistente"
        assert res["status"] == "failed"
        assert res["content"] is None
        assert res["sources_used"] == []
        assert res["error_message"] is not None
        assert "no está soportado" in res["error_message"]
        # El agente no debe ser invocado para formatos no soportados
        mock_answer.assert_not_called()


# ==========================================
# 3. Tests de AgentV1 (Mocks de LLM y Retriever)
# ==========================================

@pytest.fixture
def mock_retriever_results():
    return [
        SearchResult(
            chunk_id="chk-01",
            text="Kubernetes orquesta contenedores en nodos de cómputo.",
            score=0.95,
            metadata={"document_id": "doc-k8s"},
        )
    ]


def test_agent_v1_uses_tldr_content_schema(mock_retriever_results):
    """11. AgentV1 usa TLDRContent cuando formato == 'tldr'."""
    mock_store = MagicMock()
    agent = AgentV1(vector_store=mock_store)

    expected_content = TLDRContent(
        title="Resumen Ejecutivo",
        summary="Kubernetes orquesta contenedores.",
        key_points=["Pods", "Deployments", "Services"],
        conclusion="Esencial para DevOps."
    )

    mock_llm_response = MagicMock()
    mock_llm_response.parsed = expected_content

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_llm_response

    with patch.object(agent.retriever, "retrieve", return_value=mock_retriever_results):
        with patch("agentes.agent_v1.client", mock_client), patch("agentes.agent_v1.MODEL_NAME", "gemini-test"):
            result = agent.answer(
                query="Conceptos clave",
                document_id="doc-k8s",
                formato="tldr",
                perfil="universitario",
                nicho="Kubernetes",
                nivel="intermedio",
            )

            assert result["status"] == "success"
            assert result["content"]["title"] == "Resumen Ejecutivo"
            assert result["content"]["key_points"] == ["Pods", "Deployments", "Services"]
            assert len(result["sources_used"]) == 1
            assert result["error_message"] is None

            # Verificar que el schema pasado al SDK fue TLDRContent
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            config = call_kwargs["config"]
            assert config.response_schema == TLDRContent
            assert config.response_mime_type == "application/json"


def test_agent_v1_uses_video_script_content_schema(mock_retriever_results):
    """12. AgentV1 usa VideoScriptContent cuando formato == 'video_script'."""
    mock_store = MagicMock()
    agent = AgentV1(vector_store=mock_store)

    expected_content = VideoScriptContent(
        title="Guion de Video K8s",
        estimated_duration_minutes=2,
        scenes=[
            VideoScene(
                scene_id="SC-01",
                title="Intro",
                narration="Bienvenidos.",
                visual_description="Logo animado.",
                duration_seconds=120,
            )
        ],
    )

    mock_llm_response = MagicMock()
    mock_llm_response.parsed = expected_content

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_llm_response

    with patch.object(agent.retriever, "retrieve", return_value=mock_retriever_results):
        with patch("agentes.agent_v1.client", mock_client), patch("agentes.agent_v1.MODEL_NAME", "gemini-test"):
            result = agent.answer(
                query="Guion K8s",
                document_id="doc-k8s",
                formato="video_script",
                perfil="universitario",
                nicho="Kubernetes",
                nivel="intermedio",
            )

            assert result["status"] == "success"
            assert result["content"]["title"] == "Guion de Video K8s"
            assert result["content"]["estimated_duration_minutes"] == 2
            assert len(result["content"]["scenes"]) == 1
            assert result["error_message"] is None

            # Verificar que el schema pasado al SDK fue VideoScriptContent
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            config = call_kwargs["config"]
            assert config.response_schema == VideoScriptContent
            assert config.response_mime_type == "application/json"


def test_agent_v1_gemini_error_returns_failed(mock_retriever_results):
    """13. error de Gemini sigue devolviendo status == 'failed'."""
    mock_store = MagicMock()
    agent = AgentV1(vector_store=mock_store)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Quota exceeded 429")

    with patch.object(agent.retriever, "retrieve", return_value=mock_retriever_results):
        with patch("agentes.agent_v1.client", mock_client), patch("agentes.agent_v1.MODEL_NAME", "gemini-test"):
            result = agent.answer(
                query="Conceptos",
                document_id="doc-k8s",
                formato="tldr",
                perfil="universitario",
                nicho="Kubernetes",
                nivel="intermedio",
            )

            assert result["status"] == "failed"
            assert result["content"] is None
            assert len(result["sources_used"]) == 1
            assert result["error_message"] is not None
            assert "Quota exceeded 429" in result["error_message"]


def test_agent_v1_no_context_returns_no_results():
    """14. ausencia de contexto sigue devolviendo status == 'no_results'."""
    mock_store = MagicMock()
    agent = AgentV1(vector_store=mock_store)

    with patch.object(agent.retriever, "retrieve", return_value=[]):
        result = agent.answer(
            query="Conceptos",
            document_id="doc-inexistente",
            formato="tldr",
            perfil="universitario",
            nicho="Kubernetes",
            nivel="intermedio",
        )

        assert result["status"] == "no_results"
        assert result["content"] is None
        assert result["sources_used"] == []
        assert result["error_message"] == "No se encontró contexto suficiente en el documento."
