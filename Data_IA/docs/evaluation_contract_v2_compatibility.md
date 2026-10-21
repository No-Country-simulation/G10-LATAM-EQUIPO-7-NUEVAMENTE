# NuevaMente — Evaluation Contract V2 Compatibility Review

**Sprint:** 4  
**Estado:** Draft  
**Área responsable:** Data/IA  
**Integración principal:** BackendAPI ↔ Data/IA  
**Base revisada:** rama `QA`  
**Objetivo:** Comparar el contrato actual de evaluación entre BackendAPI y Data/IA con la propuesta `Evaluation Contract V2` antes de modificar schemas, endpoints o persistencia.

---

# 1. Propósito

Este documento analiza la compatibilidad entre:

1. el contrato de evaluación implementado actualmente al cierre de Sprint 3;
2. la evolución propuesta para Sprint 4.

El objetivo es evitar cambios incompatibles mientras se incorporan:

- evaluación semántica;
- métricas semánticas;
- observaciones más específicas;
- recomendaciones accionables;
- detección detallada de información no respaldada;
- soporte para el ciclo automático de corrección.

La estrategia recomendada es evolucionar el contrato de forma progresiva y mantener compatibilidad con BackendAPI siempre que sea posible.

---

# 2. Resultado general

La revisión del código actual indica que el request:

```text
BackendAPI → Data/IA
```

ya contiene prácticamente toda la información necesaria para ejecutar tanto:

```text
evaluación heurística
```

como:

```text
evaluación semántica
```

Por este motivo, **no se recomienda modificar inicialmente el request de `/evaluate`**.

La principal evolución de Sprint 4 debe concentrarse en:

```text
Data/IA → BackendAPI
```

es decir, en la respuesta de evaluación.

---

# 3. Flujo actual

El flujo actual puede representarse de forma simplificada como:

```text
Agentes
   ↓
contenido generado + sources_used
   ↓
BackendAPI
   ↓
POST /evaluate
   ↓
Data/IA
   ↓
evaluador heurístico
   ↓
scores + status + observaciones
   ↓
BackendAPI
```

Sprint 4 extenderá este flujo hacia:

```text
Agentes
   ↓
BackendAPI
   ↓
Data/IA
   ↓
Heuristic Evaluator
        +
Semantic Evaluator
   ↓
métricas + hallazgos + recomendaciones
   ↓
BackendAPI
   ↓
Agente Revisor
   ↓
contenido corregido
   ↓
BackendAPI
   ↓
Data/IA
```

---

# 4. Endpoint actual

El servicio Data/IA expone actualmente:

```http
POST /evaluate
```

El endpoint utiliza:

```python
EvaluationRequest
```

como schema de entrada y:

```python
EvaluationResponse
```

como schema de salida.

---

# 5. Request actual BackendAPI → Data/IA

El contrato actual contiene los siguientes elementos principales:

```text
document_id
format
generated_content
generation_context
chunks_used
```

Estos campos ya proporcionan la información necesaria para ejecutar la evaluación propuesta para Sprint 4.

---

# 6. Matriz de compatibilidad del request

| Campo | Contrato actual | V2 propuesto | Compatibilidad | Acción |
|---|---|---|---|---|
| `document_id` | Sí | Sí | Compatible | Conservar |
| `format` | Sí | Sí | Compatible | Conservar |
| `generated_content` | Sí | Sí | Compatible | Conservar |
| `generation_context` | Sí | Sí | Compatible | Conservar |
| `chunks_used` | Sí | Sí | Compatible | Conservar |
| `format_id` | No requerido por Data/IA | No obligatorio | Compatible | Mantener en Backend |
| `attempt` | No | Opcional | No necesario inicialmente | No agregar |
| `cycle_id` | No | No requerido | Compatible | Responsabilidad Backend |
| `retry_count` | No | No requerido | Compatible | Responsabilidad Backend |

---

# 7. Conclusión sobre el request

Se recomienda mantener inicialmente sin cambios:

```json
{
  "document_id": "...",
  "format": "...",
  "generated_content": {},
  "generation_context": {},
  "chunks_used": []
}
```

Esto permite implementar el evaluador semántico sin romper:

- BackendAPI;
- tests existentes;
- persistencia;
- integración actual;
- Swagger;
- validaciones Pydantic.

---

# 8. `document_id`

## Estado actual

Existe en el request.

Ejemplo:

```json
{
  "document_id": "doc_123"
}
```

## Evaluación de compatibilidad

```text
100 % compatible
```

## Acción

Conservar sin cambios.

---

# 9. `format`

## Estado actual

Existe y determina el schema de `generated_content`.

Formatos soportados:

```text
quiz
flashcards
tldr
video_script
```

## Evaluación de compatibilidad

```text
compatible
```

## Acción

Conservar.

No se recomienda introducir:

```text
format_type
```

como reemplazo mientras Backend utilice `format`.

---

# 10. `generated_content`

## Estado actual

Existe.

Su estructura depende de:

```text
format
```

## Compatibilidad

El evaluador semántico necesita analizar exactamente el mismo contenido que ya recibe el heurístico.

Por lo tanto:

```text
no requiere modificación
```

---

# 11. `generation_context`

## Estado actual

Incluye conceptualmente:

```text
profile
niche
detail_level
learning_objective
```

## Compatibilidad

Es suficiente para evaluar:

- relevancia;
- adaptación didáctica;
- nivel técnico;
- complejidad;
- correspondencia con el objetivo pedagógico.

## Acción

Conservar.

---

# 12. Regla sobre `generation_context`

Debe mantenerse la regla establecida en Sprint 3:

```text
generation_context
```

puede utilizarse para evaluar:

```text
relevancia
adaptación
nivel
```

pero no puede utilizarse como:

```text
evidencia factual
```

---

# 13. `chunks_used`

## Estado actual

Existe y contiene la evidencia recuperada mediante RAG.

Ejemplo conceptual:

```json
[
  {
    "chunk_id": "chunk_001",
    "document_id": "doc_123",
    "rank": 1,
    "score": 0.91,
    "text": "..."
  }
]
```

## Compatibilidad

Es el campo fundamental para implementar evaluación semántica de respaldo.

## Acción

