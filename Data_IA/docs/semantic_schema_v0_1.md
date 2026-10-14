# NuevaMente — Semantic Schema v0.1

**Sprint:** 4  
**Estado:** Draft  
**Área responsable:** Data/IA  
**Objetivo:** Definir los schemas internos propuestos para representar la salida del evaluador semántico antes de implementar los modelos Pydantic definitivos.

---

# 1. Propósito

Este documento convierte la especificación definida en:

```text
semantic_rubric_v0_1.md
```

en una propuesta de estructuras concretas.

El objetivo es definir de forma previa y explícita los objetos que necesitará el evaluador semántico.

La implementación posterior deberá poder representar:

```text
semantic_scores
semantic_status
semantic_observations
recommendations
unsupported_information
metadata de ejecución
```

sin romper el contrato actual de `/evaluate`.

---

# 2. Principio de compatibilidad

Los schemas definidos aquí son inicialmente:

```text
internos
```

Eso significa que pueden implementarse primero dentro de Data/IA sin exponer inmediatamente todos sus campos en la respuesta pública.

La estrategia recomendada es:

```text
internal schema
↓
semantic evaluator
↓
tests
↓
calibration
↓
public contract
```

---

# 3. Objetos principales

La propuesta inicial incluye:

```text
SemanticScores
SemanticObservation
SemanticRecommendation
UnsupportedClaim
SemanticEvaluationResult
```

También se considera:

```text
SemanticStatus
SemanticDimension
SemanticSeverity
```

como tipos controlados.

---

# 4. SemanticDimension

Representa una dimensión válida de evaluación.

Propuesta:

```python
Literal[
    "relevance",
    "coherence",
    "didactic_adaptation",
    "content_support",
]
```

---

# 5. Razón de usar valores controlados

Evitar resultados inconsistentes como:

```text
relevancia
relevance
relevancy
topic_relevance
```

dentro del mismo evaluador.

El Semantic Evaluator debe utilizar un vocabulario único internamente.

---

# 6. Posible decisión futura

El contrato público actual utiliza nombres en español.

Por lo tanto, deberá decidirse posteriormente si:

```text
interno = inglés
externo = español
```

o si se adopta una sola convención.

Para v0.1 se propone utilizar internamente:

```text
relevance
coherence
didactic_adaptation
content_support
```

---

# 7. SemanticSeverity

Valores permitidos:

```python
Literal[
    "low",
    "medium",
    "high",
]
```

---

# 8. SemanticStatus

Valores propuestos:

```python
Literal[
    "success",
    "failed",
    "unavailable",
]
```

---

# 9. Significado de `success`

El evaluador semántico:

- fue ejecutado;
- produjo una respuesta;
- la respuesta pasó validación;
- los scores están disponibles.

---

# 10. Significado de `failed`

Se intentó ejecutar el evaluador, pero ocurrió un error.

Ejemplos:

```text
timeout
structured output inválido
error del proveedor
respuesta incompleta
```

---

# 11. Significado de `unavailable`

El evaluador no pudo ejecutarse porque no está disponible.

Ejemplos:

```text
feature desactivada
modelo no configurado
credenciales inexistentes
proveedor no disponible desde configuración
```

---

# 12. SemanticScores

Representa las cuatro dimensiones evaluadas semánticamente.

Propuesta conceptual:

```python
class SemanticScores(BaseModel):
    relevance: float
    coherence: float
    didactic_adaptation: float
    content_support: float
```

---

# 13. Restricciones de SemanticScores

Cada score debe estar limitado a:

```text
1.0 <= score <= 5.0
```

---

# 14. Precisión recomendada

La implementación puede redondear a:

```text
1 decimal
```

Ejemplos válidos:

```text
4.5
3.2
2.8
5.0
```

---

# 15. Ejemplo JSON de SemanticScores

```json
{
  "relevance": 4.6,
  "coherence": 4.3,
  "didactic_adaptation": 3.1,
  "content_support": 4.0
}
```

---

# 16. SemanticObservation

Representa un hallazgo detectado por el evaluador.

Propuesta:

```python
class SemanticObservation(BaseModel):
    dimension: SemanticDimension
    severity: SemanticSeverity
    message: str
```

---

# 17. Requisitos de `message`

Debe:

- describir un problema concreto;
- ser comprensible;
- evitar lenguaje genérico;
- estar relacionado con la dimensión indicada.

---

# 18. Ejemplo válido

```json
{
  "dimension": "didactic_adaptation",
  "severity": "high",
  "message": "El contenido utiliza conceptos avanzados sin explicación previa para el perfil junior solicitado."
}
```

---

# 19. Ejemplo inválido

```json
{
  "dimension": "didactic_adaptation",
  "severity": "high",
  "message": "El contenido puede mejorar."
}
```

---

# 20. SemanticRecommendation

Representa una acción correctiva sugerida.

Propuesta:

```python
class SemanticRecommendation(BaseModel):
    dimension: SemanticDimension
    message: str
```

---

# 21. Requisitos de Recommendation

Debe ser:

- concreta;
- accionable;
- relacionada con un hallazgo;
- utilizable por el Agente Revisor.

---

# 22. Ejemplo

