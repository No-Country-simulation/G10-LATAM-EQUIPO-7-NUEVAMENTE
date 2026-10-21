# NuevaMente — Evaluation Contract V2

**Estado:** Draft  
**Sprint:** 4  
**Área responsable:** Data/IA  
**Integración principal:** BackendAPI ↔ Data/IA  
**Consumidores indirectos:** Agentes y Frontend  
**Objetivo:** Definir el contrato funcional y técnico de evaluación para soportar el ciclo de generación, evaluación, corrección y reevaluación de contenido educativo.

---

## 1. Propósito

Sprint 4 introduce una evolución del servicio Data/IA.

Hasta Sprint 3, Data/IA evaluaba contenido generado mediante un evaluador heurístico y devolvía principalmente:

- estado;
- puntuaciones;
- detección de información no respaldada;
- observaciones generales.

En Sprint 4, Data/IA pasa a desempeñar conceptualmente el rol de **Agente Evaluador**, capaz de:

- evaluar la calidad del contenido generado;
- producir métricas heurísticas;
- producir métricas semánticas;
- detectar problemas concretos;
- identificar información no respaldada;
- generar observaciones explicativas;
- generar recomendaciones accionables;
- devolver un veredicto utilizable por BackendAPI.

El objetivo es que BackendAPI pueda utilizar esta evaluación para decidir si el contenido:

1. se aprueba;
2. requiere una corrección automática;
3. debe finalizar el ciclo por una condición crítica o límite de reintentos.

---

# 2. Principios de arquitectura

## 2.1 Data/IA evalúa, no corrige

Data/IA tiene como responsabilidad:

- analizar;
- medir;
- diagnosticar;
- recomendar.

Data/IA **no modifica directamente el contenido generado**.

La corrección corresponde al servicio de Agentes.

---

## 2.2 BackendAPI orquesta el ciclo

BackendAPI es responsable de:

- recibir contenido generado por Agentes;
- enviar el contenido a Data/IA;
- persistir cada evaluación;
- interpretar el veredicto;
- controlar el límite de reintentos;
- enviar recomendaciones al Agente Revisor;
- recibir la versión corregida;
- solicitar una nueva evaluación;
- finalizar el ciclo;
- construir la respuesta final para Frontend.

---

## 2.3 Agentes genera y corrige

El servicio de Agentes es responsable de:

- recuperar evidencia mediante RAG;
- generar contenido educativo;
- proporcionar `sources_used` / `chunks_used`;
- recibir recomendaciones por medio de BackendAPI;
- generar una versión corregida cuando corresponda.

No existe comunicación directa:

```text
Agentes → Data/IA
```

La comunicación correcta es:

```text
Agentes
   ↓
BackendAPI
   ↓
Data/IA
```

---

## 2.4 Frontend no consume Data/IA directamente

Frontend recibe la información consolidada mediante BackendAPI.

Por lo tanto:

```text
Data/IA
   ↓
BackendAPI
   ↓
Frontend
```

Data/IA no es responsable de:

- construir el historial de evaluaciones del ciclo;
- decidir qué componente visual utilizar;
- ordenar evaluaciones para la interfaz;
- entregar contenido directamente al usuario.

---

# 3. Flujo general de Sprint 4

```text
Usuario
  ↓
Frontend
  ↓
BackendAPI
  ↓
Agentes
  ↓
Investigador RAG
  ↓
Redactor Pedagógico
  ↓
Contenido generado + chunks utilizados
  ↓
BackendAPI
  ↓
Data/IA /evaluate
  ↓
Evaluador Heurístico
        +
Evaluador Semántico
  ↓
Métricas
Hallazgos
Recomendaciones
Veredicto
  ↓
BackendAPI
  ↓
¿Contenido aprobado?
  ├── Sí
  │    ↓
  │ Finalizar ciclo
  │
  └── No
       ↓
    ¿Quedan reintentos?
       ├── Sí
       │    ↓
       │ Agente Revisor
       │    ↓
       │ Contenido corregido
       │    ↓
       │ Nueva evaluación
       │
       └── No
            ↓
         Finalizar ciclo
```

Para Sprint 4 se establece inicialmente:

```text
máximo 1 reintento automático de corrección
```

Esto permite como máximo:

```text
Generación inicial
      ↓
Evaluación 1
      ↓
Corrección
      ↓
Evaluación 2
```

---

# 4. Endpoint de evaluación

Se conserva como base el endpoint existente:

```http
POST /evaluate
```

El contrato actual debe evolucionar sin romper innecesariamente la integración existente.

---

# 5. Request BackendAPI → Data/IA

## 5.1 Estructura conceptual

```json
{
  "document_id": "doc_123",
  "format": "quiz",
  "generated_content": {},
  "generation_context": {
    "profile": "junior",
    "niche": "backend",
    "detail_level": "medium",
    "learning_objective": "Comprender los fundamentos de APIs REST"
  },
  "chunks_used": []
}
```