Conservar.

---

# 14. Regla factual

La regla deberá mantenerse:

```text
chunks_used = única evidencia factual
```

No utilizar como evidencia:

```text
learning_objective
profile
niche
detail_level
conocimiento del LLM
prompt
```

---

# 15. Campos que NO se recomienda añadir todavía al request

Aunque aparecen conceptualmente en los diagramas de Sprint 4, inicialmente no se recomienda incorporar:

```text
format_id
attempt
cycle_id
retry_count
previous_evaluation
```

porque Data/IA no necesita esa información para determinar la calidad del contenido.

---

# 16. `format_id`

BackendAPI utiliza internamente identificadores de generación.

Sin embargo:

```text
format_id
```

no es actualmente obligatorio para Data/IA.

## Recomendación

No agregarlo al request hasta que Backend determine que existe una necesidad real de trazabilidad entre servicios.

---

# 17. `attempt`

El número de intento pertenece conceptualmente al ciclo controlado por Backend.

Ejemplo:

```text
attempt 0 = generación inicial
attempt 1 = corrección
```

Data/IA puede evaluar ambos contenidos independientemente.

## Recomendación

No agregar `attempt` inicialmente.

Podría incorporarse posteriormente como metadata de auditoría.

---

# 18. `cycle_id`

Sprint 4 requiere agrupar evaluaciones de un mismo ciclo.

Sin embargo, esa agrupación pertenece a:

```text
BackendAPI
```

y no al evaluador.

## Recomendación

No imponer `cycle_id` como dependencia de Data/IA.

---

# 19. Response actual Data/IA → BackendAPI

El contrato actual contiene conceptualmente:

```text
document_id
format
status
scores
informacion_no_respaldada
observaciones
evaluator_version
rubric_version
```

---

# 20. Matriz de compatibilidad del response

| Campo actual | Campo V2 propuesto | Estado | Acción recomendada |
|---|---|---|---|
| `document_id` | `document_id` | Compatible | Conservar |
| `format` | `format` | Compatible | Conservar |
| `status` | `verdict` o `status` | Pendiente | No cambiar todavía |
| `scores` | `heuristic_scores` / `final_scores` | Cambio | Mantener temporalmente |
| — | `heuristic_scores` | Nuevo | Añadir |
| — | `semantic_scores` | Nuevo | Añadir |
| `informacion_no_respaldada` | `unsupported_information` | Evolución | Mantener + extender |
| `observaciones` | `observations` estructuradas | Evolución | Mantener compatibilidad |
| — | `semantic_observations` | Nuevo posible | Evaluar |
| — | `recommendations` | Nuevo | Añadir |
| — | `semantic_status` | Nuevo | Añadir |
| `evaluator_version` | `evaluator_version` | Compatible | Conservar |
| `rubric_version` | `rubric_version` | Compatible | Conservar |

---

# 21. Estrategia general de compatibilidad

No se recomienda reemplazar directamente:

```text
status
scores
informacion_no_respaldada
observaciones
```

por los nuevos campos.

Durante la transición, la respuesta puede conservar los campos actuales y añadir los nuevos.

Conceptualmente:

```text
campos legacy
+
campos V2
```

---

# 22. Estado actual

Actualmente la rúbrica utiliza:

```text
aprobado
requiere_revision
rechazado
```

---

# 23. Propuesta conceptual V2

Los diagramas y documentación de Sprint 4 utilizan conceptos equivalentes a:

```text
approved
requires_revision
rejected
```

---

# 24. Riesgo de cambiar los estados

Cambiar unilateralmente:

```text
aprobado
```

por:

```text
approved
```

puede romper:

- tests Backend;
- persistencia;
- lógica condicional;
- schemas;
- Frontend;
- datos históricos.

---

# 25. Recomendación para `status`

Mantener inicialmente:

```text
status
```

con los valores actuales:

```text
aprobado
requiere_revision
rechazado
```

hasta que BackendAPI confirme una migración coordinada.

---

# 26. `verdict`

El nuevo contrato conceptual puede hablar de:

```text
verdict
```

como concepto arquitectónico.

Pero eso no significa que el campo técnico deba llamarse inmediatamente:

```json
{
  "verdict": "approved"
}
```

## Recomendación

Conservar inicialmente:

```json
{
  "status": "requiere_revision"
}
```

y decidir posteriormente si una versión mayor del contrato migra a `verdict`.

---

# 27. `scores` actual

Actualmente la respuesta contiene:

```json
{
  "scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  }
}
```

Actualmente esos scores provienen del evaluador heurístico.

---

# 28. Problema semántico de `scores`

Al introducir un segundo evaluador aparece la pregunta:

```text
¿Qué representa scores?
```

Podría representar:

1. solo heurístico;
2. solo semántico;
3. combinación;
4. scores finales calibrados.

Sprint 4 todavía no tiene suficiente evidencia para decidir esto.

---

# 29. Propuesta de transición de scores

Durante la primera implementación se propone conservar:

```json
{
  "scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  }
}
```

y añadir:

```json
{
  "heuristic_scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  },

  "semantic_scores": {
    "relevancia": 4.5,
    "coherencia": 4.7,
    "adaptacion_didactica": 3.1,
    "informacion_respaldada": 4.2
  }
}
```

---

# 30. Interpretación temporal de `scores`

Durante la fase de compatibilidad:

```text
scores = heuristic_scores
```

puede mantenerse explícitamente para no cambiar el comportamiento existente.

Esto debe documentarse claramente.

No debe confundirse con:

```text
final_scores
```

---

# 31. `heuristic_scores`

Campo nuevo propuesto:

```json
{
  "heuristic_scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  }
}
```

## Propósito

Hacer explícito qué parte de la evaluación proviene del motor determinístico V1.1.

---

# 32. `semantic_scores`

Campo nuevo propuesto:

```json
{
  "semantic_scores": {
    "relevancia": 4.5,
    "coherencia": 4.7,
    "adaptacion_didactica": 3.1,
    "informacion_respaldada": 4.2
  }
}
```

## Propósito

Representar exclusivamente el resultado del evaluador semántico.

---

# 33. No combinar scores todavía

No asumir:

```text
final = 50 % heuristic + 50 % semantic
```

