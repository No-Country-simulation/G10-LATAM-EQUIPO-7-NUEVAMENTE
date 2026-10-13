# NuevaMente — Sprint 4 Integration Decisions

**Estado:** Draft acordado para implementación  
**Sprint:** 4  
**Áreas involucradas:** Data/IA, Agentes, BackendAPI  
**Objetivo:** Registrar decisiones de integración entre Retrieval v2.0, generación de contenido y el nuevo evaluador semántico de Data/IA.

---

# 1. Contexto

Durante Sprint 4 el equipo de Agentes propuso una evolución de sus contratos Pydantic y confirmó la implementación HTTP del contrato Retrieval v2.0.

La propuesta mantiene separadas tres responsabilidades:

```text
Retrieval
↓
Generación
↓
Evaluación de calidad
```

Cada capa conserva su propio contrato y vocabulario.

Este documento registra las decisiones acordadas para evitar incompatibilidades entre:

```text
Agentes
Data/IA
BackendAPI
```

---

# 2. Principio general

No se intentará unificar artificialmente todos los estados, errores o schemas del sistema.

La prioridad será:

```text
consistencia dentro de cada contrato
+
compatibilidad entre servicios
```

en lugar de:

```text
usar exactamente los mismos nombres en todas las capas
```

---

# 3. Contratos de contenido generativo

El equipo de Agentes propone un esquema de dos capas.

## Capa 1 — Modelos enviados a Gemini

Los modelos de contenido pedagógico:

```text
LearningMetadata
QuizContent
FlashcardsContent
TLDRContent
VideoScriptContent
```

pueden utilizarse como `response_schema` del proveedor.

Por esta razón deben evitar restricciones de JSON Schema que el proveedor pueda rechazar.

Ejemplos de restricciones que no deben introducirse innecesariamente en estos schemas:

```text
minItems
maxItems
additionalProperties
pattern
```

cuando puedan provocar incompatibilidad con Gemini.

---

# 4. Validación posterior a Gemini

Las reglas semánticas o determinísticas se ejecutarán después de recibir la respuesta del modelo.

Ejemplos:

```text
normalización de espacios
eliminación de duplicados
reparación de IDs repetidos
recalcular duración total del video
```

Estas correcciones deben resolverse en código cuando puedan realizarse sin inventar contenido.

---

# 5. Regla reparar vs rechazar

Se adopta el principio:

```text
reparar lo determinista
rechazar únicamente lo irreparable
```

Ejemplos reparables:

```text
IDs duplicados
IDs vacíos
espacios redundantes
duración total de video inconsistente
listas duplicadas
```

Ejemplo no reparable sin inventar contenido:

```text
correct_answer no coincide con ninguna option
```

Ese tipo de salida debe considerarse:

```text
INVALID_MODEL_OUTPUT
```

y puede marcarse como reintentable según el contrato de Agentes.

---

# 6. Separación respecto al evaluador semántico Data/IA

Los schemas de generación pertenecen al servicio de Agentes.

Los schemas:

```text
SemanticScores
SemanticObservation
SemanticRecommendation
UnsupportedClaim
SemanticEvaluationResult
```

pertenecen a Data/IA.

No deben trasladarse a:

```text
agentes/generated_schemas.py
```

salvo que en el futuro exista un contrato explícito que lo requiera.

---

# 7. Fuente de evidencia para Data/IA

La evidencia factual recibida por Data/IA proviene de los chunks recuperados por Retrieval.

Campos relevantes:

```text
rank
chunk_id
document_id
score
text
```

El `score` debe interpretarse según:

```text
score_type = "cross_encoder"
```

---

# 8. Semántica del CrossEncoder score

El score utilizado por Retrieval v2.0 corresponde al CrossEncoder.

Debe interpretarse como:

```text
mayor score
=
mayor relevancia relativa dentro de esa búsqueda
```

No debe interpretarse como:

```text
probabilidad
```

ni asumirse comparable directamente entre queries distintas.

---

# 9. Retrieval Contract v2.0

El contrato Retrieval v2.0 conserva:

```text
contract_version = "2.0"
```

y:

```text
score_type = "cross_encoder"
```

Estados válidos:

```text
success
no_results
error
```

---

# 10. Contrato de generación

El endpoint de generación conserva:

```text
success
failed
no_results
```

para resultados individuales.

Esto es deliberadamente diferente de Retrieval.

---

# 11. Decisión sobre status

Se acuerda mantener:

## Retrieval

```text
success
no_results
error
```

## Generation

```text
success
failed
no_results
```

No se intentará renombrar `error` como `failed` ni viceversa durante Sprint 4.

---

# 12. Razón

`error` en Retrieval y `failed` en generación pertenecen a contratos y dominios distintos.

La consistencia requerida es:

```text
cada capa mantiene un vocabulario estable
```

No:

```text
todas las capas deben utilizar exactamente la misma palabra
```

---

# 13. Endpoints HTTP de evaluación de Retrieval

Agentes implementa:

```http
POST /api/v1/evaluate/retrieval
```

y:

```http
POST /api/v1/evaluate/retrieval/batch
```

El endpoint batch admite hasta:

```text
100 casos
```

---

# 14. Política HTTP acordada

No se solicitará inicialmente un modo:

```text
always HTTP 200
```

Data/IA deberá implementar el cliente de forma que diferencie:

```text
HTTP transport status
```

de:

```text
retrieval contract status
```

---

# 15. Respuestas HTTP individuales

El cliente deberá soportar conceptualmente:

```text
200
422
500
```

y, cuando exista body contractual, intentar procesarlo antes de descartar la respuesta únicamente como error HTTP.

---

# 16. Respuestas batch

Para batch:

```text
200
```

representa lote procesado sin fallos individuales.

```text
207
```

puede representar un lote mixto.

Data/IA deberá leer:

```text
results
```

también cuando la respuesta HTTP sea:

```text
207 Multi-Status
```

---

# 17. Regla de parsing HTTP

Comportamiento esperado del futuro cliente:

```text
HTTP 200
↓
parse body

HTTP 207
↓
parse body

HTTP 4xx / 5xx
↓
si existe body contractual:
    intentar parsearlo
si no existe o es inválido:
    tratar como error de transporte/integración
```

---

# 18. No colapsar HTTP y dominio

No convertir automáticamente:

```text
HTTP 500
```

en:

```text
retrieval status = error
```

si el body no contiene un payload contractual válido.

Son dos niveles diferentes:

```text
transporte
dominio
```

---

# 19. `validate_retrieval_contract`

El validator actual de Data/IA utiliza Pydantic para validar el contrato Retrieval v2.0.

Actualmente las claves adicionales no provocan fallo porque el schema no utiliza:

```python
extra="forbid"
```

en el modelo raíz.

---

# 20. Decisión sobre claves adicionales

Data/IA tolerará extensiones aditivas del contrato siempre que no alteren los campos obligatorios existentes.

Ejemplo permitido:

```json
{
  "latency_ms": 127
}
```

---

# 21. `latency_ms`

Se aprueba conceptualmente agregar:

```text
latency_ms
```

como metadata de rendimiento.

No modifica:

```text
Recall@K
Precision@K
ranking
status
score_type
```

---

# 22. Ubicación recomendada de `latency_ms`

Preferir:

```text
nivel del resultado completo del caso
```

y no:

```text
cada chunk individual
```

porque representa el tiempo de ejecución de la operación de Retrieval.

---

# 23. Compatibilidad futura de extras

El nuevo contrato propuesto por Agentes puede utilizar:

```python
ConfigDict(extra="allow")
```

en responses que deben tolerar evolución futura.

Data/IA deberá mantener este principio cuando sea compatible con sus validaciones.

