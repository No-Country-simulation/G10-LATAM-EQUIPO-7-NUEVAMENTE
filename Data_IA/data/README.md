# Datos — Data/IA

Esta carpeta contiene los datasets, artefactos congelados, entradas,
resultados y corpus experimentales utilizados por el módulo Data/IA de
NuevaMente.

Los datos se organizan por propósito para mantener trazabilidad,
reproducibilidad y separación entre benchmarks oficiales y experimentos.

## Estructura general

```text
data/
├── raw/
├── processed/
├── evaluation/
│   ├── chunks_v1.csv
│   ├── ground_truth_v1.csv
│   ├── ground_truth_v1.xlsx
│   ├── ground_truth_v2.csv
│   ├── ground_truth_v2.xlsx
│   ├── evaluation_manifest_v1.json
│   ├── evaluation_manifest_v2.json
│   ├── input/
│   ├── mock/
│   ├── results/
│   │   ├── retrieval_v2/
│   │   └── retrieval_v2_ablation/
│   ├── calibration_v1/
│   ├── calibration_extension_v1/
│   ├── atomization_v1/
│   └── atomization_external_v1/
└── format_corpus_v1/
    ├── md/
    ├── txt/
    ├── pdf/
    ├── validation/
    └── results/
```

## `raw/`

Conserva archivos fuente cuando se requiere mantener una representación
original previa al procesamiento.

No todos los experimentos necesitan utilizar directamente esta carpeta.

## `processed/`

Contiene los documentos normalizados utilizados como base para distintos
experimentos y procesos de evaluación.

Estos documentos también sirven como fuente para construir el corpus
controlado multiformato.

## `evaluation/`

Contiene los recursos utilizados para evaluar Retrieval y distintos
experimentos del módulo Data/IA.

### Benchmark congelado de Retrieval

Los principales artefactos históricos son:

- `chunks_v1.csv`
- `ground_truth_v1.csv`
- `ground_truth_v2.csv`
- `evaluation_manifest_v1.json`
- `evaluation_manifest_v2.json`

Estos archivos forman parte de benchmarks versionados.

Los artefactos congelados no deben sobrescribirse para incorporar una nueva
configuración, Ground Truth o estrategia de chunking.

Cuando cambie alguno de esos elementos debe crearse una nueva versión.

### `input/`

Contiene resultados obtenidos desde Agentes que se utilizan como entrada para
evaluaciones offline.

### `mock/`

Contiene payloads controlados para pruebas de contratos, errores y respuestas
de evaluación.

### `results/`

Conserva resultados reproducibles derivados de los benchmarks de Retrieval.

Entre los resultados principales se encuentran:

```text
results/retrieval_v2/
results/retrieval_v2_ablation/
```

`retrieval_v2/` documenta el benchmark principal del pipeline híbrido.

`retrieval_v2_ablation/` conserva las ablaciones utilizadas para estudiar el
aporte de:

- metadata filtering;
- búsqueda vectorial;
- BM25;
- RRF;
- Cross-Encoder;
- variantes de weighted RRF;
- combinaciones experimentales de señales.

Los README ubicados dentro de estas carpetas son la referencia principal para
interpretar sus métricas.

## Calibración

### `calibration_v1/`

Contiene el conjunto y los resultados utilizados durante la calibración del
Semantic Evaluator y el análisis de `content_support`.

### `calibration_extension_v1/`

Extiende la evidencia de calibración con casos adicionales sin modificar los
artefactos congelados de `calibration_v1`.

Los experimentos de calibración no deben interpretarse automáticamente como
comportamiento productivo del sistema.

## Claim Atomization

### `atomization_v1/`

Contiene los datasets de desarrollo, validación y evaluación utilizados
durante el experimento Claim Atomization v1.

Claim Atomization es un componente experimental y no forma parte del pipeline
productivo de `/evaluate/v2`.

### `atomization_external_v1/`

Contiene la validación externa final de `claim-atomizer-v0.4`, incluyendo:

- datasets;
- Ground Truth;
- fuentes externas;
- manifests;
- predicciones;
- retries;
- análisis de fallos;
- prueba de estabilidad;
- resultados finales.

La decisión final de esta evaluación fue:

```text
STOP_V0_4_FOR_PRODUCTION_INTEGRATION
```

Por tanto, `claim-atomizer-v0.4` permanece como artefacto experimental y no
modifica:

- `/evaluate/v2`;
- `content_support`;
- el Semantic Evaluator productivo;
- los verdicts;
- BackendAPI;
- Agentes;
- Frontend.

El reporte autoritativo se encuentra en:

```text
Data_IA/docs/claim_atomization_v0_4_external_validation_final.md
```

## `format_corpus_v1/`

Contiene el corpus controlado utilizado para comparar el comportamiento del
pipeline frente a tres formatos de entrada equivalentes:

- Markdown;
- TXT;
- PDF.

Cada representación conserva el mismo contenido semántico para permitir
comparaciones controladas de extracción, chunking, retrieval y evaluación.

Este corpus es independiente del benchmark congelado ubicado en
`data/evaluation/`.

Consulta:

```text
Data_IA/data/format_corpus_v1/README.md
```

para conocer su metodología y reglas de reproducibilidad.

## Regla de versionado

No sobrescribir artefactos congelados utilizados para producir métricas
históricas.

Si cambia alguno de los siguientes elementos:

- Ground Truth;
- corpus;
- chunking;
- normalización;
- modelo;
- configuración del retrieval;
- protocolo experimental;

debe generarse una nueva versión del artefacto y, cuando corresponda, un nuevo
manifest.

Ejemplo:

```text
ground_truth_v1.csv
ground_truth_v2.csv
```

en lugar de reemplazar silenciosamente:

```text
ground_truth_v1.csv
```

Esta política permite conservar la reproducibilidad de las métricas y la
trazabilidad de las decisiones experimentales.

## Documentación relacionada

Para una visión general del módulo:

```text
Data_IA/README.md
```

Para Retrieval V2:

```text
Data_IA/data/evaluation/results/retrieval_v2/README.md
```

Para el estudio de ablaciones:

```text
Data_IA/data/evaluation/results/retrieval_v2_ablation/README.md
```

Para el corpus multiformato:

```text
Data_IA/data/format_corpus_v1/README.md
```

Para el cierre de Claim Atomization v0.4:

```text
Data_IA/docs/claim_atomization_v0_4_external_validation_final.md
```