```json
{
  "dimension": "didactic_adaptation",
  "message": "Explicar primero qué es un contenedor antes de introducir el concepto de orquestación."
}
```

---

# 23. UnsupportedClaim

Representa una afirmación factual detectada como no suficientemente respaldada.

Propuesta:

```python
class UnsupportedClaim(BaseModel):
    claim: str
    reason: str
```

---

# 24. Ejemplo de UnsupportedClaim

```json
{
  "claim": "Docker reemplaza completamente a Kubernetes.",
  "reason": "Los chunks proporcionados describen funciones diferentes y no respaldan esta afirmación."
}
```

---

# 25. Posible extensión futura

Podría añadirse:

```python
related_chunk_ids: list[str]
```

Ejemplo:

```json
{
  "claim": "La afirmación...",
  "reason": "No está respaldada...",
  "related_chunk_ids": [
    "chunk_001",
    "chunk_002"
  ]
}
```

---

# 26. Razón para no hacerlo obligatorio en v0.1

Asignar evidencia precisa por claim puede:

- aumentar complejidad;
- aumentar tokens;
- generar falsos vínculos;
- requerir validación adicional.

Por ello se considera opcional.

---

# 27. SemanticEvaluationResult

Representa la salida completa del Semantic Evaluator.

Propuesta conceptual:

```python
class SemanticEvaluationResult(BaseModel):
    status: SemanticStatus
    scores: SemanticScores | None
    observations: list[SemanticObservation]
    recommendations: list[SemanticRecommendation]
    unsupported_information: list[UnsupportedClaim]
```

---

# 28. Ejemplo completo exitoso

```json
{
  "status": "success",
  "scores": {
    "relevance": 4.5,
    "coherence": 4.2,
    "didactic_adaptation": 3.0,
    "content_support": 4.1
  },
  "observations": [
    {
      "dimension": "didactic_adaptation",
      "severity": "medium",
      "message": "El contenido introduce terminología avanzada sin suficiente explicación."
    }
  ],
  "recommendations": [
    {
      "dimension": "didactic_adaptation",
      "message": "Definir los conceptos técnicos antes de utilizarlos."
    }
  ],
  "unsupported_information": []
}
```

---

# 29. Ejemplo de fallo

```json
{
  "status": "failed",
  "scores": null,
  "observations": [],
  "recommendations": [],
  "unsupported_information": []
}
```

---

# 30. Ejemplo de unavailable

```json
{
  "status": "unavailable",
  "scores": null,
  "observations": [],
  "recommendations": [],
  "unsupported_information": []
}
```

---

# 31. Campo opcional `error_message`

Se recomienda evaluar agregar internamente:

```python
error_message: str | None
```

---

# 32. Propósito de `error_message`

Permitir diagnóstico técnico cuando:

```text
status != success
```

---

# 33. Ejemplo

```json
{
  "status": "failed",
  "scores": null,
  "observations": [],
  "recommendations": [],
  "unsupported_information": [],
  "error_message": "Semantic provider timeout after 10 seconds."
}
```

---

# 34. Exposición pública de `error_message`

No necesariamente debe exponerse completo a Frontend.

Puede utilizarse para:

- logs;
- Backend;
- debugging;
- observabilidad.

---

# 35. Campo opcional `model`

Puede considerarse:

```python
model: str | None
```

Ejemplo:

```json
{
  "model": "gemini-..."
}
```

---

# 36. Utilidad de `model`

Permite:

- trazabilidad;
- auditoría;
- comparar ejecuciones;
- reproducibilidad parcial.

---

# 37. Campo opcional `prompt_version`

Propuesta:

```python
prompt_version: str | None
```

---

# 38. Razón

El comportamiento del evaluador puede cambiar aunque:

```text
modelo
```

permanezca igual.

Cambios en:

```text
prompt
rubric
structured output
```

pueden alterar resultados.

---

# 39. Campo opcional `latency_ms`

Propuesta:

```python
latency_ms: int | None
```

---

# 40. Uso de `latency_ms`

Útil para Sprint 4 porque el ciclo:

```text
generación
evaluación
corrección
reevaluación
```

puede incrementar considerablemente el tiempo total.

---

# 41. Campo opcional `confidence`

No se recomienda como obligatorio.

Podría considerarse:

```python
confidence: float | None
```

---

# 42. Advertencia sobre confidence

No debe interpretarse automáticamente como:

```text
probabilidad estadística
```

---

# 43. Recomendación v0.1

No incluir `confidence` en el contrato mínimo.

---

# 44. SemanticEvaluationResult extendido

Una versión interna más completa podría ser:

```python
class SemanticEvaluationResult(BaseModel):
    status: SemanticStatus
    scores: SemanticScores | None = None
    observations: list[SemanticObservation] = []
    recommendations: list[SemanticRecommendation] = []
    unsupported_information: list[UnsupportedClaim] = []
    error_message: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
```

---

# 45. Nota importante sobre listas default

En Pydantic deben evitarse defaults mutables directos si la versión/configuración lo requiere.

Preferir conceptualmente:

```python
Field(default_factory=list)
```

---

# 46. Propuesta Pydantic más segura

