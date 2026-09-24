# NuevaMente — Estructura mínima Data/IA

Esta estructura sigue los lineamientos acordados por el equipo:
modularización, separación de responsabilidades, contratos explícitos,
nombres descriptivos, manejo de errores, documentación e integraciones
desacopladas.

## Responsabilidad de Data/IA

Data/IA se encarga de:

- estructura y contratos de evaluación;
- validación de entradas y salidas;
- Ground Truth;
- métricas de retrieval;
- análisis de errores;
- evaluación del JSON final;
- rúbrica y criterios de calidad del reviewer.

## Fuera del alcance de Data/IA

El equipo de Agentes se encarga del pipeline productivo de:

- extracción;
- limpieza y normalización;
- chunking;
- embeddings multilingües;
- Vector Store;
- retrieval;
- orquestación/generación.

## Estructura

```text
data_ai/
├── __init__.py
├── config.py
├── schemas/
│   ├── __init__.py
│   ├── retrieval.py
│   └── evaluation.py
├── validators/
│   ├── __init__.py
│   ├── document_validator.py
│   └── result_validator.py
├── metrics/
│   ├── __init__.py
│   ├── retrieval_metrics.py
│   └── error_analysis.py
├── evaluation/
│   ├── __init__.py
│   ├── rubric.py
│   └── reviewer.py
├── preprocessing/
│   ├── __init__.py
│   └── README.md
└── tests/
    ├── __init__.py
    └── test_retrieval_metrics.py
```

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Pruebas

```bash
pytest data_ai/tests -q
```