---

# 6. Campo `document_id`

Identificador único del documento fuente.

Ejemplo:

```json
{
  "document_id": "doc_123"
}
```

Debe coincidir con el documento asociado a los chunks utilizados.

---

# 7. Campo `format`

Tipo de contenido educativo que se está evaluando.

Valores soportados:

```text
quiz
flashcards
tldr
video_script
```

El tipo de `generated_content` depende del valor de `format`.

---

# 8. Campo `generated_content`

Representa el contenido estructurado generado por Agentes.

La estructura depende del formato.

---

## 8.1 Quiz

Ejemplo conceptual:

```json
{
  "title": "Fundamentos de APIs REST",
  "instructions": "Selecciona la respuesta correcta.",
  "questions": [
    {
      "question_id": "q1",
      "question": "¿Qué caracteriza a una API REST?",
      "options": [
        "Uso de recursos y métodos HTTP",
        "Uso exclusivo de SQL",
        "Ejecución local obligatoria",
        "Uso exclusivo de WebSockets"
      ],
      "correct_answer": "Uso de recursos y métodos HTTP",
      "explanation": "REST utiliza recursos y operaciones HTTP para interactuar con ellos."
    }
  ]
}
```

---

## 8.2 Flashcards

Ejemplo conceptual:

```json
{
  "title": "Conceptos REST",
  "instructions": "Utiliza las tarjetas para repasar conceptos.",
  "cards": [
    {
      "card_id": "c1",
      "front": "HTTP GET",
      "back": "Método utilizado normalmente para recuperar recursos."
    }
  ]
}
```

---

## 8.3 TLDR

Ejemplo conceptual:

```json
{
  "title": "Resumen de REST",
  "summary": "REST es un estilo arquitectónico utilizado para diseñar servicios web.",
  "key_points": [
    "Utiliza recursos",
    "Se apoya en métodos HTTP",
    "Promueve interfaces uniformes"
  ],
  "conclusion": "REST permite construir APIs simples y escalables."
}
```

---

## 8.4 Video Script

Ejemplo conceptual:

```json
{
  "title": "Introducción a REST",
  "estimated_duration_minutes": 3,
  "scenes": [
    {
      "scene_id": "s1",
      "title": "¿Qué es REST?",
      "narration": "REST es un estilo arquitectónico utilizado en servicios web.",
      "visual_description": "Mostrar un diagrama cliente-servidor.",
      "duration_seconds": 40
    }
  ]
}
```

---

# 9. Campo `generation_context`

Contexto pedagógico utilizado durante la generación.

Estructura base:

```json
{
  "profile": "junior",
  "niche": "backend",
  "detail_level": "medium",
  "learning_objective": "Comprender los fundamentos de APIs REST"
}
```

---

## 9.1 `profile`

Representa el perfil de usuario objetivo.

Ejemplos:

```text
beginner
junior
student
professional
```

El vocabulario definitivo deberá coordinarse con Backend y Agentes.

---

## 9.2 `niche`

Representa el dominio temático principal.

Ejemplos:

```text
backend
frontend
data science
cloud
artificial intelligence
```

---

## 9.3 `detail_level`

Nivel de profundidad esperado.

Ejemplos:

```text
low
medium
high
```

Debe mantenerse una convención única entre Agentes, Backend y Data/IA.

---

## 9.4 `learning_objective`

Objetivo pedagógico del contenido.

Ejemplo:

```text
Comprender los fundamentos de APIs REST
```

---

# 10. Uso permitido de `generation_context`

`generation_context` puede utilizarse para evaluar:

- relevancia;
- adaptación didáctica;
- nivel técnico;
- profundidad esperada;
- adecuación al perfil.

No debe utilizarse para validar afirmaciones factuales.

Regla:

```text
generation_context != evidencia factual
```

---

# 11. Campo `chunks_used`

Representa la evidencia documental utilizada para generar el contenido.

Ejemplo:

```json
[
  {
    "chunk_id": "chunk_001",
    "document_id": "doc_123",
    "rank": 1,
    "score": 0.93,
    "text": "REST es un estilo arquitectónico para sistemas distribuidos que utiliza recursos y operaciones HTTP."
  },
  {
    "chunk_id": "chunk_002",
    "document_id": "doc_123",
    "rank": 2,
    "score": 0.87,
    "text": "Los métodos GET, POST, PUT y DELETE permiten operar sobre recursos."
  }
]
```

---

# 12. Regla de evidencia factual

Para evaluar respaldo técnico:

```text
única fuente factual válida = chunks_used
```

No deben utilizarse como evidencia factual:

```text
profile
niche
detail_level
learning_objective
prompt
conocimiento interno del modelo
```

Esto preserva la trazabilidad del sistema RAG.

---