```python
from typing import Literal

from pydantic import BaseModel, Field


SemanticDimension = Literal[
    "relevance",
    "coherence",
    "didactic_adaptation",
    "content_support",
]

SemanticSeverity = Literal[
    "low",
    "medium",
    "high",
]

SemanticStatus = Literal[
    "success",
    "failed",
    "unavailable",
]


class SemanticScores(BaseModel):
    relevance: float = Field(ge=1.0, le=5.0)
    coherence: float = Field(ge=1.0, le=5.0)
    didactic_adaptation: float = Field(ge=1.0, le=5.0)
    content_support: float = Field(ge=1.0, le=5.0)


class SemanticObservation(BaseModel):
    dimension: SemanticDimension
    severity: SemanticSeverity
    message: str = Field(min_length=1)


class SemanticRecommendation(BaseModel):
    dimension: SemanticDimension
    message: str = Field(min_length=1)


class UnsupportedClaim(BaseModel):
    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    related_chunk_ids: list[str] = Field(default_factory=list)


class SemanticEvaluationResult(BaseModel):
    status: SemanticStatus
    scores: SemanticScores | None = None
    observations: list[SemanticObservation] = Field(default_factory=list)
    recommendations: list[SemanticRecommendation] = Field(default_factory=list)
    unsupported_information: list[UnsupportedClaim] = Field(
        default_factory=list
    )
    error_message: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
```

---

# 47. Estado de esta propuesta

El código anterior es:

```text
propuesta de schema
```

No debe copiarse todavía directamente a producción sin revisar compatibilidad y nombres.

---

# 48. Naming interno vs público

Internamente se propone:

```text
relevance
coherence
didactic_adaptation
content_support
```

Pero el contrato actual utiliza:

```text
relevancia
coherencia
adaptacion_didactica
informacion_respaldada
```

---

# 49. Estrategia recomendada

No modificar `EvaluationScores` actual.

Crear un nuevo:

```text
SemanticScores
```

independiente.

---

# 50. Ventaja

Permite:

```text
heuristic scores
```

y:

```text
semantic scores
```

con estructuras claramente separadas.

---

# 51. No reutilizar EvaluationScores directamente

Aunque ambas tengan cuatro dimensiones, no se recomienda inicialmente reutilizar:

```python
EvaluationScores
```

para el Semantic Evaluator.

---

# 52. Razón

El actual:

```text
EvaluationScores
```

tiene:

- nombres legacy;
- enteros;
- semántica del heurístico;
- integración pública existente.

El semántico:

- puede usar float;
- tiene naming distinto;
- requiere evolución independiente.

---

# 53. Capa de mapping

Posteriormente puede existir una función que traduzca:

```text
SemanticScores
```

a dimensiones canónicas del contrato público.

---

# 54. Ejemplo de mapping

Conceptualmente:

```python
{
    "relevancia": semantic_scores.relevance,
    "coherencia": semantic_scores.coherence,
    "adaptacion_didactica": semantic_scores.didactic_adaptation,
    "informacion_respaldada": semantic_scores.content_support,
}
```

---

# 55. No aplicar mapping todavía para decisión final

El mapping solo alinea nombres.

No significa que:

```text
semantic score
```

sustituya:

```text
heuristic score
```

---

# 56. Schema de input del Semantic Evaluator

Se puede considerar un objeto interno:

```python
class SemanticEvaluationInput(BaseModel):
    format: str
    generated_content: ...
    generation_context: GenerationContext
    chunks_used: list[ChunkUsed]
```

---

# 57. Ventaja de un input interno

Evita que `semantic_evaluator.py` dependa directamente de:

```text
FastAPI request
```

---

# 58. Separación recomendada

```text
API schema
↓
internal semantic input
↓
semantic evaluator
```

---

# 59. SemanticEvaluationInput propuesto

Conceptualmente:

```python
class SemanticEvaluationInput(BaseModel):
    format: Literal[
        "quiz",
        "flashcards",
        "tldr",
        "video_script",
    ]

    generated_content: GeneratedContent
    generation_context: GenerationContext
    chunks_used: list[ChunkUsed]
```

---

# 60. GeneratedContent

Debe soportar:

```text
QuizContent
FlashcardsContent
TLDRContent
VideoScriptContent
```

---

# 61. Reutilización de schemas actuales

Para:

```text
generated_content
generation_context
chunks_used
```

sí se recomienda reutilizar los schemas ya existentes.

---

# 62. Razón

No crear nuevas versiones innecesarias de:

```text
QuizContent
FlashcardsContent
TLDRContent
VideoScriptContent
GenerationContext
ChunkUsed
```

---

# 63. Regla de SSOT

El contenido generado debe seguir teniendo una sola fuente de verdad dentro de Data/IA.

---

# 64. SemanticObservation y ubicación del problema

Puede considerarse en el futuro añadir:

```python
location: str | None
```

---

# 65. Ejemplo de location

```json
{
  "dimension": "coherence",
  "severity": "medium",
  "message": "La explicación contradice la respuesta seleccionada.",
  "location": "questions[2].explanation"
}
```

---

# 66. Beneficio

Ayudaría al Agente Revisor a localizar el problema.

---

# 67. Riesgo

El modelo puede inventar rutas inválidas.

