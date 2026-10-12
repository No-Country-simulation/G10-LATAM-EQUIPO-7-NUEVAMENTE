# NuevaMente — Data/IA

Guía oficial del módulo Data/IA. Aquí se describe su responsabilidad, el
contrato de evaluación de formatos, el benchmark offline de retrieval, la
organización de datos y cómo ejecutar el servicio y sus pruebas.

Data/IA evalúa contenido educativo generado y mantiene herramientas y datos
para medir retrieval. No implementa el pipeline productivo de extracción,
chunking, embeddings, búsqueda ni generación; esas responsabilidades
pertenecen a [Agentes](../agentes/README.md). El flujo global del producto se
describe en el [README de la raíz](../README.md).

## Navegación

| Si buscas… | Consulta… |
|---|---|
| Responsabilidades y límites del módulo | [Alcance](#alcance) |
| API, request, respuesta y formatos aceptados | [API de evaluación](#api-de-evaluación) |
| Criterios, versión del evaluator y veredicto | [Evaluación de calidad](#evaluación-de-calidad) |
| Benchmark y análisis de retrieval | [Evaluación offline de retrieval](#evaluación-offline-de-retrieval) |
| Corpus controlado para comparar formatos de archivo | [Validación multiformato](#validación-multiformato) |
| Directorios y responsabilidades de código | [Mapa del módulo](#mapa-del-módulo) |
| Instalación, arranque y pruebas | [Operación local](#operación-local) |

## Alcance

Data/IA mantiene dos recorridos relacionados, pero separados:

1. **Evaluación integrada de formatos:** recibe desde BackendAPI el formato
   generado, el contexto de generación y los chunks que sirvieron como
   evidencia. Devuelve scores, veredicto y observaciones.
2. **Evaluación offline de retrieval:** valida respuestas de Agentes frente a
   un corpus y Ground Truth versionados; produce métricas y análisis de error.

Responsabilidades:

- contratos y validación de solicitudes y respuestas;
- evaluación de relevancia, coherencia, adaptación didáctica e información
  respaldada;
- rúbrica para aprobar, solicitar revisión o rechazar;
- mantenimiento reproducible de corpus, Ground Truth, métricas e informes.

La evaluación de calidad no genera contenido ni vuelve a ejecutar retrieval.
Usa la evidencia (`chunks_used`) que acompaña al resultado generado.

## API de evaluación

La aplicación FastAPI se define en `data_ai/api/app.py`.

| Método y ruta | Función |
|---|---|
| `GET /health` | Comprueba la disponibilidad del servicio. |
| `POST /evaluate` | Valida y evalúa un formato educativo generado. |

`POST /evaluate` acepta `format` como discriminador y valida `generated_content`
contra el esquema correspondiente. Los formatos definidos en el contrato son
`quiz`, `flashcards`, `tldr` y `video_script`.

La solicitud incluye:

- `document_id` y `format`;
- `generation_context`: `profile`, `niche`, `detail_level` y
  `learning_objective` opcional;
- `generated_content`, validado según el formato;
- `chunks_used`, con identificador, documento, ranking, score y texto de cada
  fragmento de evidencia.

La validación rechaza campos extra, contenido mal formado, identificadores
duplicados y chunks que no pertenezcan al `document_id` de la solicitud. Los
modelos completos y sus reglas están en
[`data_ai/schemas/format_evaluation.py`](data_ai/schemas/format_evaluation.py).

La respuesta contiene `document_id`, `format`, `status`, `scores`,
`informacion_no_respaldada` y `observaciones`; también incluye las versiones de
evaluator y rúbrica. Los estados posibles son `aprobado`,
`requiere_revision` y `rechazado`.

## Evaluación de calidad

El flujo de evaluación es:

```text
POST /evaluate
  -> validación FastAPI / Pydantic
  -> reviewer.evaluar_contenido
  -> quality_evaluator.evaluate
  -> rubric.calcular_veredicto_evaluacion
  -> respuesta estructurada
```

Se puntúan cuatro dimensiones, cada una de 1 a 5:

| Dimensión | Criterio general |
|---|---|
| `relevancia` | Relación del contenido con la fuente y el contexto de aprendizaje. |
| `coherencia` | Claridad, estructura y consistencia lógica. |
| `adaptacion_didactica` | Adecuación al perfil y al nivel de detalle. |
| `informacion_respaldada` | Grado de respaldo en los chunks recibidos. |

La detección de respaldo se aplica al contenido factual de cada formato. Por
ejemplo, no trata los distractores del Quiz como afirmaciones factuales; en un
resumen evalúa el resumen, los puntos clave y la conclusión, y en un guion de
video evalúa la narración, no las instrucciones visuales.

El evaluator actual es un baseline heurístico léxico (versión `1.1.0`), no un
evaluador semántico avanzado. Normaliza mayúsculas y acentos y compara términos
significativos con la evidencia. La versión de rúbrica actual es `1.0.0`.

Reglas del veredicto:

- se **rechaza** si se detecta información no respaldada o algún score es
  menor o igual a 2;
- se marca **requiere revisión** si no hay scores menores o iguales a 2, pero
  alguno es 3;
- se **aprueba** si todos los scores son al menos 4 y no hay información no
  respaldada.

La integración técnica de los cuatro formatos y la comparación de evaluator
V1.0/V1.1 están documentadas en
[Validación multiformato end-to-end](data/format_corpus_v1/results/multiformat_end_to_end/README.md).

## Evaluación offline de retrieval

Este benchmark mide el comportamiento del retrieval de Agentes; no forma
parte de la búsqueda ejecutada por el endpoint `/evaluate`.

El conjunto de evaluación contiene corpus y Ground Truth versionados. Los
artefactos congelados no deben sobrescribirse: cualquier cambio de corpus,
chunking, Ground Truth o configuración debe producir una nueva versión y un
manifest que permita reproducir la corrida.

| Recurso | Ubicación |
|---|---|
| Corpus de chunks congelado | [`data/evaluation/chunks_v1.csv`](data/evaluation/chunks_v1.csv) |
| Ground Truth v1 y v2 | [`data/evaluation/`](data/evaluation) |
| Respuestas de Agentes usadas como entrada | [`data/evaluation/input/`](data/evaluation/input) |
| Contrato histórico Retrieval v1 | [`docs/contracts/retrieval_contract_v1.md`](docs/contracts/retrieval_contract_v1.md) |
| Resultados detallados Retrieval V2 | [`data/evaluation/results/retrieval_v2/README.md`](data/evaluation/results/retrieval_v2/README.md) |
| Ablation study y configuración recomendada | [`data/evaluation/results/retrieval_v2_ablation/README.md`](data/evaluation/results/retrieval_v2_ablation/README.md) |

El benchmark calcula Recall@K y Precision@K y conserva resultados, manifests
y análisis de error en `data/evaluation/results/`. Los notebooks de
`notebooks/` documentan preparación de Ground Truth, evaluación y análisis.
Las métricas solo son comparables cuando se usa el mismo corpus, versión de
Ground Truth y configuración declarados en el manifest correspondiente.

El contrato v1 se conserva como referencia histórica. Para el contrato de
runtime y sus cambios vigentes, consulta la documentación de
[Agentes](../agentes/README.md).

## Validación multiformato

`data/format_corpus_v1/` contiene representaciones Markdown, TXT y PDF de un
mismo corpus controlado. Permite estudiar el efecto del formato de entrada
manteniendo constante el contenido semántico; es independiente del benchmark
congelado de retrieval.

- [Descripción del corpus controlado](data/format_corpus_v1/README.md)
- [Resultados de retrieval por formato](data/format_corpus_v1/results/retrieval_v2/README.md)
- [Validación técnica end-to-end de 3 formatos fuente por 4 formatos generados](data/format_corpus_v1/results/multiformat_end_to_end/README.md)

Los documentos fuente y sus versiones derivadas son datos experimentales, no
guías de implementación. Para regenerar el corpus se utiliza
`scripts/build_controlled_format_corpus.py`.

## Mapa del módulo

```text
Data_IA/
├── data_ai/
│   ├── api/             # Aplicación FastAPI
│   ├── evaluation/      # Evaluator, reviewer, rúbrica y configuración
│   ├── loaders/         # Carga de resultados de retrieval
│   ├── metrics/         # Métricas, reportes y análisis de error
│   ├── schemas/         # Contratos de evaluación y retrieval
│   ├── validators/      # Validación de documentos y resultados
│   └── tests/           # Pruebas unitarias y de API
├── data/
│   ├── evaluation/      # Corpus, Ground Truth, manifests, entradas y resultados
│   └── format_corpus_v1/# Corpus controlado para pruebas multiformato
├── docs/contracts/      # Contratos documentados y versionados
├── notebooks/           # Preparación, evaluación y análisis experimental
├── scripts/             # Generación de corpus y runners/diagnósticos
├── requirements.txt
└── README.md
```

Puntos de entrada frecuentes:

| Necesidad | Archivo o carpeta |
|---|---|
| Cambiar rutas HTTP | `data_ai/api/app.py` |
| Cambiar esquemas de evaluación de formatos | `data_ai/schemas/format_evaluation.py` |
| Cambiar evaluación de calidad | `data_ai/evaluation/quality_evaluator.py` |
| Cambiar reglas del veredicto | `data_ai/evaluation/rubric.py` |
| Cambiar carga/validación de resultados de retrieval | `data_ai/loaders/`, `data_ai/validators/` |
| Cambiar métricas o reportes de retrieval | `data_ai/metrics/` |
| Añadir o actualizar pruebas | `data_ai/tests/` |
| Crear benchmarks reproducibles | `notebooks/`, `scripts/` y `data/evaluation/` |

## Operación local

Ejecuta los comandos desde `Data_IA/`.

### Instalar dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

En macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Iniciar la API

```bash
python -m uvicorn data_ai.api.app:app --reload --port 8000
```

La documentación interactiva de FastAPI queda disponible en
`http://127.0.0.1:8000/docs`.

### Ejecutar pruebas

```bash
python -m pytest data_ai/tests
```

### Ejecutar scripts y notebooks

Los scripts de `scripts/` pueden ejecutarse desde la raíz del repositorio
según la ruta indicada en cada uno. Los notebooks de `notebooks/` registran
los parámetros, las versiones de los datos y el análisis asociado; antes de
comparar resultados, verifica el manifest y no reemplaces salidas históricas.

## Documentación relacionada

- [README de Agentes](../agentes/README.md): indexación, retrieval y generación.
- [README de BackendAPI](../backend/README.md): integración HTTP y persistencia
  de las evaluaciones recibidas.
- [README del corpus controlado](data/format_corpus_v1/README.md): diseño y
  reproducibilidad de las entradas MD/TXT/PDF.
