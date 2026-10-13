# NuevaMente — Semantic Rubric v0.1

**Sprint:** 4  
**Estado:** Draft  
**Área responsable:** Data/IA  
**Objetivo:** Definir la rúbrica semántica utilizada por el evaluador de Data/IA para analizar contenido educativo generado y producir métricas, hallazgos y recomendaciones accionables.

---

# 1. Propósito

La rúbrica semántica complementa al evaluador heurístico existente.

Su objetivo es evaluar aspectos que no pueden medirse de forma suficientemente fiable mediante:

- coincidencia léxica;
- longitud;
- reglas simples;
- thresholds determinísticos.

El evaluador semántico debe analizar significado, contexto, calidad pedagógica y relación entre el contenido generado y la evidencia disponible.

---

# 2. Principio general

El evaluador semántico no debe responder únicamente:

```text
score = 3
```

Debe producir:

```text
score
+
diagnóstico
+
recomendación
```

cuando exista un problema.

---

# 3. Entradas del evaluador semántico

El evaluador semántico recibe:

```text
generated_content
generation_context
chunks_used
format
```

---

# 4. Uso de `generated_content`

`generated_content` representa el contenido educativo que debe evaluarse.

Puede ser uno de los formatos:

```text
quiz
flashcards
tldr
video_script
```

---

# 5. Uso de `generation_context`

Incluye:

```text
profile
niche
detail_level
learning_objective
```

Se utiliza para evaluar:

```text
relevance
didactic_adaptation
```

No se utiliza como evidencia factual.

---

# 6. Uso de `chunks_used`

`chunks_used` representa la evidencia recuperada mediante RAG.

Debe utilizarse para evaluar:

```text
content_support
```

Regla:

```text
chunks_used = única evidencia factual válida
```

---

# 7. Dimensiones semánticas

La rúbrica evalúa cuatro dimensiones principales:

```text
1. relevance
2. coherence
3. didactic_adaptation
4. content_support
```

---

# 8. Escala general

Cada dimensión se evalúa en una escala de:

```text
1.0 – 5.0
```

Interpretación general:

```text
5 = excelente
4 = bueno
3 = aceptable pero requiere mejora
2 = insuficiente
1 = deficiente / crítico
```

---

# 9. Principio de consistencia

Las cuatro dimensiones deben mantener una interpretación comparable.

Sin embargo, la decisión final no debe basarse exclusivamente en un promedio.

Especialmente:

```text
content_support
```

puede requerir reglas de veto.

---

# 10. Relevance

Pregunta principal:

> ¿El contenido generado responde al objetivo de aprendizaje y al nicho solicitado?

---

# 11. Entradas para Relevance

Utilizar:

```text
generated_content
learning_objective
niche
```

---

# 12. Qué debe analizar Relevance

El evaluador debe determinar si:

- el tema principal corresponde al nicho;
- el contenido responde al objetivo solicitado;
- las ideas principales son pertinentes;
- el contenido evita desviaciones importantes;
- la explicación prioriza el foco correcto.

---

# 13. Relevance — Score 5

Asignar aproximadamente:

```text
5
```

cuando:

- el contenido está directamente alineado con el objetivo;
- cubre los conceptos necesarios;
- mantiene el foco;
- no contiene desviaciones relevantes.

Ejemplo:

Objetivo:

```text
Comprender los fundamentos de APIs REST
```

Contenido:

```text
explica recursos, métodos HTTP, endpoints y comunicación cliente-servidor
```

Resultado:

```text
relevance = 5
```

---

# 14. Relevance — Score 4

Asignar aproximadamente:

```text
4
```

cuando:

- el contenido es claramente relevante;
- cubre el objetivo principal;
- presenta pequeñas omisiones;
- incluye algún detalle secundario no esencial.

---

# 15. Relevance — Score 3

Asignar aproximadamente:

```text
3
```

cuando:

- el contenido está relacionado con el tema;
- responde parcialmente al objetivo;
- omite conceptos importantes;
- dedica demasiado espacio a aspectos secundarios.

Resultado:

```text
requires improvement
```

---

# 16. Relevance — Score 2

Asignar aproximadamente:

```text
2
```

cuando:

- el contenido solo está parcialmente relacionado;
- el foco principal no corresponde al objetivo;
- existe una desviación importante.

---

# 17. Relevance — Score 1

Asignar aproximadamente:

```text
1
```

cuando:

