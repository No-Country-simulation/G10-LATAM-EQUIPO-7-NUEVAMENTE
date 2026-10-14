import os
from pathlib import Path

from dotenv import load_dotenv


def _cargar_env_real():
    """Busca el .env desde esta carpeta hacia arriba y lo carga con prioridad."""
    base = Path(__file__).resolve().parent
    for carpeta in [base, *base.parents]:
        candidato = carpeta / ".env"
        if candidato.exists():
            load_dotenv(dotenv_path=candidato, override=True)
            return


_cargar_env_real()

# Solo aplican si el .env no definió nada: evitan errores de colección en módulos
# que leen os.environ a nivel raíz. Nunca pisan una key real.
os.environ.setdefault("GEMINI_API_KEY", "fake-test-key-for-pytest")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.5-flash-lite")