---

# 68. Recomendación v0.1

No hacerlo obligatorio.

---

# 69. Alternativa

Podría usarse:

```python
item_id: str | None
```

---

# 70. Ejemplo

Para Quiz:

```json
{
  "item_id": "q3"
}
```

Para Flashcards:

```json
{
  "item_id": "card_2"
}
```

Para Video:

```json
{
  "item_id": "scene_4"
}
```

---

# 71. Ventaja de `item_id`

Es más estable que una ruta arbitraria.

---

# 72. Propuesta futura de Observation extendida

```python
class SemanticObservation(BaseModel):
    dimension: SemanticDimension
    severity: SemanticSeverity
    message: str
    item_id: str | None = None
```

---

# 73. Recomendación v0.1

Se puede incluir `item_id` como opcional desde el inicio si el equipo considera que el Revisor lo aprovechará.

---

# 74. Recommendation con `item_id`

También podría extenderse:

```python
class SemanticRecommendation(BaseModel):
    dimension: SemanticDimension
    message: str
    item_id: str | None = None
```

---

# 75. Relación Observation–Recommendation

Podría añadirse un identificador:

```text
observation_id
```

pero no es necesario inicialmente.

---

# 76. Razón para mantenerlo simple

El objetivo del Sprint 4 es demostrar:

```text
evaluar
diagnosticar
corregir
reevaluar
```

No construir un sistema complejo de issues.

---

# 77. UnsupportedClaim y item_id

También podría ser útil:

```python
item_id: str | None
```

---

# 78. Ejemplo

```json
{
  "claim": "Docker reemplaza a Kubernetes.",
  "reason": "No está respaldado por los chunks.",
  "item_id": "q2"
}
```

---

# 79. Propuesta de schema v0.1 mínimo

Para reducir alcance, el mínimo sería:

```text
SemanticScores
SemanticObservation
SemanticRecommendation
UnsupportedClaim
SemanticEvaluationResult
```

---

# 80. Propuesta de schema v0.1 extendido recomendado

Se recomienda:

```text
SemanticScores
SemanticObservation + item_id opcional
SemanticRecommendation + item_id opcional
UnsupportedClaim + item_id opcional + related_chunk_ids
SemanticEvaluationResult + metadata técnica
```

---

# 81. Código propuesto extendido

```python
from typing import Literal

from pydantic import BaseModel, Field


SemanticDimension = Literal[
    "relevance",
    "coherence",
    "didactic_adaptation",
    "content_support",
]

SemanticSeverity = Literal[
    "low",
    "medium",
    "high",
]

SemanticStatus = Literal[
    "success",
    "failed",
    "unavailable",
]


class SemanticScores(BaseModel):
    relevance: float = Field(ge=1.0, le=5.0)
    coherence: float = Field(ge=1.0, le=5.0)
    didactic_adaptation: float = Field(ge=1.0, le=5.0)
    content_support: float = Field(ge=1.0, le=5.0)


class SemanticObservation(BaseModel):
    dimension: SemanticDimension
    severity: SemanticSeverity
    message: str = Field(min_length=1)
    item_id: str | None = None


class SemanticRecommendation(BaseModel):
    dimension: SemanticDimension
    message: str = Field(min_length=1)
    item_id: str | None = None


class UnsupportedClaim(BaseModel):
    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    item_id: str | None = None
    related_chunk_ids: list[str] = Field(default_factory=list)


class SemanticEvaluationResult(BaseModel):
    status: SemanticStatus

    scores: SemanticScores | None = None

    observations: list[SemanticObservation] = Field(
        default_factory=list
    )

    recommendations: list[SemanticRecommendation] = Field(
        default_factory=list
    )

    unsupported_information: list[UnsupportedClaim] = Field(
        default_factory=list
    )

    error_message: str | None = None

    model: str | None = None

    prompt_version: str | None = None

    latency_ms: int | None = Field(
        default=None,
        ge=0,
    )
```

---

# 82. Validación cruzada del resultado

Se recomienda añadir validaciones de coherencia entre campos.

---

# 83. Regla `success`

Si:

```text
status = success
```

entonces:

```text
scores != null
```

debería ser obligatorio.

---

# 84. Regla `failed`

Si:

```text
status = failed
```

entonces:

```text
scores = null
```

debería ser lo normal.

---

# 85. Regla `unavailable`

Si:

```text
status = unavailable
```

entonces:

```text
scores = null
```

---

# 86. Validación conceptual

Ejemplo inválido:

```json
{
  "status": "success",
  "scores": null
}
```

---

# 87. Ejemplo inválido

```json
{
  "status": "failed",
  "scores": {
    "relevance": 5,
    "coherence": 5,
    "didactic_adaptation": 5,
    "content_support": 5
  }
}
```

---

# 88. Implementación posible de validación

Pydantic v2 permite utilizar:

```text
model_validator
```

para estas reglas.

---

# 89. No implementar validadores excesivos inicialmente

Mantener solamente invariantes claras.

---

# 90. Validación de observaciones

Cada observation debe tener:

```text
message no vacío
dimension válida
severity válida
```

---

# 91. Validación de recomendaciones

Cada recommendation debe tener:

```text
message no vacío
dimension válida
```

---

# 92. Validación de claims

Cada unsupported claim debe tener:

```text
claim no vacío
reason no vacío
```

---

# 93. Duplicados

Puede considerarse eliminar duplicados antes de devolver respuesta.

---

# 94. Estrategia simple

Deduplicar por:

```text
message
```

o:

```text
claim
```

cuando existan duplicados exactos.

---

# 95. No deduplicar semánticamente en v0.1

No introducir complejidad innecesaria.

---

# 96. Cantidad máxima de observations

La rúbrica recomienda:

```text
0–5 principales
```

---

# 97. Cantidad máxima de recommendations

También:

```text
0–5 principales
```

---

# 98. Restricción de schema

No se recomienda imponer todavía:

```python
max_length=5
```

porque puede dificultar pruebas y casos especiales.

La limitación puede aplicarse a nivel prompt/orquestación.

---

# 99. Unsupported claims

Puede haber más de cinco claims.

No imponer un límite rígido sin evidencia.

---

# 100. Orden recomendado de observations

Ordenar conceptualmente por:

```text
high
medium
low
```

---

# 101. Orden de recommendations

Puede conservar el mismo orden que los problemas asociados.

---

# 102. Orden de unsupported claims

Preferiblemente en el orden en que aparecen en el contenido.

---

# 103. Semantic result y contract público

No se recomienda exponer directamente:

```text
SemanticEvaluationResult
```

como response completo de `/evaluate`.

---

# 104. Razón

La respuesta pública necesita combinar:

```text
legacy heuristic result
+
semantic result
```

---

# 105. Posible HybridEvaluationResult

En el futuro podría existir:

```python
class HybridEvaluationResult(BaseModel):
    heuristic_scores: EvaluationScores
    semantic_evaluation: SemanticEvaluationResult
    status: ...
```

---

# 106. No definir todavía el híbrido final

La estrategia de decisión depende de calibración.

---

# 107. Primera integración recomendada

`reviewer.py` podría recibir ambos resultados:

```text
heuristic_result
semantic_result
```

sin combinarlos numéricamente.

---

# 108. Ejemplo conceptual

```text
heuristic:
    scores
    informacion_no_respaldada

semantic:
    scores
    observations
    recommendations
    unsupported_information
```

---

# 109. Decision Layer futura

Después de calibración:

```text
heuristic result
+
semantic result
↓
decision layer
↓
final status
```

---

# 110. Naming de archivos recomendado

Propuesta:

```text
Data_IA/data_ai/schemas/semantic_evaluation.py
```

---

# 111. Por qué archivo separado

Evita sobrecargar:

```text
format_evaluation.py
```

con responsabilidades del evaluador semántico.

---

# 112. Estructura propuesta

```text
Data_IA/
└── data_ai/
    ├── schemas/
    │   ├── evaluation.py
    │   ├── format_evaluation.py
    │   ├── retrieval.py
    │   └── semantic_evaluation.py
```

---

# 113. Importaciones

`semantic_evaluator.py` debería importar:

```text
SemanticEvaluationResult
SemanticScores
SemanticObservation
SemanticRecommendation
UnsupportedClaim
```

desde:

```text
data_ai.schemas.semantic_evaluation
```

---

# 114. No declarar schemas dentro del evaluator

Evitar:

```text
semantic_evaluator.py
```

conteniendo clases Pydantic mezcladas con lógica.

---

# 115. Separación de responsabilidades

```text
schemas/
→ estructura

evaluation/
→ lógica

api/
→ transporte
```

---

# 116. Pruebas de schemas

Crear posteriormente:

```text
test_semantic_evaluation_schemas.py
```

---

# 117. Tests mínimos de SemanticScores

Validar:

```text
1.0 válido
5.0 válido
0.9 inválido
5.1 inválido
```

---

# 118. Tests de Observation

Validar:

```text
dimension válida
severity válida
message obligatorio
```

---

# 119. Tests de Recommendation

Validar:

```text
dimension válida
message obligatorio
```

---

# 120. Tests de UnsupportedClaim

Validar:

```text
claim obligatorio
reason obligatorio
related_chunk_ids opcional
```

---

# 121. Tests de Result

Validar:

```text
success + scores
failed + scores null
unavailable + scores null
```

---

# 122. Ejemplo de test conceptual

```python
def test_semantic_result_success_requires_scores():
    ...
```

---

# 123. Compatibilidad Pydantic

El proyecto utiliza:

```text
Pydantic >= 2.9
```

por lo que la implementación debe usar APIs de Pydantic v2.

---

# 124. No introducir dependencias nuevas para schemas

Los schemas deben depender únicamente de Pydantic y typing.

---

# 125. Serialización

Los resultados deben poder convertirse mediante:

```python
model_dump()
```

---

# 126. JSON

También deben ser serializables por FastAPI sin lógica especial.

---

# 127. Strings en español

Aunque los nombres internos estén en inglés, los mensajes pueden producirse en español.

---

# 128. Razón

La documentación y experiencia principal del proyecto están en español.

---

# 129. Ejemplo

```json
{
  "dimension": "coherence",
  "severity": "high",
  "message": "La explicación contradice la respuesta correcta."
}
```