Tampoco asumir otros pesos como:

```text
40/60
30/70
```

sin calibración.

---

# 34. `final_scores`

No se recomienda añadir inmediatamente un resultado final calculado.

La existencia de:

```text
final_scores
```

deberá depender de los resultados del dataset de calibración.

---

# 35. Evaluación por dimensión

Ambos evaluadores deberían representar conceptualmente las mismas dimensiones:

```text
relevancia
coherencia
adaptacion_didactica
informacion_respaldada
```

Esto permitirá comparar:

```text
humano
vs
heurístico
vs
semántico
```

---

# 36. Posible migración de nombres de dimensiones

Los diagramas conceptuales utilizan nombres como:

```text
relevance
coherence
didactic_adaptation
content_support
```

mientras el contrato actual utiliza:

```text
relevancia
coherencia
adaptacion_didactica
informacion_respaldada
```

## Recomendación

No cambiar los nombres técnicos durante la primera implementación.

Conservar los actuales hasta acordar un contrato canónico entre equipos.

---

# 37. `informacion_no_respaldada`

## Estado actual

Es un booleano.

Ejemplo:

```json
{
  "informacion_no_respaldada": true
}
```

---

# 38. Ventaja del campo actual

Permite aplicar fácilmente reglas determinísticas como:

```text
informacion_no_respaldada = true
→
rechazado
```

---

# 39. Limitación

No responde:

```text
¿Qué información concreta no está respaldada?
```

---

# 40. Propuesta compatible

Conservar:

```json
{
  "informacion_no_respaldada": true
}
```

y añadir:

```json
{
  "unsupported_information": [
    {
      "claim": "Docker reemplaza completamente a Kubernetes.",
      "reason": "No existe evidencia suficiente en los chunks proporcionados."
    }
  ]
}
```

---

# 41. Beneficio

Backend puede seguir usando el booleano para reglas existentes.

El Agente Revisor puede utilizar:

```text
unsupported_information
```

para aplicar una corrección específica.

---

# 42. `unsupported_information`

Schema conceptual:

```json
{
  "claim": "Afirmación detectada",
  "reason": "Motivo por el cual no está respaldada"
}
```

---

# 43. Posible extensión de `unsupported_information`

En una iteración posterior podría incluir:

```json
{
  "claim": "...",
  "reason": "...",
  "related_chunk_ids": []
}
```

No se considera obligatorio para la primera versión.

---

# 44. Observaciones actuales

Actualmente:

```python
observaciones: List[str]
```

Ejemplo:

```text
"Requiere revisión: Existen criterios con puntaje regular (3) que deben mejorarse."
```

---

# 45. Limitación de observaciones actuales

Las observaciones actuales sirven para explicar el veredicto general.

Pero no identifican necesariamente:

- dimensión;
- severidad;
- ubicación conceptual del problema;
- causa;
- acción correctiva.

---

# 46. Observaciones V2

Propuesta:

```json
{
  "dimension": "adaptacion_didactica",
  "severity": "high",
  "message": "El contenido utiliza terminología superior al nivel junior solicitado."
}
```

---

# 47. Problema de compatibilidad de `observaciones`

Cambiar:

```python
List[str]
```

directamente a:

```python
List[Observation]
```

rompería el contrato actual.

---

# 48. Estrategia recomendada para observaciones

Durante transición se pueden conservar:

```text
observaciones
```

como `List[str]`.

Y añadir, por ejemplo:

```text
semantic_observations
```

como estructura avanzada.

Ejemplo:

```json
{
  "observaciones": [
    "Requiere revisión: La adaptación didáctica debe mejorar."
  ],

  "semantic_observations": [
    {
      "dimension": "adaptacion_didactica",
      "severity": "high",
      "message": "El contenido utiliza conceptos avanzados sin explicación previa."
    }
  ]
}
```

---

# 49. Alternativa futura

En una versión mayor del contrato podría unificarse todo bajo:

```text
observations
```

estructurado.

Eso no debe hacerse antes de coordinar Backend y persistencia.

---

# 50. Recommendations

Actualmente no existe un campo específico de recomendaciones.

Sprint 4 necesita incorporar:

```text
recommendations
```

porque el Agente Revisor necesita instrucciones accionables.

---

# 51. Schema conceptual de recomendación

```json
{
  "dimension": "adaptacion_didactica",
  "message": "Definir primero los conceptos básicos antes de introducir términos avanzados."
}
```

---

# 52. Recomendaciones y compatibilidad

Al ser un campo nuevo y aditivo:

```text
recommendations
```

puede añadirse sin eliminar campos existentes.

Esto reduce el riesgo de breaking changes.

---

# 53. Reglas para recomendaciones

Las recomendaciones deben ser:

- concretas;
- accionables;
- relacionadas con una observación;
- limitadas a la evidencia disponible;
- útiles para un agente generativo.

---

# 54. Ejemplo negativo

No utilizar:

```text
"Mejorar la respuesta."
```

---

# 55. Ejemplo adecuado

Preferir:

```text
"Explicar primero qué es un contenedor antes de introducir el concepto de orquestación."
```

---

# 56. `semantic_status`

Campo nuevo recomendado.

Su propósito es distinguir:

```text
evaluador semántico ejecutado correctamente
```

de:

```text
evaluador semántico no disponible
```

---

# 57. Propuesta inicial de `semantic_status`

Valores:

```text
success
unavailable
failed
```

---

# 58. `success`

Significa:

```text
la evaluación semántica fue ejecutada y validada
```

---

# 59. `unavailable`

Podría representar casos como:

```text
modelo no configurado
proveedor no disponible
feature desactivada
```

---

# 60. `failed`

Representa una ejecución intentada que terminó en error.

Ejemplos:

```text
timeout
respuesta inválida
error de proveedor
JSON inválido
```

---

# 61. Regla fundamental del fallback

Nunca hacer:

```text
semantic_scores = heuristic_scores
```

cuando el evaluador semántico falla.

Eso crearía resultados semánticos falsos.

---

# 62. Ejemplo de fallback correcto

```json
{
  "scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  },

  "heuristic_scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  },

  "semantic_scores": null,

  "semantic_status": "failed"
}
```