# 13. Response Data/IA → BackendAPI

La respuesta de Sprint 4 debe evolucionar desde el contrato actual.

La salida conceptual deberá contener:

```text
identificación
+
scores heurísticos
+
scores semánticos
+
observaciones
+
recomendaciones
+
información no respaldada
+
veredicto
+
versionado
```

---

# 14. Propuesta de respuesta V2

```json
{
  "document_id": "doc_123",
  "format": "quiz",

  "verdict": "requires_revision",

  "heuristic_scores": {
    "relevance": 4,
    "coherence": 5,
    "didactic_adaptation": 3,
    "content_support": 4
  },

  "semantic_scores": {
    "relevance": 4.6,
    "coherence": 4.7,
    "didactic_adaptation": 2.8,
    "content_support": 4.2
  },

  "observations": [
    {
      "dimension": "didactic_adaptation",
      "severity": "high",
      "message": "El contenido utiliza conceptos superiores al nivel junior solicitado."
    }
  ],

  "recommendations": [
    {
      "dimension": "didactic_adaptation",
      "message": "Explicar los conceptos básicos antes de introducir terminología avanzada."
    }
  ],

  "unsupported_information": [],

  "evaluator_version": "2.0.0",
  "rubric_version": "2.0.0"
}
```

Este ejemplo representa una **propuesta de diseño**.

Los nombres de campos deberán congelarse después de validarlos con BackendAPI.

---

# 15. Dimensiones de evaluación

Sprint 4 conserva cuatro dimensiones conceptuales.

```text
relevance
coherence
didactic_adaptation
content_support
```

---

# 16. Relevance

Pregunta principal:

> ¿El contenido responde al objetivo de aprendizaje y al dominio solicitado?

Entradas utilizadas:

```text
generated_content
learning_objective
niche
```

Ejemplos de problemas:

- contenido fuera de tema;
- explicación parcialmente relacionada;
- omisión del objetivo principal;
- foco excesivo en conceptos secundarios.

---

# 17. Coherence

Pregunta principal:

> ¿El contenido mantiene una estructura lógica y consistente?

Entradas utilizadas:

```text
generated_content
```

El evaluador debe detectar:

- contradicciones internas;
- saltos lógicos;
- ideas inconexas;
- conclusiones sin desarrollo previo;
- preguntas cuya explicación contradice la respuesta;
- secuencias desordenadas.

Ejemplo:

```text
La conclusión introduce microservicios aunque el contenido anterior no desarrolla ese concepto.
```

---

# 18. Didactic adaptation

Pregunta principal:

> ¿El contenido está correctamente adaptado al perfil y nivel solicitado?

Entradas:

```text
generated_content
profile
detail_level
```

El evaluador semántico debe considerar:

- complejidad del vocabulario;
- conocimientos asumidos;
- profundidad técnica;
- explicación de conceptos previos;
- longitud;
- densidad conceptual;
- adecuación pedagógica.

Ejemplo:

```text
El contenido utiliza service discovery, orchestration y service mesh sin explicación previa para un perfil junior.
```

---

# 19. Content support

Pregunta principal:

> ¿Las afirmaciones factuales están respaldadas por la evidencia documental?

Entradas:

```text
generated_content
chunks_used
```

El evaluador debe analizar afirmaciones y determinar si pueden sustentarse en la evidencia.

Ejemplo:

Contenido:

```text
Docker reemplaza completamente a Kubernetes.
```

Chunks:

```text
Docker permite crear contenedores.
Kubernetes permite orquestar contenedores.
```

Resultado esperado:

```text
afirmación no respaldada
```

---

# 20. Evaluador heurístico

El evaluador heurístico existente se conserva como una fuente independiente de evaluación.

Versión actual:

```text
Evaluator V1.1
```

Utiliza mecanismos como:

- normalización léxica;
- coincidencia de términos;
- reglas;
- longitudes;
- thresholds;
- detección básica de respaldo;
- rúbrica determinística.

Salida propuesta:

```json
{
  "heuristic_scores": {
    "relevance": 4,
    "coherence": 5,
    "didactic_adaptation": 3,
    "content_support": 4
  }
}
```

---

# 21. Evaluador semántico

Sprint 4 introduce un evaluador semántico independiente.

Su objetivo es evaluar significado y contexto, no solamente coincidencia lexical.

Debe analizar:

- relevancia conceptual;
- coherencia;
- adaptación pedagógica;
- adecuación al nivel;
- respaldo semántico;
- contradicciones;
- omisiones importantes;
- afirmaciones no sustentadas.

---

# 22. Salida del evaluador semántico

Ejemplo:

```json
{
  "semantic_scores": {
    "relevance": 4.5,
    "coherence": 4.2,
    "didactic_adaptation": 2.8,
    "content_support": 4.0
  },

  "observations": [
    {
      "dimension": "didactic_adaptation",
      "severity": "high",
      "message": "La explicación presupone conocimientos superiores al perfil junior."
    }
  ],

  "recommendations": [
    {
      "dimension": "didactic_adaptation",
      "message": "Definir primero los conceptos básicos antes de introducir orquestación."
    }
  ]
}
```

---

# 23. Escala de scores

Propuesta inicial:

```text
1 = deficiente
2 = insuficiente
3 = aceptable con revisión
4 = bueno
5 = excelente
```

El evaluador heurístico actual utiliza valores enteros.

El evaluador semántico podrá inicialmente devolver:

```text
valores 1.0–5.0
```

La precisión definitiva deberá validarse durante calibración.

---

# 24. Separación heuristic vs semantic

En Sprint 4 no se debe asumir inicialmente:

```text
50 % heurístico
+
50 % semántico
```

ni ningún otro peso arbitrario.

Se conservarán ambos resultados:

```text
heuristic_scores
semantic_scores
```

para poder comparar su comportamiento.

---

# 25. `final_scores`

Un futuro campo:

```text
final_scores
```

solo deberá introducirse si el dataset de calibración demuestra una estrategia razonable de combinación.

Las alternativas podrán incluir:

- ponderación;
- reglas;
- prioridad por dimensión;
- veto por condiciones críticas;
- combinación basada en calibración.

---

# 26. Guardrail de respaldo factual

`content_support` requiere un tratamiento especial.

Una afirmación factual grave no respaldada no debe poder compensarse simplemente con:

```text
alta relevancia
+
alta coherencia
+
buena adaptación
```

Ejemplo incorrecto:

```text
relevance = 5
coherence = 5
adaptation = 5
support = 1

promedio = 4
=> aprobado
```

Ese comportamiento no debe aceptarse.

El respaldo factual puede requerir una regla de veto.

---

# 27. Observations

Las observaciones representan hallazgos concretos.

Schema conceptual:

```json
{
  "dimension": "coherence",
  "severity": "medium",
  "message": "La conclusión introduce un concepto que no fue desarrollado previamente."
}
```

---

# 28. Dimensiones válidas para observaciones

Propuesta:

```text
relevance
coherence
didactic_adaptation
content_support
general
```

---

# 29. Severity

Valores iniciales:

```text
low
medium
high
```

Ejemplo:

```json
{
  "dimension": "content_support",
  "severity": "high",
  "message": "Se detectó una afirmación técnica sin respaldo documental."
}
```

---

# 30. Reglas de calidad para observaciones

Las observaciones deben ser:

- específicas;
- breves;
- comprensibles;
- relacionadas con un problema real;
- utilizables por Backend;
- potencialmente utilizables por el Agente Revisor.

Evitar observaciones como:

```text
"La calidad es baja."
```

Preferir:

```text
"La explicación introduce Kubernetes sin haber explicado previamente el concepto de orquestación."
```

---

# 31. Recommendations

Las recomendaciones deben indicar cómo corregir un problema.

Schema conceptual:

```json
{
  "dimension": "didactic_adaptation",
  "message": "Introducir primero una definición breve de contenedores antes de explicar orquestación."
}
```

---

# 32. Características de una recomendación útil

Debe ser:

- accionable;
- específica;
- relacionada con una observación;
- suficientemente clara para un agente generativo;
- limitada a la información disponible.

Evitar:

```text
"Mejorar la respuesta."
```

Preferir:

```text
"Reducir la cantidad de términos avanzados y explicar service discovery antes de utilizarlo en la conclusión."
```

---

# 33. Relación observación → recomendación

Ejemplo:

```json
{
  "observation": {
    "dimension": "didactic_adaptation",
    "severity": "high",
    "message": "El nivel técnico supera el perfil junior."
  },

  "recommendation": {
    "dimension": "didactic_adaptation",
    "message": "Simplificar la terminología y definir conceptos avanzados antes de utilizarlos."
  }
}
```

No se exige que el contrato final utilice esta estructura anidada.

Se presenta únicamente como relación conceptual.

---

# 34. Unsupported information

El evaluador semántico podrá identificar afirmaciones concretas no respaldadas.

Propuesta:

```json
{
  "unsupported_information": [
    {
      "claim": "Docker reemplaza completamente a Kubernetes.",
      "reason": "No existe evidencia suficiente en los chunks utilizados."
    }
  ]
}
```

---

# 35. Posible extensión de trazabilidad

De considerarse útil, una afirmación podría incluir:

```json
{
  "claim": "Docker utiliza Kubernetes internamente.",
  "reason": "La afirmación no está respaldada por la evidencia.",
  "related_chunk_ids": []
}
```

O, para información respaldada:

```json
{
  "claim": "REST utiliza recursos y métodos HTTP.",
  "supported_by": [
    "chunk_001",
    "chunk_002"
  ]
}
```