---

# 130. Message language

Para Sprint 4 se recomienda:

```text
Spanish
```

para:

```text
observations
recommendations
reason
```

---

# 131. Claims

`claim` debe conservar el idioma original del contenido generado.

---

# 132. Normalización

No modificar sustancialmente el claim.

Debe permitir reconocer qué afirmación fue detectada.

---

# 133. No inventar quotations

Si el modelo devuelve un claim textual, debe corresponder realmente al contenido.

---

# 134. Alternativa futura

En lugar de texto completo podría usarse:

```text
claim_summary
```

pero no es necesario para v0.1.

---

# 135. Error schema interno

Se puede considerar un tipo específico:

```python
SemanticError
```

pero sería innecesario inicialmente.

---

# 136. Mantener error simple

Usar:

```text
error_message
```

es suficiente para v0.1.

---

# 137. Error code

Podría añadirse:

```python
error_code: str | None
```

---

# 138. Ejemplos de error code

```text
timeout
provider_error
invalid_output
not_configured
```

---

# 139. ¿Agregarlo en v0.1?

Recomendado si facilita tests y fallback.

---

# 140. SemanticErrorCode

Podría definirse:

```python
SemanticErrorCode = Literal[
    "timeout",
    "provider_error",
    "invalid_output",
    "not_configured",
]
```

---

# 141. Resultado extendido con error code

```python
class SemanticEvaluationResult(BaseModel):
    status: SemanticStatus
    scores: SemanticScores | None = None
    observations: list[SemanticObservation] = Field(default_factory=list)
    recommendations: list[SemanticRecommendation] = Field(default_factory=list)
    unsupported_information: list[UnsupportedClaim] = Field(default_factory=list)

    error_code: SemanticErrorCode | None = None
    error_message: str | None = None

    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
```

---

# 142. Beneficio de error_code

Backend y tests pueden distinguir:

```text
timeout
```

de:

```text
invalid_output
```

sin interpretar texto.

---

# 143. Exposición pública

No necesariamente debe exponerse desde el primer día.

Puede ser interno.

---

# 144. Schema recomendado definitivo para v0.1

Se propone como base de implementación:

```python
from typing import Literal

from pydantic import BaseModel, Field


SemanticDimension = Literal[
    "relevance",
    "coherence",
    "didactic_adaptation",
    "content_support",
]

SemanticSeverity = Literal[
    "low",
    "medium",
    "high",
]

SemanticStatus = Literal[
    "success",
    "failed",
    "unavailable",
]

SemanticErrorCode = Literal[
    "timeout",
    "provider_error",
    "invalid_output",
    "not_configured",
]


class SemanticScores(BaseModel):
    relevance: float = Field(ge=1.0, le=5.0)
    coherence: float = Field(ge=1.0, le=5.0)
    didactic_adaptation: float = Field(ge=1.0, le=5.0)
    content_support: float = Field(ge=1.0, le=5.0)


class SemanticObservation(BaseModel):
    dimension: SemanticDimension
    severity: SemanticSeverity
    message: str = Field(min_length=1)
    item_id: str | None = None


class SemanticRecommendation(BaseModel):
    dimension: SemanticDimension
    message: str = Field(min_length=1)
    item_id: str | None = None


class UnsupportedClaim(BaseModel):
    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    item_id: str | None = None
    related_chunk_ids: list[str] = Field(default_factory=list)


class SemanticEvaluationResult(BaseModel):
    status: SemanticStatus

    scores: SemanticScores | None = None

    observations: list[SemanticObservation] = Field(
        default_factory=list
    )

    recommendations: list[SemanticRecommendation] = Field(
        default_factory=list
    )

    unsupported_information: list[UnsupportedClaim] = Field(
        default_factory=list
    )

    error_code: SemanticErrorCode | None = None
    error_message: str | None = None

    model: str | None = None
    prompt_version: str | None = None

    latency_ms: int | None = Field(
        default=None,
        ge=0,
    )
```

---

# 145. Campos mínimos obligatorios en success

Cuando:

```text
status = success
```

deben existir:

```text
scores
```

---

# 146. Campos opcionales en success

Pueden estar vacíos:

```text
observations
recommendations
unsupported_information
```

si no existen problemas.

---

# 147. Campos esperados en failed

Cuando:

```text
status = failed
```

esperar:

```text
scores = null
error_code != null
```

idealmente.

---

# 148. Campos esperados en unavailable

Cuando:

```text
status = unavailable
```

esperar:

```text
scores = null
error_code = not_configured
```

o causa equivalente.

---

# 149. Invariantes propuestas

```text
success → scores required
failed → scores null
unavailable → scores null
```

---

# 150. No asociar status semántico al status pedagógico

`SemanticStatus` representa:

```text
estado técnico del evaluador
```

No representa:

```text
approved / requires_revision / rejected
```

---

# 151. Distinción fundamental

Ejemplo:

```text
semantic_status = success
```

y al mismo tiempo:

```text
evaluation_status = requiere_revision
```

es totalmente válido.

---

# 152. Razón

Uno describe:

```text
si el evaluador funcionó
```

El otro:

```text
qué tan bueno es el contenido
```

---