- el contenido es esencialmente irrelevante;
- responde a otro tema;
- no satisface el objetivo pedagógico.

---

# 18. Ejemplo de observación de Relevance

```json
{
  "dimension": "relevance",
  "severity": "medium",
  "message": "El contenido se concentra en despliegue de aplicaciones, aunque el objetivo solicitado es comprender los fundamentos de APIs REST."
}
```

---

# 19. Ejemplo de recomendación de Relevance

```json
{
  "dimension": "relevance",
  "message": "Reorientar el contenido hacia recursos, métodos HTTP y estructura de endpoints, reduciendo la sección de despliegue."
}
```

---

# 20. Coherence

Pregunta principal:

> ¿El contenido mantiene una estructura lógica, consistente y comprensible?

---

# 21. Entradas para Coherence

Utilizar principalmente:

```text
generated_content
```

---

# 22. Qué debe analizar Coherence

El evaluador debe detectar:

- contradicciones;
- saltos lógicos;
- ideas sin conexión;
- secuencia poco clara;
- conclusiones no sustentadas por el desarrollo;
- respuestas incompatibles con explicaciones;
- duplicaciones que afecten comprensión;
- estructura pedagógica confusa.

---

# 23. Coherence — Score 5

Asignar aproximadamente:

```text
5
```

cuando:

- la secuencia es clara;
- las ideas progresan lógicamente;
- no existen contradicciones;
- las conclusiones derivan del desarrollo;
- el formato es internamente consistente.

---

# 24. Coherence — Score 4

Asignar aproximadamente:

```text
4
```

cuando:

- el contenido es coherente;
- existen detalles menores de organización;
- puede haber alguna transición mejorable sin afectar comprensión.

---

# 25. Coherence — Score 3

Asignar aproximadamente:

```text
3
```

cuando:

- el contenido puede entenderse;
- existen saltos o inconsistencias moderadas;
- algunas ideas aparecen sin suficiente desarrollo.

---

# 26. Coherence — Score 2

Asignar aproximadamente:

```text
2
```

cuando:

- la estructura dificulta la comprensión;
- existen contradicciones importantes;
- varias partes no se conectan correctamente.

---

# 27. Coherence — Score 1

Asignar aproximadamente:

```text
1
```

cuando:

- el contenido es internamente contradictorio;
- la secuencia carece de lógica;
- resulta difícil determinar qué intenta enseñar.

---

# 28. Ejemplo de problema de Coherence

Contenido:

```text
Primero indica que REST requiere mantener estado entre solicitudes.
Después afirma que REST es stateless.
```

Resultado:

```text
coherence bajo
```

---

# 29. Ejemplo de observación de Coherence

```json
{
  "dimension": "coherence",
  "severity": "high",
  "message": "El contenido contiene afirmaciones contradictorias sobre el manejo de estado en REST."
}
```

---

# 30. Ejemplo de recomendación de Coherence

```json
{
  "dimension": "coherence",
  "message": "Corregir la contradicción y mantener una explicación consistente del principio stateless."
}
```

---

# 31. Didactic Adaptation

Pregunta principal:

> ¿El contenido corresponde al perfil, nivel de detalle y complejidad solicitados?

---

# 32. Entradas para Didactic Adaptation

Utilizar:

```text
generated_content
profile
detail_level
```

---

# 33. Qué debe analizar Didactic Adaptation

El evaluador debe considerar:

- complejidad del vocabulario;
- cantidad de conceptos nuevos;
- prerequisitos asumidos;
- nivel técnico;
- profundidad;
- densidad conceptual;
- explicaciones previas;
- longitud relativa;
- claridad;
- accesibilidad pedagógica.

---

# 34. Principio importante

No debe evaluarse nivel únicamente por longitud.

Un contenido breve puede ser demasiado avanzado.

Un contenido largo puede seguir siendo apropiado si explica correctamente.

---

# 35. Didactic Adaptation — Score 5

Asignar aproximadamente:

```text
5
```

cuando:

- el lenguaje corresponde al perfil;
- la profundidad es adecuada;
- conceptos complejos se explican antes de utilizarlos;
- no presupone conocimientos innecesarios;
- el contenido tiene el nivel de detalle solicitado.

---

# 36. Didactic Adaptation — Score 4

Asignar aproximadamente:

```text
4
```

cuando:

- la adaptación es buena;
- existe algún término o sección ligeramente más avanzada;
- la comprensión general sigue siendo adecuada.

