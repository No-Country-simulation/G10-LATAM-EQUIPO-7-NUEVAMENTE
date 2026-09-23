"""Configuración común para la rama Data/IA.

Este módulo centraliza rutas y constantes. No contiene lógica de negocio.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
EVALUATION_DIR = DATA_DIR / "evaluation"

CHUNKS_PATH = EVALUATION_DIR / "chunks_v1.csv"
GROUND_TRUTH_PATH = EVALUATION_DIR / "ground_truth_v1.csv"
MANIFEST_PATH = EVALUATION_DIR / "evaluation_manifest_v1.json"
