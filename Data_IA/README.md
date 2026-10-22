# NuevaMente — Data/IA

Guía oficial del módulo Data/IA. Aquí se describen sus responsabilidades,
los endpoints V1.1 y V2 de evaluación de formatos, el benchmark offline de
retrieval, la organización de datos y cómo ejecutar el servicio y sus pruebas.

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
| Contratos activos V1.1 y V2, y Semantic Evaluator | [API de evaluación](#api-de-evaluación) |
| Criterios, versión del evaluator y veredicto | [Evaluación de calidad](#evaluación-de-calidad) |
| Benchmark y análisis de retrieval | [Evaluación offline de retrieval](#evaluación-offline-de-retrieval) |
| Corpus controlado para comparar formatos de archivo | [Validación multiformato](#validación-multiformato) |
| Directorios y responsabilidades de código | [Mapa del módulo](#mapa-del-módulo) |
| Instalación, arranque y pruebas | [Operación local](#operación-local) |

## Alcance

Data/IA mantiene tres recorridos relacionados, pero separados:

1. **Evaluación integrada de formatos:** recibe desde BackendAPI el formato
   generado, el contexto de generación y los chunks que sirvieron como
   evidencia. `POST /evaluate` mantiene la respuesta V1.1 y
   `POST /evaluate/v2` devuelve señales heurísticas y semánticas separadas.

2. **Evaluación offline de retrieval:** valida respuestas de Agentes frente a
   un corpus y Ground Truth versionados; produce métricas y análisis de error.

3. **Calibración y experimentación:** conserva datasets, protocolos y
   resultados reproducibles utilizados para investigar mejoras potenciales
   del evaluador sin incorporarlas automáticamente al pipeline productivo.

Responsabilidades:

- contratos y validación de solicitudes y respuestas;
- evaluación de relevancia, coherencia, adaptación didáctica e información
  respaldada;
- rúbrica para aprobar, solicitar revisión o rechazar;
- evaluación semántica estructurada en Evaluation V2;
- mantenimiento reproducible de corpus, Ground Truth, métricas e informes.

La evaluación de calidad no genera contenido ni vuelve a ejecutar retrieval.
Usa la evidencia (`chunks_used`) que acompaña al resultado generado.

## API de evaluación

La aplicación FastAPI se define en `data_ai/api/app.py`.

| Método y ruta | Función |
|---|---|
| `GET /health` | Comprueba la disponibilidad del servicio. |
| `POST /evaluate` | Evaluación V1.1, conservada por compatibilidad. |
| `POST /evaluate/v2` | Evaluation V2 activa, con señales heurísticas y semánticas separadas. |

Ambos endpoints aceptan el mismo request tipado y discriminado por `format`.
El cuerpo incluye `document_id`, `format`, `generation_context`,
`generated_content` y `chunks_used`; los modelos rechazan campos adicionales.
Los formatos soportados son `quiz`, `flashcards`, `tldr` y `video_script`.
`generated_content` se valida según el formato. `generation_context` contiene
`profile`, `niche`, `detail_level` y `learning_objective` opcional;
`chunks_used` contiene los fragmentos de evidencia, cada uno con `chunk_id`,
`document_id`, `rank`, `score` y `text`.

La validación también rechaza contenido mal formado, identificadores
duplicados y chunks que no pertenezcan al `document_id` de la solicitud. Los
modelos completos y sus reglas están en
[`data_ai/schemas/format_evaluation.py`](data_ai/schemas/format_evaluation.py).

La respuesta de `POST /evaluate` contiene `document_id`, `format`, `status`,
`scores`, `informacion_no_respaldada` y `observaciones`; también incluye las
versiones de evaluator y rúbrica.

Los estados posibles del contrato V1.1 son:

- `aprobado`;
- `requiere_revision`;
- `rechazado`.

### Evaluation V2

`POST /evaluate/v2` implementa el contrato V2 y coexiste con
`POST /evaluate`; no reemplaza ni modifica la respuesta V1.1. BackendAPI
configura actualmente esta ruta mediante `DATA_IA_EVALUATE_PATH=/evaluate/v2`.

La respuesta mantiene separadas las dos señales de evaluación:

- `heuristic_scores`: scores producidos por el evaluator heurístico;
- `semantic_evaluation`: resultado producido por el Semantic Evaluator.

Dentro de `semantic_evaluation` se exponen:

- `status`;
- `scores`;
- `observations`;
- `recommendations`;
- `unsupported_information`;
- `error_code` y `error_message` cuando corresponde;
- `model`;
- `prompt_version`;
- `latency_ms`.

Las dimensiones semánticas evaluadas son:

- `relevance`;
- `coherence`;
- `didactic_adaptation`;
- `content_support`.

Los scores heurísticos y semánticos no se ponderan ni combinan. Actualmente no
existe un `final_score`, `combined_score` ni `weighted_score`.

El `verdict` V2 se mapea actualmente desde el veredicto heurístico V1.1:
`aprobado` → `approved`, `requiere_revision` → `requires_revision` y
`rechazado` → `rejected`. Si el evaluator heurístico no produce una señal
válida, el veredicto permanece `null`. Un resultado semántico exitoso no
genera ni modifica por sí solo el veredicto.

La forma principal de la respuesta V2 es:

```json
{
  "document_id": "doc_123",
  "format": "tldr",
  "verdict": "approved",
  "heuristic_scores": {
    "relevance": 4.0,
    "coherence": 4.0,
    "didactic_adaptation": 4.0,
    "content_support": 4.0
  },
  "semantic_evaluation": {
    "status": "unavailable",
    "scores": null,
    "observations": [],
    "recommendations": [],
    "unsupported_information": [],
    "error_code": "not_configured",
    "error_message": "Semantic provider is not configured.",
    "model": null,
    "prompt_version": "semantic-evaluator-v0.1",
    "latency_ms": 1
  },
  "evaluator_version": "1.1.0",
  "rubric_version": "1.0.0"
}
```

Los valores del ejemplo ilustran la estructura; los scores y el veredicto
dependen del contenido evaluado. Cuando el proveedor semántico se ejecuta,
`status` es `success` y `scores` contiene las cuatro dimensiones. Ante un fallo
técnico puede ser `failed`; si no hay configuración del proveedor, es
`unavailable`. Esos estados describen al componente semántico, no la calidad
global del formato ni el `verdict`.

Para la dimensión `content_support`, `chunks_used` es la única evidencia
factual válida.

`generation_context` puede utilizarse para evaluar relevancia y adaptación
didáctica, pero no debe utilizarse como evidencia factual.

#### Semantic Provider

El Semantic Evaluator utiliza Gemini cuando están configuradas las siguientes
variables de entorno:

```env
DATA_IA_GEMINI_API_KEY=
DATA_IA_GEMINI_MODEL=
```

Cuando ambas variables están disponibles, Data/IA construye un
`GeminiSemanticProvider`.

Si falta cualquiera de las dos variables, utiliza
`UnavailableSemanticProvider` como fallback controlado.

En ese caso, `semantic_evaluation` devuelve:

```text
status = unavailable
error_code = not_configured
scores = null
```

Este fallback:

- no fabrica scores semánticos;
- no genera un error HTTP por falta de configuración;
- no impide que la evaluación heurística continúe;
- permite mantener operativo el contrato V2 aunque Gemini no esté configurado.

Los errores técnicos del proveedor semántico se normalizan para mantenerlos
separados de las decisiones de calidad del contenido.

Los estados semánticos posibles son:

- `success`;
- `failed`;
- `unavailable`.

## Evaluación de calidad

El flujo V1.1 de evaluación es:

```text
POST /evaluate
  -> validación FastAPI / Pydantic
  -> reviewer.evaluar_contenido
  -> quality_evaluator.evaluate
  -> rubric.calcular_veredicto_evaluacion
  -> respuesta estructurada
```

El flujo V2 agrega la evaluación semántica sin reemplazar el evaluador
heurístico:

```text
POST /evaluate/v2
  -> validación FastAPI / Pydantic
  -> evaluación heurística
  -> SemanticEvaluator
      -> SemanticProvider
          -> GeminiSemanticProvider
          o
          -> UnavailableSemanticProvider
  -> Evaluation V2 Builder
  -> respuesta estructurada
```

Se puntúan cuatro dimensiones, cada una de 1 a 5:

| Dimensión V1.1 | Equivalente V2 | Criterio general |
|---|---|---|
| `relevancia` | `relevance` | Relación del contenido con la fuente y el contexto de aprendizaje. |
| `coherencia` | `coherence` | Claridad, estructura y consistencia lógica. |
| `adaptacion_didactica` | `didactic_adaptation` | Adecuación al perfil y al nivel de detalle. |
| `informacion_respaldada` | `content_support` | Grado de respaldo en los chunks recibidos. |

La detección de respaldo se aplica al contenido factual de cada formato.

Por ejemplo:

- en Quiz no se tratan los distractores como afirmaciones factuales;
- en TLDR se evalúan resumen, puntos clave y conclusión;
- en Video Script se evalúa la narración, no las instrucciones visuales;
- en Flashcards se evalúa el contenido educativo de frente y reverso.

Data/IA conserva el evaluator heurístico léxico V1.1 y añade en Evaluation V2
un Semantic Evaluator independiente basado en LLM-as-a-Judge.

Ambas señales permanecen separadas y todavía no se ponderan ni combinan.

El evaluator heurístico continúa siendo la fuente del veredicto global; no hay
una Decision Layer calibrada que combine ambas señales.

La versión V1.1 normaliza mayúsculas y acentos y compara términos
significativos con la evidencia.

Reglas actuales del veredicto heurístico:

- se **rechaza** si se detecta información no respaldada o algún score es
  menor o igual a 2;
- se marca **requiere revisión** si no hay scores menores o iguales a 2, pero
  alguno es 3;
- se **aprueba** si todos los scores son al menos 4 y no hay información no
  respaldada.

La integración técnica de los cuatro formatos y la comparación de evaluator
V1.0/V1.1 están documentadas en
[Validación multiformato end-to-end](data/format_corpus_v1/results/multiformat_end_to_end/README.md).

La especificación del evaluador semántico y del contrato V2 se encuentra en:

- [`docs/evaluation_contract_v2.md`](docs/evaluation_contract_v2.md);
- [`docs/evaluation_contract_v2_compatibility.md`](docs/evaluation_contract_v2_compatibility.md);
- [`docs/semantic_rubric_v0_1.md`](docs/semantic_rubric_v0_1.md);
- [`docs/semantic_schema_v0_1.md`](docs/semantic_schema_v0_1.md);
- [`docs/sprint4_integration_decisions.md`](docs/sprint4_integration_decisions.md).

## Evaluación offline de retrieval

Este benchmark mide el comportamiento del retrieval de Agentes; no forma
parte de la búsqueda ejecutada por los endpoints `/evaluate` o `/evaluate/v2`.

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
y análisis de error en `data/evaluation/results/`.

Los notebooks de `notebooks/` documentan preparación de Ground Truth,
evaluación y análisis.

Las métricas solo son comparables cuando se usa el mismo corpus, versión de
Ground Truth y configuración declarados en el manifest correspondiente.

El contrato v1 se conserva como referencia histórica. Para el contrato de
runtime y sus cambios vigentes, consulta la documentación de
[Agentes](../agentes/README.md).

## Validación multiformato

`data/format_corpus_v1/` contiene representaciones Markdown, TXT y PDF de un
mismo corpus controlado.

Permite estudiar el efecto del formato de entrada manteniendo constante el
contenido semántico; es independiente del benchmark congelado de retrieval.

- [Descripción del corpus controlado](data/format_corpus_v1/README.md)
- [Resultados de retrieval por formato](data/format_corpus_v1/results/retrieval_v2/README.md)
- [Validación técnica end-to-end de 3 formatos fuente por 4 formatos generados](data/format_corpus_v1/results/multiformat_end_to_end/README.md)

Los documentos fuente y sus versiones derivadas son datos experimentales, no
guías de implementación.

Para regenerar el corpus se utiliza
`scripts/build_controlled_format_corpus.py`.

## Calibración y experimentación

Data/IA conserva experimentos reproducibles utilizados para investigar y
calibrar posibles mejoras del sistema de evaluación.

Estos experimentos están separados del comportamiento productivo de
`POST /evaluate/v2` y no modifican automáticamente el verdict.

Entre los principales artefactos se encuentran:

- calibración del Semantic Evaluator;
- análisis de `content_support`;
- extensiones controladas de calibración;
- Claim Atomization v1;
- validación externa de Claim Atomization v0.4.

### Claim Atomization v0.4

Claim Atomization estudió la posibilidad de dividir claims complejos en
unidades semánticas evaluables de manera independiente.

Después de las evaluaciones internas se realizó una validación externa
congelada sobre 80 casos procedentes de documentación técnica oficial.

El benchmark externo incluyó:

- 20 casos `atomic`;
- 20 casos `compound`;
- 20 casos `relational`;
- 20 casos `non_propositional`;
- cinco dominios técnicos.

Los principales resultados externos fueron:

| Métrica | Resultado |
|---|---:|
| Exact structure accuracy | 0.3833 |
| Count accuracy | 0.5167 |
| Type-sequence accuracy | 0.4167 |
| Non-propositional precision | 0.9375 |
| Non-propositional recall | 0.7500 |
| Fully stable rate | 0.6875 |

La evidencia externa no confirmó una generalización estructural suficiente
para integrar `claim-atomizer-v0.4` al flujo productivo.

Decisión final:

```text
STOP_V0_4_FOR_PRODUCTION_INTEGRATION
```

Por tanto, Claim Atomization v0.4:

- permanece experimental;
- no modifica `/evaluate/v2`;
- no modifica `content_support`;
- no cambia el verdict;
- no se integra al Semantic Evaluator productivo.

El reporte final y autoritativo se encuentra en:

[`docs/claim_atomization_v0_4_external_validation_final.md`](docs/claim_atomization_v0_4_external_validation_final.md).

## Mapa del módulo

```text
Data_IA/
├── data_ai/
│   ├── api/             # Aplicación FastAPI
│   ├── evaluation/      # Evaluators, providers, reviewer y rúbrica
│   ├── loaders/         # Carga de resultados de retrieval
│   ├── metrics/         # Métricas, reportes y análisis de error
│   ├── schemas/         # Contratos de evaluación y retrieval
│   ├── validators/      # Validación de documentos y resultados
│   └── tests/           # Pruebas unitarias y de API
├── data/
│   ├── evaluation/      # Corpus, Ground Truth, manifests, entradas y resultados
│   └── format_corpus_v1/# Corpus controlado para pruebas multiformato
├── docs/                # Contratos, rúbricas y decisiones de integración
├── notebooks/           # Preparación, evaluación y análisis experimental
├── scripts/             # Generación de corpus y runners/diagnósticos
├── .env.example         # Variables de entorno documentadas sin secretos
├── requirements.txt
└── README.md
```

Puntos de entrada frecuentes:

| Necesidad | Archivo o carpeta |
|---|---|
| Cambiar rutas HTTP | `data_ai/api/app.py` |
| Cambiar esquemas V1.1 | `data_ai/schemas/format_evaluation.py` |
| Cambiar contrato V2 | `data_ai/schemas/evaluation_v2.py` |
| Cambiar esquema semántico | `data_ai/schemas/semantic_evaluation.py` |
| Cambiar evaluación heurística | `data_ai/evaluation/quality_evaluator.py` |
| Cambiar orquestación V2 | `data_ai/evaluation/evaluation_v2_service.py` |
| Cambiar ensamblado o mapeo V2 | `data_ai/evaluation/evaluation_v2_builder.py`, `data_ai/evaluation/evaluation_v2_mapper.py` |
| Cambiar Semantic Evaluator | `data_ai/evaluation/semantic_evaluator.py` |
| Cambiar configuración del evaluator y versiones | `data_ai/evaluation/config.py` |
| Cambiar integración Gemini | `data_ai/evaluation/gemini_semantic_provider.py` |
| Cambiar interfaz del provider semántico | `data_ai/evaluation/semantic_provider.py` |
| Cambiar selección de provider | `data_ai/evaluation/semantic_provider_factory.py` |
| Cambiar reglas del veredicto | `data_ai/evaluation/rubric.py` |
| Cambiar carga/validación de retrieval | `data_ai/loaders/`, `data_ai/validators/` |
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

### Configuración opcional del Semantic Evaluator

Para habilitar Gemini en Evaluation V2, configura:

```env
DATA_IA_GEMINI_API_KEY=<api-key>
DATA_IA_GEMINI_MODEL=<modelo>
```

También existe un archivo de referencia sin secretos:

```text
Data_IA/.env.example
```

con:

```env
DATA_IA_GEMINI_API_KEY=
DATA_IA_GEMINI_MODEL=
```

No deben almacenarse API keys reales en Git.

En despliegue, Data/IA lee estas variables desde un archivo externo al
repositorio:

```text
/opt/nuevamente/env/data-ia.env
```

El archivo real de despliegue debe contener:

```env
DATA_IA_GEMINI_API_KEY=<api-key-real>
DATA_IA_GEMINI_MODEL=<modelo-configurado>
```

Este archivo debe existir en el servidor antes de ejecutar Docker Compose.

### Iniciar la API

```bash
python -m uvicorn data_ai.api.app:app --reload --port 8000
```

La documentación interactiva de FastAPI queda disponible en:

```text
http://127.0.0.1:8000/docs
```

En Docker, el servicio Data/IA utiliza el puerto `8002`.

### Ejecutar pruebas

```bash
python -m pytest data_ai/tests
```

### Ejecutar scripts y notebooks

Los scripts de `scripts/` pueden ejecutarse desde la raíz del repositorio
según la ruta indicada en cada uno.

Los notebooks de `notebooks/` registran los parámetros, las versiones de los
datos y el análisis asociado.

Antes de comparar resultados, verifica el manifest correspondiente y no
reemplaces salidas históricas.

## Documentación relacionada

- [README de Agentes](../agentes/README.md): indexación, retrieval y generación.
- [README de BackendAPI](../backend/README.md): integración HTTP y persistencia
  de las evaluaciones recibidas.
- [README del corpus controlado](data/format_corpus_v1/README.md): diseño y
  reproducibilidad de las entradas MD/TXT/PDF.
- [Evaluation Contract V2](docs/evaluation_contract_v2.md): contrato público
  de Evaluation V2.
- [Semantic Rubric v0.1](docs/semantic_rubric_v0_1.md): criterios del
  Semantic Evaluator.

## Pendientes técnicos identificados

Esta sección registra límites observables en el código actual; no representa
un backlog priorizado:

- V1.1 y V2 coexisten. V2 está publicado en `/evaluate/v2`, mientras
  `/evaluate` conserva el contrato V1.1.
- V2 no tiene una Decision Layer calibrada: el `verdict` se deriva del
  evaluator heurístico y las señales semánticas no se combinan con esos scores.
- La evaluación semántica requiere configurar `DATA_IA_GEMINI_API_KEY` y
  `DATA_IA_GEMINI_MODEL`; sin ellas, V2 responde con estado semántico
  `unavailable`, pero mantiene la evaluación heurística.
- La evaluación offline de retrieval es un benchmark de análisis y no una API
  de búsqueda o retrieval del servicio Data/IA.