---

# 37. Didactic Adaptation — Score 3

Asignar aproximadamente:

```text
3
```

cuando:

- el contenido es parcialmente adecuado;
- utiliza varios términos no explicados;
- el nivel es algo superior o inferior al solicitado;
- requiere ajustes pedagógicos.

---

# 38. Didactic Adaptation — Score 2

Asignar aproximadamente:

```text
2
```

cuando:

- el contenido está claramente desalineado con el perfil;
- presupone conocimientos avanzados;
- la profundidad es significativamente incorrecta.

---

# 39. Didactic Adaptation — Score 1

Asignar aproximadamente:

```text
1
```

cuando:

- el nivel es totalmente inadecuado;
- el contenido resulta prácticamente inaccesible para el perfil;
- o es tan simplificado que no cumple el propósito solicitado.

---

# 40. Ejemplo de nivel demasiado alto

Contexto:

```text
profile = junior
detail_level = medium
```

Contenido:

```text
El service mesh implementa sidecar proxies, mTLS,
circuit breaking y service discovery...
```

sin explicación previa.

Resultado:

```text
didactic_adaptation <= 3
```

---

# 41. Ejemplo de observación de nivel

```json
{
  "dimension": "didactic_adaptation",
  "severity": "high",
  "message": "El contenido introduce service mesh, mTLS y service discovery sin explicar previamente estos conceptos, superando el nivel junior solicitado."
}
```

---

# 42. Ejemplo de recomendación de nivel

```json
{
  "dimension": "didactic_adaptation",
  "message": "Introducir primero conceptos básicos de comunicación entre servicios y explicar los términos técnicos antes de utilizarlos."
}
```

---

# 43. Content Support

Pregunta principal:

> ¿Las afirmaciones factuales del contenido están respaldadas por los chunks proporcionados?

---

# 44. Entradas para Content Support

Utilizar exclusivamente:

```text
generated_content
chunks_used
```

---

# 45. Prohibición

No utilizar:

```text
conocimiento general del modelo
learning_objective
niche
profile
detail_level
```

como fuente factual.

---

# 46. Qué debe analizar Content Support

El evaluador debe:

- identificar afirmaciones factuales;
- compararlas con los chunks;
- determinar si están respaldadas;
- detectar contradicciones con la evidencia;
- detectar extrapolaciones;
- detectar información inventada;
- diferenciar framing/presentación de contenido factual.

---

# 47. Content Support — Score 5

Asignar aproximadamente:

```text
5
```

cuando:

- prácticamente todas las afirmaciones factuales están respaldadas;
- no existen contradicciones;
- no se introduce información externa significativa.

---

# 48. Content Support — Score 4

Asignar aproximadamente:

```text
4
```

cuando:

- el contenido está bien respaldado;
- puede existir una extrapolación menor;
- no afecta sustancialmente la exactitud.

---

# 49. Content Support — Score 3

Asignar aproximadamente:

```text
3
```

cuando:

- parte del contenido está respaldado;
- existen varias afirmaciones débiles;
- se requiere corrección o eliminación de algunos elementos.

---

# 50. Content Support — Score 2

Asignar aproximadamente:

```text
2
```

cuando:

- una parte importante del contenido no está sustentada;
- existen afirmaciones técnicas no disponibles en la evidencia;
- puede haber contradicciones con los chunks.

---

# 51. Content Support — Score 1

Asignar aproximadamente:

```text
1
```

cuando:

- la mayoría del contenido factual no está respaldada;
- existe información inventada significativa;
- el contenido contradice claramente la evidencia.

---

# 52. Ejemplo de afirmación no respaldada

Chunks:

```text
Docker permite crear y ejecutar contenedores.
Kubernetes permite orquestar contenedores.
```

Contenido:

```text
Docker reemplaza completamente a Kubernetes.
```

Resultado:

```text
unsupported claim
```

---

# 53. Ejemplo de hallazgo

```json
{
  "claim": "Docker reemplaza completamente a Kubernetes.",
  "reason": "Los chunks describen funciones diferentes para Docker y Kubernetes y no respaldan esta afirmación."
}
```

---

# 54. Ejemplo de recomendación

```json
{
  "dimension": "content_support",
  "message": "Eliminar o reformular la afirmación sobre reemplazo entre Docker y Kubernetes para ajustarla a la evidencia disponible."
}
```