Esta extensión queda pendiente de validación por costo y utilidad.

---

# 36. Verdict

Propuesta de vocabulario técnico canónico:

```text
approved
requires_revision
rejected
```

---

# 37. `approved`

Significa:

- calidad suficiente;
- no existen fallos críticos;
- el contenido puede considerarse válido;
- BackendAPI puede finalizar el ciclo.

---

# 38. `requires_revision`

Significa:

- existen problemas corregibles;
- las observaciones y recomendaciones pueden utilizarse para mejorar el contenido;
- BackendAPI puede solicitar corrección si quedan reintentos.

---

# 39. `rejected`

Significa que existe una condición crítica.

Posibles ejemplos:

- información factual grave no respaldada;
- contenido totalmente irrelevante;
- calidad insuficiente;
- error estructural severo.

La diferencia exacta entre:

```text
requires_revision
```

y:

```text
rejected
```

debe acordarse con BackendAPI.

Especialmente debe definirse si:

```text
rejected
```

permite corrección automática o implica finalizar el ciclo.

---

# 40. Compatibilidad con el contrato actual

Actualmente Data/IA utiliza estados:

```text
aprobado
requiere_revision
rechazado
```

Sprint 4 propone evaluar una migración a:

```text
approved
requires_revision
rejected
```

La migración no debe implementarse unilateralmente.

Debe acordarse con BackendAPI para evitar romper persistencia, tests o lógica existente.

---

# 41. Versionado

La respuesta debe mantener información de versión.

Ejemplo:

```json
{
  "evaluator_version": "2.0.0",
  "rubric_version": "2.0.0"
}
```

Sin embargo, la numeración final deberá definirse al completar el alcance.

Posibles alternativas:

```text
Evaluator 1.2.0
```

si el cambio es compatible,

o:

```text
Evaluator 2.0.0
```

si se considera una evolución mayor del contrato.

---

# 42. Evaluación independiente por llamada

Cada request a:

```http
POST /evaluate
```

produce una evaluación independiente.

Ejemplo:

```text
evaluación inicial
!=
evaluación después de corrección
```

Data/IA no necesita conocer obligatoriamente el historial anterior para evaluar la nueva versión.

---

# 43. Historial del ciclo

Data/IA no administra el historial.

Responsabilidad:

```text
BackendAPI
```

Backend deberá:

- guardar cada evaluación;
- asociarla a la generación correspondiente;
- identificar el último ciclo;
- recuperar todas las evaluaciones de dicho ciclo;
- ordenarlas desde la más reciente a la más antigua.

---

# 44. Respuesta Backend → Frontend

Data/IA no define directamente el contrato final de Frontend.

Sin embargo, Data/IA debe entregar información suficientemente útil para que Backend pueda exponer:

```text
contenido final
+
historial de métricas
+
estado final
+
observaciones relevantes
```

---

# 45. Información recomendada para Frontend

Como requerimiento funcional, se considera útil que Backend pueda exponer al Front:

- estado final de evaluación;
- scores;
- evolución de scores;
- observaciones importantes;
- indicador de que hubo revisión/corrección.

No es necesario que Frontend reciba detalles internos del evaluador semántico.

---

# 46. Comportamiento cuando falla el evaluador semántico

Sprint 4 debe contemplar degradación controlada.

Ejemplo conceptual:

```json
{
  "semantic_status": "unavailable"
}
```

Si el evaluador semántico falla, el endpoint no debería necesariamente perder toda capacidad de evaluación.

Posible comportamiento:

```text
heurístico disponible
+
semántico no disponible
=
respuesta parcial controlada
```

La política definitiva debe acordarse con Backend.

---

# 47. Posibles causas de fallo semántico

Ejemplos:

```text
timeout
API key inválida
modelo no disponible
quota exceeded
respuesta mal formada
JSON inválido
error de proveedor
```

---

# 48. Regla de fallback

No se debe simular un resultado semántico.

Ejemplo incorrecto:

```text
semantic_scores = heuristic_scores
```

cuando el modelo semántico falla.

Eso ocultaría un error real.

Debe reportarse explícitamente la indisponibilidad.

---

# 49. Modelo semántico

La implementación del evaluador semántico debe definir:

```text
provider
model
temperature
timeout
retry policy
structured output
```

Esta configuración no queda congelada en este documento.

---

# 50. Structured output

El evaluador semántico debería utilizar una respuesta estructurada validada.

Ejemplo conceptual:

```json
{
  "scores": {
    "relevance": 4.5,
    "coherence": 4.0,
    "didactic_adaptation": 3.0,
    "content_support": 4.2
  },
  "observations": [],
  "recommendations": [],
  "unsupported_information": []
}
```

La respuesta del modelo nunca deberá enviarse directamente a Backend sin validación.

---

# 51. Dataset de calibración

Antes de combinar scores deberá crearse un dataset de calibración.