---

# 63. Estado final cuando falla el semántico

Todavía debe definirse con Backend.

Opciones posibles:

1. devolver evaluación heurística como respuesta parcial;
2. marcar evaluación como degradada;
3. pedir revisión manual;
4. tratar el fallo semántico como error técnico.

No debe decidirse unilateralmente.

---

# 64. Versiones actuales

El código actual utiliza:

```text
EVALUATOR_VERSION = 1.1.0
RUBRIC_VERSION = 1.0.0
```

---

# 65. Versionado V2

No se debe cambiar todavía automáticamente a:

```text
2.0.0
```

hasta conocer la estrategia de compatibilidad final.

---

# 66. Posible versionado compatible

Si se añaden campos opcionales sin romper el contrato:

```text
1.2.0
```

podría representar mejor una evolución compatible.

---

# 67. Posible versión mayor

Si se reemplazan:

```text
status
scores
observaciones
```

por estructuras incompatibles, tendría más sentido:

```text
2.0.0
```

---

# 68. Evaluador heurístico actual

El motor actual está implementado principalmente en:

```text
Data_IA/data_ai/evaluation/quality_evaluator.py
```

---

# 69. Función actual

Conceptualmente:

```text
generated_content
+
chunks_used
+
generation_context
↓
evaluate()
↓
EvaluationScores
+
informacion_no_respaldada
```

---

# 70. Estado actual de evaluación semántica

`quality_evaluator.py` contiene placeholders para modelos semánticos.

Existen variables como:

```python
_gemini_client = None
_embedding_model = None
```

y una función:

```python
get_semantic_models()
```

---

# 71. Limitación del placeholder

Actualmente no existe una evaluación semántica funcional.

Por ello:

```text
Semantic Evaluator Sprint 4
```

debe considerarse una implementación nueva.

---

# 72. Riesgo del placeholder actual

Existe lógica conceptual equivalente a:

```python
if modelo_embeddings is not None:
    informacion_respaldada = 5
```

Esto no debe convertirse en la implementación semántica real.

La simple presencia de un modelo no demuestra respaldo factual.

---

# 73. Recomendación técnica

No activar el placeholder.

Crear un módulo separado:

```text
semantic_evaluator.py
```

---

# 74. Arquitectura recomendada

```text
                 /evaluate
                     │
                     ▼
              EvaluationRequest
                     │
       ┌─────────────┴─────────────┐
       │                           │
       ▼                           ▼
quality_evaluator.py      semantic_evaluator.py
       │                           │
       ▼                           ▼
heuristic_scores          semantic_scores
                                  │
                                  ├── observations
                                  ├── recommendations
                                  └── unsupported_information
       │                           │
       └─────────────┬─────────────┘
                     ▼
               Decision Layer
                     │
                     ▼
                Response
```

---

# 75. `hybrid_evaluator.py`

Puede considerarse crear:

```text
hybrid_evaluator.py
```

como capa de orquestación.

Su responsabilidad sería:

- llamar heurístico;
- llamar semántico;
- manejar fallback;
- preparar resultados conjuntos;
- invocar capa de decisión.

---

# 76. Reviewer interno actual

Actualmente:

```text
reviewer.py
```

orquesta:

```text
quality_evaluator
↓
rubric
↓
EvaluacionReviewerContract
```

---

# 77. Evolución conceptual del reviewer

Sprint 4 debería evolucionar hacia:

```text
heuristic evaluator
        +
semantic evaluator
        ↓
evaluation orchestration
        ↓
decision layer
        ↓
structured response
```

---

# 78. Confusión potencial con el término `reviewer`

Existe:

```text
Data_IA/data_ai/evaluation/reviewer.py
```

pero Sprint 4 también introduce un:

```text
Agente Revisor
```

dentro de Agentes.

Son responsabilidades distintas.

---

# 79. Reviewer de Data/IA

El `reviewer.py` de Data/IA:

```text
orquesta evaluación
```

---

# 80. Agente Revisor de Agentes

El Revisor del sistema multiagente:

```text
corrige contenido
```

---

# 81. Regla de responsabilidades

```text
Data/IA → evalúa
Agente Revisor → corrige
BackendAPI → orquesta
```

---

# 82. Soporte de formatos

El sistema soporta actualmente:

```text
quiz
flashcards
tldr
video_script
```

---

# 83. Inconsistencia interna detectada

El schema público y `quality_evaluator.py` soportan los cuatro formatos.

Sin embargo, el tipo declarado en `reviewer.py` todavía refleja:

```python
GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
]
```

---

# 84. Acción requerida

Actualizar ese tipo para incluir:

```python
GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
    TLDRContent,
    VideoScriptContent,
]
```

---

# 85. Impacto

Este cambio debería considerarse:

```text
cleanup técnico
```

y no una modificación conceptual del contrato.

---

# 86. Docstrings desactualizados

También deberán actualizarse textos como:

```text
"Evalúa un Quiz o conjunto de Flashcards."
```

por una descripción que refleje los cuatro formatos.

---

# 87. Backend ya posee integración Data/IA

Backend cuenta con componentes como:

```text
backend/app/ports/data_ia_port.py
backend/app/application/format_evaluation_service.py
backend/app/infrastructure/integrations/http_data_ia_adapter.py
```

---

# 88. Consecuencia arquitectónica

No es necesario construir una integración Backend → Data/IA desde cero.

La tarea es:

```text
evolucionar el contrato existente
```

---

# 89. Persistencia actual

Backend ya persiste evaluaciones.

Cada evaluación puede asociarse a una generación mediante los mecanismos internos de Backend.

---

# 90. Nueva necesidad de Sprint 4

Backend deberá resolver cómo recuperar:

```text
evaluación inicial
+
evaluación posterior a corrección
```

como parte del mismo ciclo funcional.

---

# 91. Responsabilidad del ciclo

La asociación del ciclo pertenece a:

```text
BackendAPI
```

No debe implementarse dentro de Data/IA.

---

# 92. Historial

Data/IA produce:

```text
una evaluación independiente por request
```

Backend construye:

```text
historial del ciclo
```

---

# 93. Orden del historial

De acuerdo con la arquitectura propuesta:

```text
más reciente
↓
más antigua
```