---

# 55. Guardrail de Content Support

`content_support` no debe compensarse mediante promedio simple.

Ejemplo:

```text
relevance = 5
coherence = 5
didactic_adaptation = 5
content_support = 1
```

No debería resultar automáticamente en:

```text
approved
```

---

# 56. Regla provisional de guardrail

Durante calibración se propone:

```text
content_support <= 2
```

como señal fuerte de:

```text
requires_revision
```

o:

```text
rejected
```

La decisión exacta deberá validarse con dataset.

---

# 57. Evaluación según formato

La rúbrica general se mantiene igual, pero cada formato requiere consideraciones propias.

---

# 58. Quiz

Para `quiz`, evaluar:

- claridad de preguntas;
- coherencia entre pregunta y respuesta;
- validez de la explicación;
- distractores razonables;
- alineación con objetivo;
- respaldo de afirmaciones.

---

# 59. Problemas típicos en Quiz

Ejemplos:

```text
respuesta correcta ambigua
explicación contradice respuesta
pregunta fuera del objetivo
distractores absurdos
información no respaldada
nivel demasiado avanzado
```

---

# 60. Flashcards

Para `flashcards`, evaluar:

- relación front ↔ back;
- claridad;
- precisión;
- utilidad pedagógica;
- adecuación del nivel;
- respaldo factual.

---

# 61. Problemas típicos en Flashcards

```text
front ambiguo
back demasiado largo
definición incorrecta
conceptos repetidos
contenido no respaldado
```

---

# 62. TLDR

Para `tldr`, evaluar:

- fidelidad al contenido;
- síntesis;
- cobertura de ideas importantes;
- relación entre summary, key_points y conclusion;
- nivel;
- respaldo.

---

# 63. Consideración de TLDR

El título puede considerarse framing.

Las afirmaciones factuales principales están en:

```text
summary
key_points
conclusion
```

---

# 64. Problemas típicos en TLDR

```text
omisión del punto principal
conclusión no respaldada
resumen demasiado extenso
introducción de datos externos
nivel inadecuado
```

---

# 65. Video Script

Para `video_script`, evaluar:

- secuencia de escenas;
- continuidad pedagógica;
- narración;
- adecuación al nivel;
- respaldo factual de la narración.

---

# 66. Consideración de Video Script

La evaluación factual debe centrarse principalmente en:

```text
narration
```

y no interpretar automáticamente como afirmación factual:

```text
visual_description
```

---

# 67. Problemas típicos en Video Script

```text
escenas sin conexión
narración contradictoria
conceptos avanzados sin explicación
información inventada
tiempo poco razonable
```

---

# 68. Observations

El evaluador semántico debe producir observaciones únicamente cuando exista un hallazgo relevante.

---

# 69. Schema conceptual de Observation

```json
{
  "dimension": "coherence",
  "severity": "medium",
  "message": "La conclusión introduce un concepto que no fue desarrollado previamente."
}
```

---

# 70. Severity

Valores:

```text
low
medium
high
```

---

# 71. Severity — Low

Utilizar cuando:

- el problema es menor;
- no afecta sustancialmente la calidad;
- puede mejorarse sin cambiar el contenido central.

---

# 72. Severity — Medium

Utilizar cuando:

- afecta claridad o calidad;
- requiere corrección;
- pero no invalida totalmente el contenido.

---

# 73. Severity — High

Utilizar cuando:

- existe un problema importante;
- puede inducir a error;
- el nivel es claramente incorrecto;
- existe contradicción;
- existe información factual no sustentada relevante.

---

# 74. Reglas para Observation

Una observación debe:

- mencionar un problema concreto;
- indicar la dimensión;
- explicar qué ocurre;
- evitar vaguedades.

---

# 75. Observación inválida

```text
"El contenido puede mejorar."
```

---

# 76. Observación válida

```text
"La segunda sección introduce conceptos de autenticación avanzada sin explicar previamente tokens o sesiones."
```

---

# 77. Recommendations

Las recomendaciones deben proponer una acción concreta.

---

# 78. Schema conceptual de Recommendation

```json
{
  "dimension": "didactic_adaptation",
  "message": "Explicar primero qué es un token de autenticación antes de introducir OAuth."
}
```

---

# 79. Reglas para Recommendation

Debe ser:

- específica;
- accionable;
- relacionada con el problema;
- compatible con la evidencia.

---

# 80. Recommendation inválida