# 153. No incluir verdict dentro de SemanticEvaluationResult v0.1

El Semantic Evaluator debería producir:

```text
scores
hallazgos
recommendaciones
```

pero no necesariamente decidir el status final del sistema.

---

# 154. Razón

El verdict final puede depender de:

```text
heurístico
semántico
guardrails
```

---

# 155. Posible semantic recommendation severity

No es necesario.

La severidad pertenece principalmente al hallazgo.

---

# 156. Relación por item_id

Observation:

```text
item_id = q2
```

Recommendation:

```text
item_id = q2
```

permite relacionarlas de manera sencilla.

---

# 157. No exigir item_id

Algunos problemas son globales.

Ejemplo:

```text
todo el contenido está demasiado avanzado
```

---

# 158. item_id nulo válido

```json
{
  "dimension": "didactic_adaptation",
  "severity": "high",
  "message": "El nivel general del contenido es demasiado avanzado.",
  "item_id": null
}
```

---

# 159. Casos por formato

Quiz:

```text
item_id = question_id
```

Flashcards:

```text
item_id = card_id
```

Video:

```text
item_id = scene_id
```

TLDR:

Puede ser:

```text
summary
key_point_1
conclusion
```

o null.

---

# 160. No imponer esquema TLDR de item_id inicialmente

Mantener flexibilidad.

---

# 161. Related chunk IDs

Para unsupported claim:

```text
related_chunk_ids
```

puede estar vacío.

---

# 162. Significado de lista vacía

```text
no se identificó evidencia suficientemente relacionada
```

No significa:

```text
no existen chunks
```

---

# 163. Modelo semántico y reproducibilidad

Guardar:

```text
model
prompt_version
```

ayuda a interpretar resultados históricos.

---

# 164. Latency

Debe medirse en:

```text
milliseconds
```

---

# 165. Prompt version inicial

Propuesta futura:

```text
semantic-evaluator-v0.1
```

---

# 166. No hardcodear en múltiples archivos

La versión debería centralizarse posteriormente.

---

# 167. Ubicación futura de configuración

Podría estar en:

```text
evaluation/config.py
```

o módulo específico.

---

# 168. No definir configuración aquí

Este documento solo define schema.

---

# 169. Ejemplo completo aprobado semánticamente

```json
{
  "status": "success",
  "scores": {
    "relevance": 5.0,
    "coherence": 4.8,
    "didactic_adaptation": 4.6,
    "content_support": 4.9
  },
  "observations": [],
  "recommendations": [],
  "unsupported_information": [],
  "error_code": null,
  "error_message": null,
  "model": "semantic-model",
  "prompt_version": "semantic-evaluator-v0.1",
  "latency_ms": 824
}
```

---

# 170. Ejemplo con problemas

```json
{
  "status": "success",
  "scores": {
    "relevance": 4.5,
    "coherence": 4.0,
    "didactic_adaptation": 2.4,
    "content_support": 3.0
  },
  "observations": [
    {
      "dimension": "didactic_adaptation",
      "severity": "high",
      "message": "El contenido utiliza terminología avanzada sin explicación previa.",
      "item_id": null
    },
    {
      "dimension": "content_support",
      "severity": "medium",
      "message": "Una afirmación técnica no está suficientemente respaldada.",
      "item_id": "q2"
    }
  ],
  "recommendations": [
    {
      "dimension": "didactic_adaptation",
      "message": "Definir los conceptos avanzados antes de utilizarlos.",
      "item_id": null
    },
    {
      "dimension": "content_support",
      "message": "Eliminar o reformular la afirmación no respaldada.",
      "item_id": "q2"
    }
  ],
  "unsupported_information": [
    {
      "claim": "Docker reemplaza completamente a Kubernetes.",
      "reason": "Los chunks no respaldan una relación de reemplazo entre ambas tecnologías.",
      "item_id": "q2",
      "related_chunk_ids": [
        "chunk_001",
        "chunk_002"
      ]
    }
  ],
  "error_code": null,
  "error_message": null,
  "model": "semantic-model",
  "prompt_version": "semantic-evaluator-v0.1",
  "latency_ms": 1092
}
```

---

# 171. Ejemplo timeout

```json
{
  "status": "failed",
  "scores": null,
  "observations": [],
  "recommendations": [],
  "unsupported_information": [],
  "error_code": "timeout",
  "error_message": "Semantic evaluation exceeded configured timeout.",
  "model": "semantic-model",
  "prompt_version": "semantic-evaluator-v0.1",
  "latency_ms": 10000
}
```

---

# 172. Ejemplo not configured

```json
{
  "status": "unavailable",
  "scores": null,
  "observations": [],
  "recommendations": [],
  "unsupported_information": [],
  "error_code": "not_configured",
  "error_message": "Semantic evaluator is not configured.",
  "model": null,
  "prompt_version": "semantic-evaluator-v0.1",
  "latency_ms": 0
}
```

---

# 173. Backward compatibility

Ninguno de estos objetos debe reemplazar automáticamente:

```text
EvaluationResponse
```

actual.

---

# 174. Primera integración recomendada

El endpoint puede continuar devolviendo legacy mientras el semántico se valida internamente.

---

# 175. Segunda integración