---

# 94. Relación con Frontend

Frontend no consume directamente:

```text
Data/IA
```

Consume:

```text
BackendAPI
```

---

# 95. Tarea de Data/IA respecto a Frontend

Data/IA debe definir:

```text
qué información de evaluación tiene valor
```

pero no:

```text
cómo se renderiza
```

---

# 96. Datos potencialmente útiles para Frontend

Backend podría exponer:

```text
status
scores
semantic_scores
evolución de scores
observaciones relevantes
indicador de corrección
```

La selección final debe acordarse con Frontend.

---

# 97. Recommendations para Agentes

Las recomendaciones generadas por Data/IA viajarán:

```text
Data/IA
↓
BackendAPI
↓
Agente Revisor
```

No existe comunicación:

```text
Data/IA → Agentes
```

directa.

---

# 98. Información útil para el Agente Revisor

El Revisor necesita principalmente:

```text
qué está mal
por qué está mal
qué debe corregir
qué afirmación no tiene evidencia
qué dimensión se ve afectada
```

---

# 99. Los scores no son suficientes

Ejemplo poco útil:

```json
{
  "adaptacion_didactica": 2
}
```

Ejemplo útil:

```json
{
  "dimension": "adaptacion_didactica",
  "severity": "high",
  "message": "El contenido utiliza conceptos superiores al nivel junior solicitado.",
  "recommendation": "Explicar primero los conceptos básicos antes de introducir service discovery."
}
```

---

# 100. Evaluación de nivel

Sprint 4 tiene como objetivo verificar que el nivel generado realmente corresponda al solicitado.

---

# 101. Inputs para adaptación

El evaluador deberá usar:

```text
generated_content
profile
detail_level
```

---

# 102. Aspectos que debe analizar

- vocabulario;
- jerga técnica;
- profundidad;
- prerequisitos implícitos;
- densidad conceptual;
- explicación de conceptos;
- nivel de abstracción.

---

# 103. Ejemplo de problema

Contexto:

```text
profile = junior
detail_level = medium
```

Contenido:

```text
El service mesh utiliza sidecar proxies para gestionar observabilidad,
mTLS, service discovery y políticas de tráfico...
```

sin explicar previamente dichos conceptos.

Resultado esperado:

```text
adaptación insuficiente
```

---

# 104. Ejemplo de observación

```json
{
  "dimension": "adaptacion_didactica",
  "severity": "high",
  "message": "El contenido presupone conocimientos de service mesh, mTLS y service discovery superiores al perfil junior."
}
```

---

# 105. Ejemplo de recomendación

```json
{
  "dimension": "adaptacion_didactica",
  "message": "Introducir primero una explicación básica de comunicación entre servicios antes de utilizar conceptos de service mesh."
}
```

---

# 106. Evaluación de respaldo semántico

El evaluador semántico deberá comparar:

```text
claims del contenido generado
vs
chunks_used
```

---

# 107. Fuente de verdad

La evidencia factual sigue siendo exclusivamente:

```text
chunks_used
```

---

# 108. Guardrail de `informacion_respaldada`

El respaldo factual no debería compensarse mediante un promedio simple.

Ejemplo:

```text
relevancia = 5
coherencia = 5
adaptación = 5
respaldo = 1
```

no debería transformarse en:

```text
promedio = 4
→ aprobado
```

---

# 109. Regla de veto

Una baja puntuación de respaldo o una afirmación crítica no sustentada puede requerir:

```text
requires_revision
```

o:

```text
rejected
```

independientemente de otras dimensiones.

La regla exacta deberá calibrarse.

---

# 110. Dataset de calibración

Antes de definir una combinación definitiva se creará un dataset controlado.

---

# 111. Comparación prevista

```text
evaluación humana
vs
heurístico
vs
semántico
```

---

# 112. Tipos de casos necesarios

El dataset deberá incluir:

```text
contenido excelente
contenido irrelevante
contenido incoherente
contenido demasiado avanzado
contenido demasiado básico
contenido con alucinaciones
contenido parcialmente respaldado
contenido incompleto
contenido aparentemente correcto pero no sustentado
```

---

# 113. Formatos del dataset

Debe cubrir:

```text
quiz
flashcards
tldr
video_script
```

---

# 114. Calibración

La calibración permitirá responder:

```text
¿Dónde funciona bien el heurístico?
¿Dónde funciona mejor el semántico?
¿Dónde se equivocan ambos?
¿Qué dimensión necesita guardrails?
```

---

# 115. Decisión sobre pesos

No definir pesos antes de esa evaluación.

---

# 116. Posibles estrategias posteriores

Dependiendo de los resultados:

```text
scores separados
```

o:

```text
reglas por dimensión
```

o:

```text
ponderación calibrada
```

o:

```text
semantic score + guardrails heurísticos
```

---

# 117. Semantic Evaluator y proveedor

Actualmente Data/IA no tiene configurado un proveedor semántico activo.

---

# 118. Dependencias actuales

`Data_IA/requirements.txt` no contiene actualmente necesariamente un SDK para Gemini dentro del servicio Data/IA.

---

# 119. Si se utiliza Gemini

Será necesario añadir explícitamente:

```text
SDK
API key
model
timeout
configuración del contenedor
```

---

# 120. Variables de entorno

Ejemplo conceptual:

```text
GEMINI_API_KEY
GEMINI_MODEL
```

Los nombres finales deberán coordinarse con infraestructura.

---

# 121. Secrets

Nunca almacenar:

```text
API keys
tokens
credentials
```

en Git.

---

# 122. Docker

Actualmente el servicio:

```text
data-ia
```

deberá evolucionar si necesita acceso al proveedor semántico.

---

# 123. Configuración potencial

Podría requerirse:

```yaml
data-ia:
  env_file:
    - ...
```

o variables seguras equivalentes.

La implementación corresponde coordinarla con infraestructura.

---

# 124. CI

Los cambios deberán pasar:

```text
Data IA - Tests
```

---

# 125. Impacto de contrato

Como la respuesta es consumida por Backend, también deberá verificarse:

```text
Backend - Tests and lint
```

---

# 126. Tests generales del PR

Idealmente deberán quedar verdes:

```text
Backend - Tests and lint
Agents - Tests
Data IA - Tests
Frontend - Build
```

---

# 127. Tests del evaluador semántico

Casos mínimos:

```text
semantic success
semantic unavailable
semantic timeout
semantic malformed response
unsupported claim
wrong level
irrelevant content
incoherent content
fully supported content
```

---

# 128. Tests de compatibilidad

Debe existir al menos un test que compruebe que los campos actuales continúan presentes durante la transición:

```text
status
scores
informacion_no_respaldada
observaciones
```

---

# 129. Tests de campos nuevos

También verificar:

```text
heuristic_scores
semantic_scores
semantic_status
recommendations
unsupported_information
```

cuando corresponda.

---

# 130. Estrategia de migración propuesta

Se recomienda realizar Sprint 4 por fases.

---

# 131. Fase 1 — Contract compatibility

Mantener el request actual.

Mantener los campos legacy del response.

Crear schemas nuevos internamente.

---

# 132. Fase 2 — Semantic Evaluator

Implementar:

```text
semantic_evaluator.py
```

sin modificar todavía la lógica final de status.

---

# 133. Fase 3 — Exponer resultados semánticos

Añadir campos opcionales:

```text
heuristic_scores
semantic_scores
semantic_status
semantic_observations
recommendations
unsupported_information
```

---

# 134. Fase 4 — Dataset

Ejecutar calibración:

```text
human
vs
heuristic
vs
semantic
```

---

# 135. Fase 5 — Decision Layer

Definir cómo se obtiene:

```text
status / verdict
```

a partir de ambos evaluadores.

---

# 136. Fase 6 — Backend integration

Actualizar:

```text
DataIAPort
HTTP adapter
persistence
schemas
tests
```

según contrato aprobado.

---

# 137. Fase 7 — Correction cycle

Validar:

```text
generation
↓
evaluation
↓
correction
↓
reevaluation
```

---

# 138. Fase 8 — Frontend

Backend podrá exponer las métricas relevantes y el historial del último ciclo.

---

# 139. Campos seguros para implementar internamente

Data/IA puede comenzar a trabajar sin coordinación externa inmediata en:

```text
semantic evaluator
semantic schemas
dataset
calibration scripts
unit tests
semantic observations
recommendations
unsupported claim detection
```

si todavía no cambia el contrato público.

---

# 140. Cambios que requieren acuerdo Backend

No modificar unilateralmente:

```text
status
valores de status
scores
nombres de dimensiones
observaciones existentes
response obligatorio
request
```

---

# 141. Cambios que requieren coordinación con Agentes

Coordinar:

```text
estructura de recommendations
datos que necesita el Revisor
estructura de unsupported_information
contexto pedagógico necesario
```

---

# 142. Cambios que requieren coordinación con Frontend

Coordinar:

```text
qué scores mostrar
qué historial mostrar
qué observaciones exponer
cómo representar mejora entre evaluaciones
```

---

# 143. Contrato temporal recomendado

Durante la fase de transición, una respuesta podría verse conceptualmente así:

```json
{
  "document_id": "doc_123",
  "format": "quiz",

  "status": "requiere_revision",

  "scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  },

  "informacion_no_respaldada": false,

  "observaciones": [
    "Requiere revisión: La adaptación didáctica puede mejorarse."
  ],

  "heuristic_scores": {
    "relevancia": 4,
    "coherencia": 5,
    "adaptacion_didactica": 3,
    "informacion_respaldada": 4
  },

  "semantic_status": "success",

  "semantic_scores": {
    "relevancia": 4.6,
    "coherencia": 4.7,
    "adaptacion_didactica": 2.9,
    "informacion_respaldada": 4.3
  },

  "semantic_observations": [
    {
      "dimension": "adaptacion_didactica",
      "severity": "high",
      "message": "El contenido utiliza conceptos superiores al nivel junior solicitado."
    }
  ],

  "recommendations": [
    {
      "dimension": "adaptacion_didactica",
      "message": "Explicar los conceptos fundamentales antes de introducir terminología avanzada."
    }
  ],

  "unsupported_information": [],

  "evaluator_version": "1.1.0",
  "rubric_version": "1.0.0"
}
```

---

# 144. Nota sobre el ejemplo anterior

La respuesta anterior es una propuesta de compatibilidad.

No debe considerarse todavía el contrato final.

En particular, quedan pendientes:

```text
evaluator_version
rubric_version
semantic_observations
nombres de dimensiones
semantic_status
```

---

# 145. Posible simplificación posterior

Una vez que Backend migre completamente, una versión futura podría eliminar duplicación como:

```text
scores
heuristic_scores
```

si ya existe una estrategia definitiva.

---

# 146. No eliminar legacy durante calibración

Mientras se comparan evaluadores, conservar:

```text
heuristic_scores
semantic_scores
```

es especialmente útil para análisis.

---

# 147. Evaluator Version

La versión del evaluador debe identificar cambios funcionales importantes.

---

# 148. Rubric Version

La versión de rúbrica debe cambiar únicamente cuando cambian:

- dimensiones;
- umbrales;
- reglas de decisión;
- semántica de scores.

---

# 149. Separación version evaluator / rubric

No asumir que:

```text
Evaluator 2.0
```

implica automáticamente:

```text
Rubric 2.0
```

Puede cambiar implementación sin cambiar rúbrica.

---

# 150. Riesgo: duplicación de fuentes de verdad

Durante la transición existirán potencialmente:

```text
scores
heuristic_scores
semantic_scores
```

Debe documentarse claramente qué representa cada uno.

---

# 151. Regla temporal recomendada

Hasta calibración:

```text
scores = resultado legacy heurístico
heuristic_scores = resultado heurístico explícito
semantic_scores = resultado semántico independiente
```

---

# 152. Riesgo: Backend asume `scores` como resultado final

Por ello no se debe cambiar el significado de:

```text
scores
```

sin coordinación.

---

# 153. Riesgo: observations incompatibles

Backend puede estar persistiendo:

```text
List[str]
```

Cambiar a objetos estructurados podría requerir:

```text
migración de schema
serialización
tests
```

---

# 154. Recomendación para observations

Añadir inicialmente:

```text
semantic_observations
```

