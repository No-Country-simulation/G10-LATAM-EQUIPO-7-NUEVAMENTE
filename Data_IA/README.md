# NuevaMente — Data/IA

Módulo de **Data/IA** del proyecto NuevaMente.

Esta área se encarga de definir, validar y evaluar la calidad de los resultados generados por el sistema, manteniendo contratos reproducibles, métricas de retrieval, Ground Truth y evaluación estructurada de formatos educativos.

---

## Responsabilidad de Data/IA

Data/IA se enfoca en:

- preparación y versionado del corpus de evaluación;
- definición y mantenimiento de Ground Truth;
- validación de contratos de entrada y salida;
- métricas de retrieval;
- análisis de errores;
- evaluación de formatos educativos;
- detección heurística de información no respaldada;
- evaluación de relevancia, coherencia y adaptación didáctica;
- definición de reglas de aprobación, revisión y rechazo;
- exposición del endpoint `/evaluate`.

---

## Fuera del alcance de Data/IA

El pipeline productivo de:

- extracción;
- limpieza y normalización;
- chunking;
- embeddings multilingües;
- Vector Store;
- retrieval;
- orquestación;
- generación de contenido;

corresponde principalmente al equipo de **Agentes**.

Data/IA recibe los resultados generados y la evidencia utilizada para evaluar su calidad.

---

# Sprint 2 — Evaluación de formatos

Durante Sprint 2 se implementó el flujo de evaluación para los formatos:

- `quiz`
- `flashcards`

El sistema recibe contenido generado, contexto de generación y chunks utilizados como evidencia.

El flujo actual es:

```text
EvaluationRequest
        ↓
Validación Pydantic
        ↓
reviewer.evaluar_contenido()
        ↓
quality_evaluator.evaluate()
        ↓
EvaluationScores
+ informacion_no_respaldada
        ↓
rubric.calcular_veredicto_evaluacion()
        ↓
EvaluationResponse
        ↓
HTTP 200
```

---

# API de evaluación

La API utiliza **FastAPI**.

Archivo principal:

```text
data_ai/api/app.py
```

Para ejecutarla:

```bash
python -m uvicorn data_ai.api.app:app --reload
```

Por defecto:

```text
http://127.0.0.1:8000
```

---

## GET `/health`

Permite comprobar que el servicio se encuentra disponible.

### Respuesta

```json
{
  "status": "ok"
}
```

---

## POST `/evaluate`

Evalúa un Quiz o conjunto de Flashcards generado por NuevaMente.

### Request

El request contiene:

```text
document_id
format
generation_context
generated_content
chunks_used
```

Ejemplo simplificado:

```json
{
  "document_id": "DOC-001",
  "format": "quiz",
  "generation_context": {
    "profile": "student",
    "niche": "technology",
    "detail_level": "beginner",
    "learning_objective": "Comprender conceptos básicos de FastAPI"
  },
  "generated_content": {},
  "chunks_used": []
}
```

Los contratos completos se encuentran en:

```text
data_ai/schemas/format_evaluation.py
```

---

# Contexto de generación

`GenerationContext` conserva los parámetros utilizados durante la generación para que Data/IA pueda evaluar la adaptación del contenido.

Campos:

```text
profile
niche
detail_level
learning_objective
```

`learning_objective` es opcional.

---

# Chunks utilizados como evidencia

Cada elemento de `chunks_used` incluye:

```text
chunk_id
document_id
rank
score
text
```

Todos los chunks deben pertenecer al mismo `document_id` de la solicitud.

Data/IA necesita el texto completo de los chunks para evaluar el grado de respaldo del contenido generado.

---

# Scores de evaluación

El evaluator devuelve cuatro dimensiones:

```text
relevancia
coherencia
adaptacion_didactica
informacion_respaldada
```

Cada dimensión utiliza una escala de:

```text
1 — 5
```

---

## Relevancia

Evalúa si el contenido generado mantiene relación con:

- el objetivo de aprendizaje;
- el nicho;
- los conceptos relevantes del contexto.

---

## Coherencia

Evalúa si el contenido presenta una estructura mínima suficiente para ser utilizado como material educativo.

---

## Adaptación didáctica

Considera parámetros como:

```text
profile
detail_level
```

Por ejemplo, un contenido excesivamente largo para un perfil principiante puede requerir revisión.

---

## Información respaldada

Compara el contenido evaluable contra los chunks utilizados como evidencia.

Para Quiz se analizan principalmente:

```text
question
correct_answer
explanation
```

Los distractores no se consideran afirmaciones de conocimiento para la detección de información no respaldada.

Para Flashcards se evalúan:

```text
front
back
```

---

# Baseline heurístico

La versión actual de `quality_evaluator.py` implementa un **baseline heurístico léxico**.

Actualmente utiliza:

- normalización de texto;
- stopwords;
- términos significativos;
- coincidencia de vocabulario;
- proporción de términos respaldados;
- reglas simples de longitud y adaptación.

Esta implementación permite cerrar el flujo funcional de evaluación de Sprint 2.

No debe considerarse todavía un evaluador semántico avanzado.

Mejoras futuras pueden incluir:

- embeddings;
- similitud semántica;
- reranking;
- NLI;
- evaluación asistida por LLM;
- calibración de umbrales con dataset validado.

---

# Veredicto final

Las reglas de decisión están definidas en:

```text
data_ai/evaluation/rubric.py
```