```text
"Mejorar el contenido."
```

---

# 81. Recommendation válida

```text
"Reducir la terminología avanzada y definir previamente los conceptos de autenticación antes de presentar OAuth."
```

---

# 82. Unsupported Information

El evaluador debe devolver afirmaciones problemáticas cuando existan.

---

# 83. Schema conceptual

```json
{
  "claim": "Docker reemplaza completamente a Kubernetes.",
  "reason": "La afirmación no está sustentada por los chunks proporcionados."
}
```

---

# 84. Opcional: evidencia relacionada

Puede considerarse:

```json
{
  "claim": "...",
  "reason": "...",
  "related_chunk_ids": [
    "chunk_001",
    "chunk_002"
  ]
}
```

No es obligatorio para v0.1.

---

# 85. Cantidad de observaciones

Evitar producir listas excesivamente largas.

Priorizar los hallazgos de mayor impacto.

---

# 86. Recomendación inicial de cantidad

Como referencia:

```text
0–5 observaciones principales
```

y:

```text
0–5 recomendaciones
```

No es un límite rígido.

---

# 87. No duplicar observaciones

Evitar generar varias observaciones que describan esencialmente el mismo problema.

---

# 88. No inventar fallos

Si una dimensión es adecuada, no es obligatorio producir una observación negativa.

---

# 89. Posible feedback positivo

La primera versión no necesita producir feedback positivo detallado.

La prioridad es:

```text
detectar problemas
+
proponer correcciones
```

---

# 90. Semantic Scores

Los scores deben representar la evaluación del contenido, no la confianza del modelo.

---

# 91. Separación score vs confidence

No confundir:

```text
semantic score
```

con:

```text
confidence
```

---

# 92. Decimales

Se permite inicialmente una escala:

```text
1.0 – 5.0
```

con decimales.

---

# 93. Precisión

No producir una falsa precisión excesiva.

Preferir valores como:

```text
4.2
3.5
2.8
```

y evitar valores como:

```text
4.87391
```

---

# 94. Recomendación de precisión

Máximo:

```text
1 decimal
```

para v0.1.

---

# 95. Semantic Status

El evaluador debe distinguir ejecución de evaluación.

Posibles valores:

```text
success
failed
unavailable
```

---

# 96. `success`

La evaluación fue completada y validada.

---

# 97. `failed`

Se intentó evaluar, pero ocurrió un error.

---

# 98. `unavailable`

El evaluador semántico no está configurado o disponible.

---

# 99. Regla de fallo

Si falla el evaluador semántico:

```text
semantic_scores = null
```

No copiar scores heurísticos.

---

# 100. Structured Output

La respuesta semántica debe validarse mediante schema.

---

# 101. Output conceptual completo

```json
{
  "semantic_status": "success",

  "semantic_scores": {
    "relevance": 4.5,
    "coherence": 4.2,
    "didactic_adaptation": 3.1,
    "content_support": 4.0
  },

  "observations": [
    {
      "dimension": "didactic_adaptation",
      "severity": "medium",
      "message": "El contenido utiliza varios conceptos avanzados sin explicación previa."
    }
  ],

  "recommendations": [
    {
      "dimension": "didactic_adaptation",
      "message": "Introducir primero definiciones breves de los conceptos avanzados."
    }
  ],

  "unsupported_information": []
}
```

---

# 102. Relación con el evaluador heurístico

El semántico no sustituye al heurístico.

Ambos se ejecutan sobre el mismo contenido.

---

# 103. Objetivo de comparación

Comparar:

```text
heuristic_scores
vs
semantic_scores
```

---

# 104. No forzar concordancia

El evaluador semántico no debe intentar replicar artificialmente los scores heurísticos.

---

# 105. Divergencias

Una divergencia puede ser útil.

Ejemplo:

```text
heuristic coherence = 5
semantic coherence = 2.8
```

puede revelar que la heurística de longitud no detecta incoherencia real.

---

# 106. Dataset de calibración

La rúbrica debe validarse contra evaluación humana.

---

# 107. Casos mínimos de calibración

Incluir:

```text
caso excelente
caso irrelevante
caso incoherente
caso de nivel incorrecto
caso no respaldado
caso parcialmente respaldado
```

---

# 108. Ground Truth humano

Cada caso debe tener:

```text
expected scores
expected observations
expected verdict
```

cuando sea posible.

---

# 109. Criterio de calidad del Semantic Evaluator