en lugar de reemplazar:

```text
observaciones
```

---

# 155. Riesgo: `rejected`

La arquitectura de Sprint 4 introduce corrección automática.

Debe definirse qué ocurre cuando Data/IA devuelve:

```text
rechazado
```

---

# 156. Pregunta pendiente

¿Un contenido rechazado:

```text
puede ser corregido
```

o:

```text
termina inmediatamente el ciclo
```

?

---

# 157. Recomendación conceptual

Separar:

```text
calidad del contenido
```

de:

```text
error técnico
```

---

# 158. Error técnico

Ejemplos:

```text
semantic timeout
provider unavailable
malformed response
```

No deberían transformarse en:

```text
rechazado
```

porque no representan calidad del contenido.

---

# 159. Estado de evaluación vs estado técnico

Puede resultar útil distinguir:

```text
evaluation status
```

de:

```text
semantic execution status
```

---

# 160. Ejemplo

```json
{
  "status": "requiere_revision",
  "semantic_status": "success"
}
```

---

# 161. Otro ejemplo

```json
{
  "status": "requiere_revision",
  "semantic_status": "failed"
}
```

si Backend acepta fallback heurístico.

La política debe acordarse.

---

# 162. Timeout

Debe existir un timeout claro para evitar que el ciclo completo quede bloqueado por el evaluador semántico.

---

# 163. Retry semántico

No confundir:

```text
retry del proveedor semántico
```

con:

```text
retry de corrección del contenido
```

Son conceptos diferentes.

---

# 164. Retry de proveedor

Responsabilidad interna técnica del servicio Data/IA.

---

# 165. Retry de contenido

Responsabilidad de BackendAPI.

---

# 166. Máximo de correcciones

Sprint 4 inicia con:

```text
1 corrección automática
```

---

# 167. Cantidad máxima de evaluaciones normales

Si la generación inicial requiere corrección:

```text
Evaluación 1
+
Evaluación 2
```

---

# 168. Data/IA no necesita saber el límite

El evaluador procesa cada request independientemente.

---

# 169. Auditoría

Podría resultar útil en el futuro persistir:

```text
semantic model
semantic evaluator version
latency
confidence
```

pero no es obligatorio para la primera versión.

---

# 170. `confidence`

Un campo:

```text
confidence
```

puede considerarse en evaluación semántica.

---

# 171. Riesgo de confidence

Un LLM puede producir confianza poco calibrada.

No debe utilizarse automáticamente como probabilidad estadística.

---

# 172. Recomendación

Si se incorpora:

```text
confidence
```

debe tratarse como señal auxiliar.

---

# 173. Structured Output

El Semantic Evaluator debería utilizar salida estructurada.

---

# 174. Beneficio

Permite validar:

```text
scores
observations
recommendations
unsupported_information
```

antes de construir la respuesta HTTP.

---

# 175. No confiar en texto libre sin validación

Una respuesta del proveedor no debe enviarse directamente a Backend.

Debe pasar por:

```text
Pydantic
```

o validación equivalente.

---

# 176. Error de structured output

Si la respuesta no cumple schema:

```text
semantic_status = failed
```

y debe aplicarse la política de fallback.

---

# 177. Dataset antes de pesos

La decisión sobre combinación debe ocurrir después del dataset.

---

# 178. Objetivo del dataset

No demostrar que el semántico siempre es mejor.

El objetivo es saber:

```text
cuándo aporta valor
```

y:

```text
cuándo puede equivocarse
```

---

# 179. Casos adversariales

Incluir casos diseñados para engañar a cada evaluador.

Ejemplo:

Contenido con muchas palabras del source, pero significado incorrecto.

Esto puede engañar al heurístico.

---

# 180. Otro caso adversarial

Contenido semánticamente plausible pero que introduce información externa no presente en chunks.

Puede engañar al modelo semántico si no se obliga a fundamentar contra evidencia.

---

# 181. Resultado deseado de calibración

Poder justificar técnicamente la decisión de arquitectura final.

---

# 182. Definition of Done — Compatibility Review

Este análisis podrá considerarse completo cuando:

- request actual haya sido validado con Backend;
- response V2 haya sido revisado con Backend;
- recomendaciones hayan sido revisadas con Agentes;
- datos visibles hayan sido revisados con Frontend;
- política de fallback esté acordada;
- vocabulario de status esté acordado;
- estrategia de versionado esté acordada;
- schemas Pydantic estén definidos;
- tests de contrato existan.

---

# 183. Decisiones pendientes

Las siguientes decisiones siguen abiertas:

1. mantener `status` o migrar a `verdict`;
2. mantener valores en español o migrar a inglés;
3. significado futuro de `scores`;
4. necesidad final de `heuristic_scores`;
5. schema exacto de `semantic_scores`;
6. schema exacto de `semantic_observations`;
7. nombre definitivo de observaciones semánticas;
8. schema exacto de `recommendations`;
9. schema exacto de `unsupported_information`;
10. comportamiento de `rechazado`;
11. comportamiento cuando falla el semántico;
12. timeout;
13. retry técnico;
14. proveedor;
15. modelo;
16. versionado;
17. estrategia de combinación;
18. reglas de veto factual;
19. campos visibles para Frontend;
20. información que consumirá exactamente el Agente Revisor.

---

# 184. Decisiones que sí pueden considerarse establecidas

Se consideran sólidas las siguientes reglas:

```text
Data/IA evalúa.
Backend orquesta.
Agentes corrige.
Frontend consume Backend.
```

También:

```text
chunks_used = evidencia factual
```

y:

```text
generation_context != evidencia factual
```

---

# 185. Recomendación final de compatibilidad

Sprint 4 debería comenzar con una estrategia:

```text
additive first
```

es decir:

```text
añadir capacidades
antes que reemplazar contratos
```

---

# 186. Contrato recomendado para primera iteración

Mantener:

```text
document_id
format
status
scores
informacion_no_respaldada
observaciones
evaluator_version
rubric_version
```

y añadir progresivamente:

```text
heuristic_scores
semantic_status
semantic_scores
semantic_observations
recommendations
unsupported_information
```

---

# 187. Ventajas de esta estrategia