---

# 24. Corpus congelado del benchmark

El benchmark oficial Retrieval v2 utiliza un corpus congelado.

Archivo:

```text
Data_IA/data/evaluation/chunks_v1.csv
```

---

# 25. Ground Truth

La ejecución actual de Retrieval v2 utiliza:

```text
Data_IA/data/evaluation/ground_truth_v2.csv
```

con:

```text
50 casos
```

---

# 26. Chroma del benchmark

Directorio:

```text
.benchmark_chroma_v2
```

---

# 27. Collection

Nombre de colección:

```text
benchmark_retrieval_v2
```

---

# 28. Carga de chunks

El benchmark debe cargar directamente los chunks congelados.

No debe regenerarlos mediante:

```text
RecursiveCharacterTextSplitter
chunk_size
chunk_overlap
cleaner
chunker
```

durante la ejecución reproducible del benchmark.

---

# 29. Estabilidad de `chunk_id`

Mientras se utilice:

```text
chunks_v1.csv
```

los `chunk_id` del benchmark permanecen congelados.

Por tanto:

```text
cambiar chunk_size o overlap en producción
```

no debe cambiar automáticamente los IDs históricos del benchmark.

---

# 30. Cambios futuros de chunking

Si se modifica:

```text
chunk_size
chunk_overlap
chunking algorithm
normalización
```

y se desea evaluar el nuevo corpus, deberá crearse una nueva versión.

Ejemplo conceptual:

```text
chunks_v2.csv
```

junto con:

```text
benchmark_retrieval_v3
```

o equivalente.

---

# 31. Regla de reproducibilidad

Nunca sobrescribir:

```text
chunks_v1.csv
```

con chunks generados por una configuración nueva.

El benchmark histórico debe permanecer reproducible.

---

# 32. Bug detectado en `retrieve_for_evaluation`

Se identificó que:

```text
build_success_response
```

puede ejecutarse fuera del bloque de manejo de excepciones.

Si un resultado contiene datos inválidos como:

```text
document_id ausente
```

puede generarse una excepción en lugar de:

```text
status = "error"
```

---

# 33. Caso adicional

Un:

```text
case_id vacío
```

también puede provocar una excepción fuera del flujo contractual esperado.

---

# 34. Decisión sobre el bug

La corrección debe realizarse en:

```text
core
```

y no depender exclusivamente de la mitigación implementada en el endpoint HTTP.

---

# 35. Razón

El principio debe ser:

```text
retrieve_for_evaluation
```

cumple su contrato independientemente del transport adapter que lo invoque.

---

# 36. Mitigación HTTP

La protección adicional en el endpoint puede mantenerse como defensa.

Sin embargo:

```text
endpoint mitigation
```

no sustituye:

```text
core fix
```

---

# 37. Contratos Pydantic estrictos vs Gemini schemas

Se establece una distinción explícita.

## Schemas que viajan a Gemini

Deben mantenerse compatibles con las limitaciones de structured output del proveedor.

## Schemas de entrada/respuesta HTTP

Pueden ser estrictos.

Ejemplo:

```python
ConfigDict(extra="forbid")
```

puede utilizarse en requests donde un typo deba provocar:

```text
422
```

---

# 38. Impacto sobre Data/IA Semantic Evaluator

Los schemas de Data/IA:

```text
SemanticScores
SemanticObservation
SemanticRecommendation
UnsupportedClaim
SemanticEvaluationResult
```

son inicialmente schemas internos.

No son todavía el `response_schema` utilizado para generación pedagógica.

Por lo tanto, sus validaciones Pydantic no deben confundirse con las limitaciones de los schemas enviados por Agentes a Gemini.

---

# 39. Si Data/IA utiliza Gemini

Cuando Data/IA implemente su propio Semantic Evaluator mediante Gemini, deberá evaluar por separado qué schema se entrega como:

```text
structured output schema
```