Una vez aprobado el contrato con Backend, añadir campos nuevos opcionales.

---

# 176. Posible response público futuro

Conceptualmente:

```json
{
  "document_id": "...",
  "format": "...",
  "status": "requiere_revision",

  "scores": {},

  "informacion_no_respaldada": false,

  "observaciones": [],

  "heuristic_scores": {},

  "semantic_evaluation": {
    "status": "success",
    "scores": {},
    "observations": [],
    "recommendations": [],
    "unsupported_information": []
  }
}
```

---

# 177. Alternativa flat

Otra posibilidad:

```text
semantic_status
semantic_scores
semantic_observations
recommendations
unsupported_information
```

---

# 178. Nested vs flat

Debe decidirse con Backend.

---

# 179. Ventaja nested

```text
semantic_evaluation
```

agrupa claramente los datos del evaluador semántico.

---

# 180. Ventaja flat

Puede simplificar algunos consumidores.

---

# 181. Recomendación conceptual

Preferir nested internamente.

---

# 182. Razón

Evita mezclar:

```text
status pedagógico
```

con:

```text
semantic_status técnico
```

---

# 183. Ejemplo nested

```json
{
  "semantic_evaluation": {
    "status": "success",
    "scores": {
      "relevance": 4.4,
      "coherence": 4.1,
      "didactic_adaptation": 3.2,
      "content_support": 4.0
    },
    "observations": [],
    "recommendations": [],
    "unsupported_information": []
  }
}
```

---

# 184. Decisión pendiente con Backend

Definir si el contrato público utilizará:

```text
nested
```

o:

```text
flat
```

---

# 185. Recomendación para implementación de Luis

Luis puede implementar inicialmente los schemas internos sin esperar esa decisión.

---

# 186. Trabajo que no depende del Backend

Puede avanzar con:

```text
SemanticScores
SemanticObservation
SemanticRecommendation
UnsupportedClaim
SemanticEvaluationResult
schema tests
```

---

# 187. Trabajo que sí depende del Backend

Esperar acuerdo antes de modificar:

```text
EvaluationResponse
HTTP response
persistence
```

---

# 188. Definition of Done del schema v0.1

Se considera listo para implementar cuando:

- `SemanticDimension` esté definido;
- `SemanticSeverity` esté definido;
- `SemanticStatus` esté definido;
- `SemanticScores` tenga límites 1–5;
- Observation esté estructurada;
- Recommendation esté estructurada;
- UnsupportedClaim esté estructurado;
- SemanticEvaluationResult soporte success/failure/unavailable;
- exista metadata básica de error;
- estén definidas las invariantes;
- exista estrategia de tests.

---

# 189. Decisiones pendientes

Todavía deben acordarse:

1. naming interno español vs inglés;
2. incluir o no `item_id` desde v0.1;
3. incluir `related_chunk_ids`;
4. incluir `error_code`;
5. incluir metadata de modelo;
6. nested vs flat en contrato público;
7. exponer o no `latency_ms`;
8. migración futura de `scores`;
9. schema público definitivo.

---

# 190. Propuesta de decisión inicial

Para implementación interna v0.1:

```text
usar inglés internamente
usar item_id opcional
usar related_chunk_ids opcional
usar error_code
usar model
usar prompt_version
usar latency_ms
mantener response público sin cambios inicialmente
```

---

# 191. Archivo de implementación futuro

Crear posteriormente:

```text
Data_IA/data_ai/schemas/semantic_evaluation.py
```

---

# 192. Archivo de tests futuro

Crear:

```text
Data_IA/data_ai/tests/test_semantic_evaluation_schemas.py
```

---

# 193. Próximo paso

Después de aprobar este documento, crear el primer archivo de código:

```text
Data_IA/data_ai/schemas/semantic_evaluation.py
```

junto con sus tests.

Todavía no será necesario implementar:

```text
semantic_evaluator.py
```

hasta validar que los schemas funcionan correctamente.

---

# 194. Orden recomendado

```text
semantic_schema_v0_1.md
↓
semantic_evaluation.py
↓
schema tests
↓
semantic_evaluator.py
↓
semantic evaluator tests
↓
calibration dataset
↓
hybrid integration
```

---

# 195. Resumen final

El Semantic Schema v0.1 debe permitir representar de manera inequívoca:

```text
qué puntuó el evaluador
qué problema encontró
qué recomienda cambiar
qué afirmación no está respaldada
si el evaluador funcionó
qué modelo/prompt produjo el resultado
```

sin mezclar todavía estas responsabilidades con la decisión final del ciclo.

---

# 196. Regla principal

El Semantic Evaluator produce:

```text
evidence-aware assessment
```

La capa de decisión produce:

```text
final evaluation status
```

Estas dos responsabilidades deben permanecer separadas.

---

# 197. Estado del documento

```text
Draft
```

Debe revisarse antes de implementar el schema público definitivo.

---

# 198. Próximo entregable técnico

Implementar:

```text
Data_IA/data_ai/schemas/semantic_evaluation.py
```

y:

```text
Data_IA/data_ai/tests/test_semantic_evaluation_schemas.py
```

como primera implementación de código de Sprint 4 para Data/IA.