- reduce breaking changes;
- permite trabajo paralelo con Backend;
- permite implementar semántico antes de cerrar toda la integración;
- facilita calibración;
- conserva trazabilidad;
- permite rollback;
- mantiene tests existentes;
- evita bloquear el Sprint.

---

# 188. Próximo paso técnico

Después de aprobar esta revisión, el siguiente entregable debería ser:

```text
semantic_rubric_v0_1.md
```

---

# 189. Objetivo de Semantic Rubric

Definir exactamente qué significa:

```text
1
2
3
4
5
```

para cada dimensión:

```text
relevancia
coherencia
adaptacion_didactica
informacion_respaldada
```

---

# 190. Después de la rúbrica

El orden recomendado es:

```text
Contract compatibility
        ↓
Semantic rubric
        ↓
Semantic schemas
        ↓
Semantic evaluator
        ↓
Dataset
        ↓
Calibration
        ↓
Decision layer
        ↓
Backend integration
        ↓
Correction E2E
```

---

# 191. Archivos relacionados

La implementación deberá revisarse especialmente contra:

```text
Data_IA/data_ai/api/app.py
Data_IA/data_ai/schemas/evaluation.py
Data_IA/data_ai/schemas/format_evaluation.py
Data_IA/data_ai/evaluation/quality_evaluator.py
Data_IA/data_ai/evaluation/reviewer.py
Data_IA/data_ai/evaluation/rubric.py
Data_IA/data_ai/evaluation/config.py
```

---

# 192. Archivos Backend relacionados

```text
backend/app/ports/data_ia_port.py
backend/app/application/format_evaluation_service.py
backend/app/infrastructure/integrations/http_data_ia_adapter.py
backend/app/domain/format_evaluation.py
```

---

# 193. Archivos Agentes relacionados

La integración futura del ciclo deberá tener en cuenta:

```text
agentes/agent_v1.py
agentes/api.py
agentes/generated_schemas.py
```

además de los nuevos componentes del Revisor que se implementen en Sprint 4.

---

# 194. Nota sobre Agentes

No se recomienda que Data/IA modifique la arquitectura interna de Agentes.

La responsabilidad de Data/IA termina al producir:

```text
métricas
hallazgos
recomendaciones
evidencia de problemas
```

---

# 195. Nota sobre Backend

Backend deberá decidir técnicamente cómo:

- identificar un ciclo;
- vincular generaciones;
- recuperar evaluaciones;
- limitar reintentos;
- persistir nuevos campos;
- entregar el historial al Frontend.

---

# 196. Nota sobre Frontend

Frontend no debe necesitar conocer:

```text
cómo funciona el evaluador semántico internamente
```

Solo necesita la información final que Backend decida exponer.

---

# 197. Resultado conceptual esperado

Al finalizar la evolución, Data/IA debería ser capaz de devolver información equivalente a:

```text
El contenido requiere revisión.

La relevancia es adecuada y el contenido está mayormente
respaldado por la evidencia.

Sin embargo, la adaptación didáctica no corresponde al
perfil junior solicitado porque introduce tres conceptos
avanzados sin explicación previa.

Se recomienda definir primero los conceptos de contenedor,
orquestación y service discovery antes de reutilizarlos.
```

---

# 198. Diferencia respecto a Sprint 3

Sprint 3:

```text
score + status
```

Sprint 4:

```text
score
+
diagnóstico
+
recomendación
+
status
```

---

# 199. Estado final de este documento

```text
Draft
```

No representa todavía un contrato aprobado.

Su función es servir como base para:

```text
Data/IA
BackendAPI
Agentes
Frontend
Project Manager
```

antes de modificar contratos públicos.

---

# 200. Conclusión

La revisión demuestra que el contrato actual ya contiene una base suficientemente sólida para Sprint 4.

No es necesario rediseñar completamente:

```text
BackendAPI → Data/IA
```

La principal evolución debe concentrarse en:

```text
Data/IA → BackendAPI
```

agregando información semántica y correctiva de forma progresiva.

La estrategia recomendada es:

```text
mantener compatibilidad
+
añadir evaluación semántica
+
calibrar
+
migrar contrato después
```

en lugar de introducir un breaking change antes de validar el comportamiento del nuevo evaluador.

---

## Próximo entregable

Crear:

```text
Data_IA/docs/semantic_rubric_v0_1.md
```

para definir la rúbrica semántica exacta de Sprint 4 antes de implementar `semantic_evaluator.py`.

---

# Addendum — Integración con Retrieval v2.0 y Agentes

Después de la revisión conjunta con el equipo de Agentes se acordó:

```text
Retrieval:
success | no_results | error
```

```text
Generation:
success | failed | no_results
```

Estos vocabularios permanecerán separados.

Data/IA mantendrá compatibilidad con campos adicionales en Retrieval v2.0, incluyendo potencialmente:

```text
latency_ms
```

El benchmark oficial conserva como referencia reproducible:

```text
Corpus:
Data_IA/data/evaluation/chunks_v1.csv

Ground Truth:
Data_IA/data/evaluation/ground_truth_v2.csv

Chroma:
.benchmark_chroma_v2

Collection:
benchmark_retrieval_v2
```

Los chunks del benchmark se cargan directamente desde el corpus congelado y no deben regenerarse cuando cambien parámetros de chunking.

La política HTTP y las demás decisiones de integración quedan detalladas en:

```text
Data_IA/docs/sprint4_integration_decisions.md
```

---

# Actualización posterior a revisión con Backend y Agentes

Las siguientes decisiones dejan de considerarse pendientes:

```text
semantic_evaluation
→ objeto anidado

verdict canónico
→ approved | requires_revision | rejected

fallback semántico
→ utilizar heurístico cuando sea válido

persistencia/historial
→ BackendAPI

heurístico + semántico
→ permanecen separados

final_score
→ no se implementa antes de calibración

proveedor semántico
→ Gemini

configuración del proveedor
→ independiente para Data/IA
```

La migración desde los valores históricos:

```text
aprobado
requiere_revision
rechazado
```

deberá coordinarse con BackendAPI antes de eliminar soporte a los valores
actuales.

La evolución continuará siendo aditiva hasta que Backend complete la
migración al contrato Evaluation V2.