al proveedor.

No se debe asumir automáticamente que todo el modelo interno Pydantic puede enviarse sin adaptación.

---

# 40. Recomendación de arquitectura para Semantic Evaluator

Mantener tres niveles:

```text
Provider Output Schema
        ↓
Pydantic validation
        ↓
SemanticEvaluationResult
```

Esto permite adaptar el schema compatible con el proveedor sin debilitar el contrato interno.

---

# 41. Retrieval y Semantic Evaluator

Retrieval produce:

```text
evidencia
```

Semantic Evaluator consume:

```text
evidencia
+
contenido generado
+
contexto pedagógico
```

---

# 42. No duplicar Retrieval

El Semantic Evaluator no debe volver a ejecutar Retrieval automáticamente durante la evaluación inicial.

Debe utilizar:

```text
chunks_used
```

entregados por el flujo actual.

---

# 43. Score de retrieval vs semantic score

No confundir:

```text
chunk.score
```

con:

```text
semantic_scores.content_support
```

El primero representa ranking del chunk.

El segundo representa evaluación de respaldo factual del contenido generado.

---

# 44. Ejemplo

Un chunk puede tener:

```text
cross_encoder score alto
```

pero el contenido generado puede incluir una afirmación no respaldada.

Por tanto:

```text
high retrieval score
!=
high content_support score
```

---

# 45. Responsabilidades finales

## Agentes

Responsable de:

```text
Retrieval
generación
corrección
schemas de contenido generativo
```

## Data/IA

Responsable de:

```text
benchmark Retrieval
métricas
evaluación heurística
evaluación semántica
diagnóstico
recomendaciones
```

## BackendAPI

Responsable de:

```text
orquestación
persistencia
ciclo de corrección
historial
```

---

# 46. Decisiones confirmadas

Se consideran aceptadas para continuar implementación:

```text
1. No usar always-200 por defecto.
2. Data/IA deberá leer cuerpos contractuales en 200, 207 y cuando existan en 4xx/5xx.
3. Retrieval Contract puede recibir campos extra aditivos.
4. latency_ms es compatible como metadata.
5. Benchmark Retrieval v2 usa corpus congelado chunks_v1.csv.
6. Collection: benchmark_retrieval_v2.
7. Chroma path: .benchmark_chroma_v2.
8. Cambios futuros de chunking requieren nuevo corpus/versionado.
9. Retrieval conserva status error.
10. Generation conserva status failed.
11. El bug de retrieve_for_evaluation debe corregirse en core.
12. Los schemas semánticos de Data/IA permanecen separados de generated_schemas.py.
```

---

# 47. Elementos aún pendientes

Quedan pendientes:

```text
implementación del cliente HTTP de Retrieval
persistencia o uso de latency_ms
fix en core de retrieve_for_evaluation
merge definitivo de schemas de Agentes
contrato público del Semantic Evaluator
proveedor semántico
fallback del Semantic Evaluator
Decision Layer heurístico + semántico
```

---

# 48. Impacto en los documentos Data/IA existentes

Estas decisiones complementan:

```text
evaluation_contract_v2.md
evaluation_contract_v2_compatibility.md
semantic_rubric_v0_1.md
semantic_schema_v0_1.md
```

En caso de conflicto sobre integración Retrieval/Agentes, este documento representa la decisión transversal más reciente hasta que exista un contrato aprobado por todos los equipos.

---

# 49. Próximo paso Data/IA

Una vez registradas estas decisiones se puede continuar con:

```text
semantic_evaluator.py
```

manteniendo:

```text
Semantic Evaluation
```

desacoplada de:

```text
Retrieval HTTP transport
```

y de:

```text
generated_schemas.py
```

de Agentes.

---

# 50. Estado

```text
Draft acordado para implementación inicial
```

Las decisiones podrán actualizarse si BackendAPI o Agentes identifican una incompatibilidad durante integración.