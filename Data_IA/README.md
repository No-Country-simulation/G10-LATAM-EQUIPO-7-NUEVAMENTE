# NuevaMente — Data/IA

Repositorio base de la rama **Data/IA** del proyecto NuevaMente.

## Responsabilidad de Data/IA

Esta rama se enfoca en:

- preparación y versionado del corpus de evaluación;
- Ground Truth;
- contratos de entrada/salida para evaluación;
- validación de documentos y resultados;
- métricas de retrieval;
- análisis de errores;
- evaluación del JSON final;
- rúbrica y criterios de calidad del reviewer.

## Fuera del alcance de esta rama

El pipeline productivo de:

- extracción;
- limpieza/normalización;
- chunking;
- embeddings multilingües;
- Vector Store;
- retrieval;
- orquestación/generación;

corresponde al equipo de **Agentes**.

## Estructura

```text
.
├── data_ai/
│   ├── config.py
│   ├── schemas/
│   ├── validators/
│   ├── metrics/
│   ├── evaluation/
│   ├── preprocessing/
│   └── tests/
├── notebooks/
│   └── 01_data_ai_corpus_ground_truth_v1.ipynb
├── data/
│   ├── raw/
│   ├── processed/
│   └── evaluation/
│       ├── NuevaMente_Dataset_ES_10_Documentos_Evaluacion_v1.xlsx
│       ├── chunks_v1.csv
│       ├── ground_truth_v1.csv
│       ├── ground_truth_v1.xlsx
│       └── evaluation_manifest_v1.json
├── requirements.txt
├── README_DATA_AI_STRUCTURE.md
└── README.md
```

## Instalación

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Pruebas

```bash
pytest data_ai/tests -q
```

## Notebook 01

`notebooks/01_data_ai_corpus_ground_truth_v1.ipynb`

Objetivo: reproducir y documentar el corpus de evaluación y el Ground Truth v1 sin implementar el retrieval productivo.

## Artefactos congelados

Los siguientes archivos forman parte de la versión de evaluación v1 y no deben sobrescribirse durante la medición del baseline:

- `data/evaluation/chunks_v1.csv`
- `data/evaluation/ground_truth_v1.csv`
- `data/evaluation/evaluation_manifest_v1.json`

Si cambian el corpus, chunking o Ground Truth, crear una nueva versión.