No se medirá únicamente por cercanía numérica.

También debe evaluarse:

- utilidad de observaciones;
- utilidad de recomendaciones;
- detección de claims;
- estabilidad;
- consistencia.

---

# 110. Consistencia

Casos similares deberían producir resultados similares.

---

# 111. Robustez

Pequeños cambios de redacción no deberían generar cambios extremos de score sin razón.

---

# 112. Grounding

El evaluador debe recibir instrucciones explícitas para no usar conocimiento externo como evidencia.

---

# 113. Ejemplo de instrucción conceptual

```text
Evalúa únicamente si las afirmaciones están respaldadas por chunks_used.
No uses conocimiento externo para confirmar hechos.
```

---

# 114. Adaptation Prompt

Debe indicar explícitamente:

```text
Evalúa si la complejidad corresponde al profile y detail_level.
```

---

# 115. Coherence Prompt

Debe indicar:

```text
Evalúa contradicciones, saltos lógicos y consistencia interna.
```

---

# 116. Relevance Prompt

Debe indicar:

```text
Compara el contenido con learning_objective y niche.
```

---

# 117. Formato de salida

El modelo debe devolver únicamente una estructura validable.

---

# 118. No permitir salida libre como contrato

Evitar depender de respuestas como:

```text
"Creo que el contenido está bien..."
```

---

# 119. Decision Layer

Esta rúbrica define scores semánticos.

No define todavía definitivamente:

```text
status final
```

---

# 120. Razón

El status final dependerá de:

```text
heurístico
+
semántico
+
guardrails
+
calibración
```

---

# 121. Regla provisional

Antes de calibración:

```text
semantic evaluator no reemplaza rubric.py
```

---

# 122. Guardrails potenciales

Posibles reglas a evaluar:

```text
content_support <= 2
→ no approved
```

```text
didactic_adaptation <= 2
→ no approved
```

```text
relevance <= 2
→ no approved
```

No se congelan todavía.

---

# 123. Rejected vs Requires Revision

La diferencia todavía debe calibrarse.

---

# 124. Principio provisional

En general:

```text
requires_revision
```

representa problemas corregibles.

---

# 125. Rejected

Puede reservarse para:

- falta grave de respaldo;
- contenido completamente irrelevante;
- error severo;
- contenido inutilizable.

---

# 126. Error técnico

Nunca convertir automáticamente:

```text
semantic failure
```

en:

```text
rejected
```

---

# 127. Latency

La evaluación semántica añade costo y tiempo.

Debe medirse durante Sprint 4.

---

# 128. Métrica de latencia

Puede registrarse internamente:

```text
semantic_latency_ms
```

No es obligatorio en el contrato público v0.1.

---

# 129. Token Usage

Si el proveedor lo permite, puede medirse consumo.

No es requisito inicial.

---

# 130. Riesgo de input demasiado largo

`chunks_used` y `generated_content` pueden producir prompts extensos.

---

# 131. Estrategia futura

Si fuera necesario:

- limitar chunks;
- resumir evidencia;
- evaluar claims por lotes;
- segmentar contenido.

No se implementará sin necesidad.

---

# 132. No modificar Retrieval V2

La implementación del semántico no debe modificar:

```text
retrieval
chunking
embeddings
reranking
```

---

# 133. Separación de responsabilidades

Retrieval produce evidencia.

Semantic Evaluator evalúa el contenido contra esa evidencia.

---

# 134. Pruebas mínimas de rúbrica

Cada dimensión debe tener al menos:

```text
score alto
score medio
score bajo
```

en el dataset.

---

# 135. Ejemplo de test de Relevance

Caso:

```text
objetivo = APIs REST
contenido = redes neuronales
```

Esperado:

```text
relevance bajo
```

---

# 136. Ejemplo de test de Coherence

Caso:

```text
contenido con contradicción explícita
```

Esperado:

```text
coherence bajo
```

---

# 137. Ejemplo de test de Adaptation

Caso:

```text
profile junior
contenido altamente avanzado
```

Esperado:

```text
didactic_adaptation bajo
```

---

# 138. Ejemplo de test de Support

Caso:

```text
claim no presente en chunks
```

Esperado:

```text
content_support bajo
unsupported_information no vacío
```

---

# 139. Resultado esperado de implementación

El Semantic Evaluator debe ser capaz de distinguir:

```text
contenido técnicamente correcto
```