Debe contener casos como:

```text
contenido correcto
contenido irrelevante
contenido incoherente
contenido con alucinación
contenido demasiado avanzado
contenido demasiado básico
contenido parcialmente respaldado
contenido correcto pero incompleto
```

---

# 52. Cobertura de formatos del dataset

Debe incluir:

```text
quiz
flashcards
tldr
video_script
```

Se recomienda cubrir múltiples dominios y niveles.

---

# 53. Ground Truth humano

Cada caso de calibración deberá incluir una evaluación humana esperada.

Ejemplo:

```json
{
  "expected_scores": {
    "relevance": 5,
    "coherence": 4,
    "didactic_adaptation": 3,
    "content_support": 5
  },
  "expected_verdict": "requires_revision"
}
```

---

# 54. Métricas de calibración

Se deberá comparar:

```text
human evaluation
vs
heuristic evaluation
vs
semantic evaluation
```

El objetivo es determinar:

- concordancia;
- divergencias;
- falsos positivos;
- falsos negativos;
- dimensiones con mayor error.

---

# 55. Evaluación del nivel técnico

Una prioridad de Sprint 4 es comprobar que el nivel solicitado realmente se respeta.

Ejemplo:

```text
profile = junior
detail_level = medium
```

El evaluador deberá analizar si el contenido:

- presupone conocimientos avanzados;
- utiliza jerga sin explicación;
- profundiza más de lo solicitado;
- simplifica demasiado;
- corresponde al perfil esperado.

---

# 56. Ejemplo de observación de nivel

```json
{
  "dimension": "didactic_adaptation",
  "severity": "high",
  "message": "El contenido utiliza conceptos de service mesh, orchestration y discovery sin explicación previa, por lo que excede el nivel junior solicitado."
}
```

---

# 57. Ejemplo de recomendación de nivel

```json
{
  "dimension": "didactic_adaptation",
  "message": "Introducir primero conceptos básicos de contenedores y comunicación entre servicios antes de explicar service discovery."
}
```

---

# 58. Contrato con Agente Revisor

Data/IA no invoca directamente al Revisor.

La información deberá viajar:

```text
Data/IA
   ↓
BackendAPI
   ↓
Agente Revisor
```

El Revisor necesitará principalmente:

```text
contenido actual
chunks/evidencia
observaciones
recomendaciones
contexto pedagógico
```

---

# 59. Lo que Data/IA debe proporcionar al Revisor indirectamente

Información útil:

```text
qué está mal
por qué está mal
qué debería cambiar
qué información carece de respaldo
qué dimensión presenta el problema
```

Los scores por sí solos no son suficientes.

---

# 60. No duplicar responsabilidades

El Agente Revisor no debería volver a implementar la lógica completa de evaluación.

Data/IA:

```text
evalúa
```

Agente Revisor:

```text
corrige
```

Backend:

```text
orquesta
```

---

# 61. Compatibilidad con los cuatro formatos

Toda extensión de Sprint 4 debe seguir soportando:

```text
quiz
flashcards
tldr
video_script
```

No debe regresarse a un contrato limitado solo a:

```text
quiz
flashcards
```

---

# 62. Cleanup técnico relacionado

Durante Sprint 4 se deberá revisar que los tipos internos del reviewer reflejen correctamente los cuatro formatos.

Conceptualmente:

```python
GeneratedContent = Union[
    QuizContent,
    FlashcardsContent,
    TLDRContent,
    VideoScriptContent,
]
```

Este cambio deberá implementarse en código dentro de la rama correspondiente.

---

# 63. Reglas de backward compatibility

Se intentará conservar:

```text
document_id
format
generated_content
generation_context
chunks_used
```

Los cambios principales se concentrarán en la respuesta.

Si fuera necesario modificar el request, deberá justificarse y coordinarse con Backend.

---

# 64. Campos que no deben asumirse como obligatorios todavía

Los siguientes campos aparecen en diagramas conceptuales, pero no deben incorporarse al contrato sin acuerdo:

```text
format_id
attempt
cycle_id
retry_count
```

Backend puede gestionarlos internamente.

Solo deberán incorporarse a Data/IA si existe una necesidad funcional real.

---

# 65. Regla sobre `format_id`

Actualmente Backend puede utilizar `format_id` para vincular internamente una evaluación con una generación.

Eso no implica que:

```text
format_id
```

deba convertirse automáticamente en un campo obligatorio del request Data/IA.

Debe acordarse primero.

---

# 66. Regla sobre `attempt`

Data/IA no necesita conocer necesariamente:

```text
attempt = 0
attempt = 1
```

para evaluar la calidad de un contenido.

El control de reintentos pertenece a Backend.

Podría añadirse únicamente si se necesita para:

- trazabilidad;
- logging;
- auditoría;
- análisis comparativo.

---

