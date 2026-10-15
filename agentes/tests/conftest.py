import os
from pathlib import Path

from dotenv import load_dotenv


def _cargar_env_real():
    """Busca el .env desde esta carpeta hacia arriba y lo carga con prioridad[cite: 2]."""
    base = Path(__file__).resolve().parent
    for carpeta in [base, *base.parents]:
        candidato = carpeta / ".env"
        if candidato.exists():
            load_dotenv(dotenv_path=candidato, override=True)
            return


_cargar_env_real()

# Solo se establece la clave de prueba si no existe ninguna variable previa en el entorno o .env[cite: 2].
if not os.environ.get("GEMINI_API_KEY"):
    os.environ.setdefault("GEMINI_API_KEY", "fake-test-key-for-pytest")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.5-flash-lite")