de:

```text
contenido que solo parece correcto por coincidencia lexical
```

---

# 140. Ejemplo

Chunks:

```text
Kubernetes orquesta contenedores.
```

Contenido:

```text
Kubernetes es una base de datos distribuida.
```

Puede compartir palabras relacionadas con infraestructura.

Pero semánticamente:

```text
content_support = bajo
```

---

# 141. Otro ejemplo

Chunks:

```text
REST utiliza métodos HTTP para operar sobre recursos.
```

Contenido:

```text
GET suele emplearse para recuperar recursos.
```

Aunque no sea una copia textual exacta:

```text
content_support = alto
```

---

# 142. Valor principal del semántico

Detectar equivalencia conceptual y contradicción.

---

# 143. Limitaciones conocidas

Un LLM evaluator puede:

- ser inconsistente;
- utilizar conocimiento externo;
- sobreinterpretar;
- producir scores variables;
- inventar justificaciones.

---

# 144. Mitigaciones

Utilizar:

- temperature baja;
- structured output;
- instrucciones estrictas;
- chunks explícitos;
- tests;
- calibración;
- guardrails heurísticos.

---

# 145. Temperature

Recomendación inicial:

```text
low temperature
```

para mejorar consistencia.

El valor concreto se definirá durante implementación.

---

# 146. Prompt Versioning

El prompt del Semantic Evaluator debe versionarse conceptualmente.

---

# 147. Razón

Cambios de prompt pueden alterar resultados aunque el código no cambie.

---

# 148. Posible metadata futura

```text
semantic_prompt_version
```

No es obligatorio para la primera respuesta pública.

---

# 149. Evaluator Version

La implementación debe registrar una versión.

---

# 150. Rubric Version

Esta rúbrica comienza como:

```text
Semantic Rubric v0.1
```

No equivale necesariamente al `RUBRIC_VERSION` público hasta que sea aprobada.

---

# 151. Estado de esta rúbrica

```text
Draft
```

---

# 152. Criterios para pasar a v1.0

La rúbrica puede promoverse a:

```text
v1.0
```

cuando:

- haya sido revisada por Data/IA;
- tenga casos de calibración;
- Luis implemente un evaluador compatible;
- se comparen resultados con evaluación humana;
- Backend valide la información necesaria;
- Agentes valide recomendaciones;
- se ajusten criterios ambiguos.

---

# 153. Definition of Done

La rúbrica semántica v0.1 se considera lista para implementación cuando:

- las cuatro dimensiones estén definidas;
- exista escala 1–5;
- existan criterios de alto/medio/bajo;
- existan ejemplos;
- observations estén definidas;
- recommendations estén definidas;
- unsupported information esté definida;
- fallback esté especificado;
- el uso de chunks esté claro;
- esté claro que generation_context no es evidencia factual.

---

# 154. Próximo paso después de este documento

Diseñar los schemas Pydantic internos del Semantic Evaluator.

Propuesta conceptual:

```text
SemanticScores
SemanticObservation
SemanticRecommendation
UnsupportedClaim
SemanticEvaluationResult
```

---

# 155. Arquitectura conceptual final

```text
generated_content
generation_context
chunks_used
        │
        ▼
Semantic Evaluator
        │
        ├── semantic_scores
        ├── observations
        ├── recommendations
        └── unsupported_information
        │
        ▼
Hybrid / Decision Layer
```

---

# 156. Resumen final

El Semantic Evaluator debe responder cuatro preguntas:

```text
¿El contenido responde al objetivo?
```

```text
¿El contenido tiene sentido internamente?
```

```text
¿El contenido corresponde al nivel del usuario?
```

```text
¿El contenido está respaldado por la evidencia recuperada?
```

Y cuando exista un problema:

```text
¿Qué está mal?
```

```text
¿Cómo debería corregirse?
```

---

# 157. Regla fundamental de Sprint 4

El éxito del evaluador semántico no se medirá únicamente por producir mejores scores.

Se medirá también por la capacidad de producir:

```text
hallazgos claros
+
recomendaciones accionables
```

que permitan al Agente Revisor generar una versión mejor del contenido.

---

# 158. Próximo entregable

Después de aprobar esta rúbrica, crear:

```text
Data_IA/docs/semantic_schema_v0_1.md
```

para traducir esta especificación conceptual a estructuras Pydantic concretas antes de implementar `semantic_evaluator.py`.