# 67. Seguridad y secretos

Si Data/IA utiliza un proveedor externo de IA, las credenciales:

```text
API keys
tokens
secrets
```

no deben almacenarse en el repositorio.

Deberán cargarse mediante variables de entorno o infraestructura segura.

---

# 68. Configuración de contenedor

La incorporación del evaluador semántico probablemente requerirá ampliar la configuración de:

```text
data-ia
```

para incluir:

```text
modelo
API key
timeout
otros parámetros
```

La decisión debe coordinarse con Infraestructura.

---

# 69. Dependencias

Si el evaluador semántico utiliza un SDK externo, deberá agregarse explícitamente a:

```text
Data_IA/requirements.txt
```

y validarse dentro de Docker y CI.

---

# 70. CI

Los cambios de Data/IA deberán pasar:

```text
Data IA - Tests
```

dentro del workflow de QA.

Además, cambios de contrato pueden impactar:

```text
Backend - Tests and lint
Agents - Tests
Frontend - Build
```

Por lo tanto, la integración deberá comprobar los cuatro jobs.

---

# 71. Pruebas unitarias mínimas del evaluador semántico

Se deberán cubrir:

```text
caso aprobado
caso requiere revisión
caso no respaldado
caso incoherente
caso nivel incorrecto
modelo no disponible
timeout
respuesta inválida
```

---

# 72. Pruebas de integración

Se deberá comprobar:

```text
Backend
  ↓
Data/IA
```

con payload real.

Y posteriormente:

```text
Agentes
  ↓
Backend
  ↓
Data/IA
  ↓
Backend
  ↓
Agente Revisor
  ↓
Backend
  ↓
Data/IA
```

---

# 73. Prueba E2E mínima de Sprint 4

Objetivo:

```text
generación
↓
evaluación
↓
requires_revision
↓
corrección
↓
reevaluación
↓
approved
```

Debe conservarse evidencia suficiente para demostrar el recorrido.

---

# 74. Regresión

Sprint 4 no debe romper:

- Retrieval V2;
- generación multiformato;
- `learning_metadata`;
- `sources_used`;
- persistencia existente;
- schemas actuales de formatos;
- evaluación heurística;
- integración actual Backend ↔ Data/IA.

---

# 75. Resultado esperado

Al finalizar Sprint 4, Data/IA debería poder responder conceptualmente:

> El contenido presenta un nivel de relevancia alto, pero la adaptación didáctica es insuficiente para un perfil junior. Se detectaron dos conceptos avanzados introducidos sin explicación previa. Se recomienda simplificar la terminología y explicar esos conceptos antes de reutilizarlos. El contenido requiere revisión.

En lugar de limitarse a:

```text
adaptacion_didactica = 2
```

---

# 76. Definition of Done del contrato

Este contrato podrá considerarse congelado cuando:

- Backend valide request y response;
- Data/IA valide estructura interna;
- Agentes confirme que las recomendaciones son accionables;
- Frontend confirme qué datos necesita visualizar;
- se acuerde vocabulario de estados;
- se acuerde estrategia de fallback;
- se definan schemas Pydantic;
- exista al menos un payload válido de ejemplo;
- existan tests de contrato.

---

# 77. Decisiones pendientes

Antes de marcar este documento como estable deben resolverse:

1. vocabulario final de `verdict`;
2. mantener español o migrar códigos técnicos a inglés;
3. schema final de `observations`;
4. schema final de `recommendations`;
5. schema final de `unsupported_information`;
6. rango definitivo de scores semánticos;
7. comportamiento de `rejected`;
8. estrategia de fallback;
9. timeout del evaluador semántico;
10. modelo/proveedor;
11. versión final de evaluator;
12. versión final de rubric;
13. estrategia heurístico + semántico;
14. eventual `final_scores`;
15. campos visibles para Frontend;
16. necesidad o no de `attempt`;
17. necesidad o no de `format_id`.

---

# 78. Propuesta de decisiones iniciales

Como punto de partida se propone:

```text
Request:
mantener compatible con V1 siempre que sea posible.

Heuristic:
conservar V1.1 sin modificar inicialmente.

Semantic:
implementar como módulo separado.

Evidence:
solo chunks_used.

Scores:
heuristic_scores y semantic_scores separados.

Observations:
estructuradas.

Recommendations:
estructuradas y accionables.

Verdict:
determinado por una capa de decisión.

Retries:
responsabilidad de Backend.

Correction:
responsabilidad de Agentes.

History:
responsabilidad de Backend.

Frontend:
consume Backend, nunca Data/IA directamente.
```

---

# 79. Arquitectura objetivo de Data/IA