Reglas actuales:

```text
informacion_no_respaldada = True
→ rechazado

algún score <= 2
→ rechazado

ningún score <= 2
y algún score == 3
→ requiere_revision

todos los scores >= 4
e informacion_no_respaldada = False
→ aprobado
```

Estados posibles:

```text
aprobado
requiere_revision
rechazado
```

---

# EvaluationResponse

Ejemplo:

```json
{
  "document_id": "DOC-001",
  "format": "quiz",
  "status": "aprobado",
  "scores": {
    "relevancia": 5,
    "coherencia": 5,
    "adaptacion_didactica": 5,
    "informacion_respaldada": 5
  },
  "informacion_no_respaldada": false,
  "observaciones": [
    "Aprobado: El contenido cumple con altos estándares de calidad."
  ]
}
```

---

# Estructura principal

```text
Data_IA/
│
├── data_ai/
│   ├── api/
│   │   └── app.py
│   │
│   ├── evaluation/
│   │   ├── quality_evaluator.py
│   │   ├── reviewer.py
│   │   └── rubric.py
│   │
│   ├── metrics/
│   │   ├── retrieval_evaluator.py
│   │   ├── retrieval_metrics.py
│   │   ├── retrieval_reporting.py
│   │   └── error_analysis.py
│   │
│   ├── schemas/
│   │   ├── evaluation.py
│   │   ├── format_evaluation.py
│   │   └── retrieval.py
│   │
│   ├── validators/
│   │
│   └── tests/
│
├── data/
│   └── evaluation/
│       ├── input/
│       ├── mock/
│       ├── results/
│       ├── chunks_v1.csv
│       ├── ground_truth_v1.csv
│       ├── ground_truth_v2.csv
│       ├── evaluation_manifest_v1.json
│       └── evaluation_manifest_v2.json
│
├── notebooks/
│   ├── 01_data_ai_corpus_ground_truth_v1.ipynb
│   ├── 02_data_ai_retrieval_evaluation_v1.ipynb
│   ├── 03_data_ai_retrieval_error_analysis_v1.ipynb
│   └── 04_data_ai_retrieval_evaluation_gt_v2.ipynb
│
├── docs/
│   ├── contracts/
│   └── Informe_Retrieval_v1_GT_v1_vs_GT_v2.pdf
│
├── requirements.txt
└── README.md
```

---

# Retrieval evaluation

Data/IA mantiene un benchmark reproducible para evaluar retrieval.

El contrato se encuentra en:

```text
docs/contracts/retrieval_contract_v1.md
```

El batch real utilizado se encuentra en:

```text
data/evaluation/input/retrieval_results_agentes_v1.json
```

---

## Ground Truth v1

Ground Truth original congelado.

Artefactos:

```text
ground_truth_v1.csv
evaluation_manifest_v1.json
```

Resultados principales:

```text
Recall@3 = 0.5400
Recall@5 = 0.7200

Precision@3 = 0.1867
Precision@5 = 0.1480
```

---

## Ground Truth v2

Versión ampliada después de revisión manual de casos con múltiples chunks válidos.

Artefactos:

```text
ground_truth_v2.csv
evaluation_manifest_v2.json
```

Resultados:

```text
Recall@3 = 0.573333
Recall@5 = 0.753333

Precision@3 = 0.213333
Precision@5 = 0.164000
```

El retrieval utilizado para ambas mediciones es el mismo.

La diferencia corresponde únicamente a la actualización del Ground Truth.

---

# Análisis de errores

Notebook:

```text
notebooks/03_data_ai_retrieval_error_analysis_v1.ipynb
```

Categorías utilizadas:

```text
AMBIGUEDAD_CONTEXTO
RANKING_SEMANTICO
ENTIDAD_LEXICAL
COMPETENCIA_INTRADOCUMENTO
PREGUNTA_INFERENCIAL
CHUNKING
EMBEDDING
GROUND_TRUTH
OTRO
```

---

# Pruebas automáticas

Ejecutar desde `Data_IA`:

```bash
python -m pytest data_ai/tests -v
```

Última validación funcional realizada durante Sprint 2:

```text
55 passed
```

También se validó manualmente el endpoint `/evaluate` con:

- Quiz válido;
- Flashcards válidas.

Ambos casos devolvieron:

```text
HTTP 200
status = aprobado
```

---

# Instalación

Crear entorno virtual:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

# Artefactos versionados

Los artefactos congelados no deben sobrescribirse.

Si cambia alguno de los siguientes elementos:

- corpus;
- chunking;
- Ground Truth;
- configuración de evaluación;

debe generarse una nueva versión.

Esto permite conservar:

- trazabilidad;
- reproducibilidad;
- comparación histórica de métricas.

---

# Estado actual

## Sprint 2

Completado:

```text
✅ Contratos Quiz / Flashcards
✅ GenerationContext
✅ Validation schemas
✅ EvaluationScores
✅ EvaluationResponse
✅ Quality evaluator baseline
✅ Reviewer
✅ Rúbrica
✅ POST /evaluate
✅ HTTP 200 para requests válidos
✅ Validación 422 para contratos inválidos
✅ Tests automáticos
✅ Prueba end-to-end Quiz
✅ Prueba end-to-end Flashcards
```

El siguiente trabajo corresponde a integración con el resto del sistema y mejoras del evaluator durante los siguientes sprints.