```text
                 POST /evaluate
                       │
                       ▼
             Evaluation Request
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
Heuristic Evaluator         Semantic Evaluator
     V1.1                         V0.1
          │                         │
          ▼                         ▼
 heuristic_scores          semantic_scores
                                    │
                                    ├── observations
                                    ├── recommendations
                                    └── unsupported_information
          │                         │
          └────────────┬────────────┘
                       ▼
                Decision Layer
                       │
                       ▼
                    verdict
                       │
                       ▼
            Evaluation Response
```

---

# 80. Separación recomendada de módulos

Propuesta futura de implementación:

```text
Data_IA/
└── data_ai/
    ├── evaluation/
    │   ├── quality_evaluator.py
    │   ├── semantic_evaluator.py
    │   ├── hybrid_evaluator.py
    │   ├── rubric.py
    │   └── reviewer.py
    │
    ├── schemas/
    │   ├── evaluation.py
    │   └── format_evaluation.py
    │
    └── api/
        └── app.py
```

Esta estructura es orientativa y deberá ajustarse al código real.

---

# 81. Evolución conceptual

Sprint 3:

```text
contenido
   ↓
heurística
   ↓
scores
   ↓
status
```

Sprint 4:

```text
contenido
   ↓
heurística + evaluación semántica
   ↓
scores
   ↓
diagnóstico
   ↓
observaciones
   ↓
recomendaciones
   ↓
veredicto
   ↓
ciclo de corrección
```

---

# 82. Resumen

Data/IA en Sprint 4 debe convertirse en una capa de control de calidad capaz de responder tres preguntas:

```text
¿El contenido es suficientemente bueno?
```

```text
¿Qué problema tiene?
```

```text
¿Cómo debería corregirse?
```

El objetivo final no es únicamente puntuar contenido.

El objetivo es producir información suficientemente confiable y accionable para que BackendAPI pueda coordinar un ciclo automático de mejora junto con el Agente Revisor.

---

# 83. Estado del documento

```text
Draft
```

Este documento deberá revisarse conjuntamente con:

- BackendAPI;
- Agentes;
- Frontend;
- Project Manager.

No debe considerarse contrato definitivo hasta que los equipos involucrados validen los campos y comportamientos descritos.

---

## Próximo paso

Revisar este contrato contra:

```text
Data_IA/data_ai/schemas/format_evaluation.py
Data_IA/data_ai/schemas/evaluation.py
Data_IA/data_ai/evaluation/reviewer.py
Data_IA/data_ai/evaluation/rubric.py
backend/app/ports/data_ia_port.py
backend/app/application/format_evaluation_service.py
backend/app/infrastructure/integrations/http_data_ia_adapter.py
```

y generar una tabla:

```text
campo actual
campo propuesto
compatible
requiere cambio
responsable
```

antes de modificar código.

---

## Decisiones de integración Sprint 4

Las decisiones transversales relacionadas con:

- Retrieval Contract v2.0;
- códigos HTTP;
- `latency_ms`;
- corpus congelado;
- estabilidad de `chunk_id`;
- diferencias entre `error` y `failed`;
- schemas de Agentes;
- límites de responsabilidad entre Agentes y Data/IA;

se documentan en:

```text
Data_IA/docs/sprint4_integration_decisions.md
```

Este documento debe consultarse antes de modificar contratos relacionados con Retrieval o generación.

---

# Sprint 4 — Decisiones inter-área congeladas

Después de la revisión con Agentes y BackendAPI se confirman las siguientes
decisiones para Evaluation V2:

```text
Proveedor semántico:
Gemini / LLM-as-a-Judge

Configuración:
independiente para Data/IA

Semantic result:
semantic_evaluation anidado

Verdict:
approved | requires_revision | rejected

Fallback:
heurístico disponible + semántico fallido
→ conservar verdict heurístico

Persistencia:
BackendAPI

Historial:
BackendAPI

Scores:
heurístico y semántico separados

Final score:
no definido hasta calibración

Evidencia factual:
chunks_used únicamente
```

## Contrato conceptual de respuesta

```json
{
  "document_id": "doc_123",
  "format": "tldr",
  "verdict": "requires_revision",
  "heuristic_scores": {
    "relevance": 4,
    "coherence": 4,
    "didactic_adaptation": 3,
    "content_support": 4
  },
  "semantic_evaluation": {
    "status": "success",
    "scores": {
      "relevance": 4.5,
      "coherence": 4.2,
      "didactic_adaptation": 3.7,
      "content_support": 4.1
    },
    "observations": [],
    "recommendations": [],
    "unsupported_information": [],
    "error_code": null,
    "error_message": null,
    "model": "gemini-...",
    "prompt_version": "semantic-evaluator-v0.1",
    "latency_ms": 120
  },
  "evaluator_version": "...",
  "rubric_version": "..."
}
```

Este ejemplo continúa siendo conceptual hasta completar la implementación
del endpoint público.

La fuente de verdad para las decisiones transversales se encuentra en:

```text
Data_IA/docs/sprint4_integration_decisions.md
```